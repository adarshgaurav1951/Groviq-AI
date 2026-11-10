"""
Basket and Transaction Management Service for BarcodeLess Produce Assistant.
Handles line additions, idempotency keys, line modifications, voiding, and checkout commit.
"""

import uuid
from typing import Dict, Any, Optional, List
from services.database import get_db
from services.pricing.service import PricingService
from services.audit.service import AuditService
from services.pos_adapter.adapter import POSAdapter


class BasketService:
    def __init__(self, db_path: str = None):
        self.db_path = db_path
        self.pricing_service = PricingService()
        self.audit_service = AuditService(db_path=db_path)
        self.pos_adapter = POSAdapter()

    def get_or_create_open_transaction(self, store_id: str, station_id: str) -> str:
        """Finds active open transaction for station or creates a new one."""
        with get_db(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id FROM transactions 
                WHERE store_id = ? AND station_id = ? AND status = 'open'
                ORDER BY created_at DESC LIMIT 1
            """, (store_id, station_id))
            row = cursor.fetchone()
            if row:
                return row["id"]

            txn_id = f"TXN-{uuid.uuid4().hex[:10].upper()}"
            conn.execute("""
                INSERT INTO transactions (id, store_id, station_id, status, subtotal, tax_amount, total_amount, currency)
                VALUES (?, ?, ?, 'open', '0.00', '0.00', '0.00', 'INR')
            """, (txn_id, store_id, station_id))
            return txn_id

    def add_line(
        self,
        store_id: str,
        station_id: str,
        catalog_item_id: str,
        idempotency_key: str,
        transaction_id: Optional[str] = None,
        weight_value: Optional[float] = None,
        tare_value: Optional[float] = 0.0,
        quantity: int = 1,
        actor_id: str = "shopper"
    ) -> Dict[str, Any]:
        """
        Adds a produce item to the basket.
        Idempotency key prevents duplicate line additions on network retries.
        """
        with get_db(self.db_path) as conn:
            # 1. Check idempotency key first
            if idempotency_key:
                cursor = conn.execute("SELECT * FROM basket_lines WHERE idempotency_key = ?", (idempotency_key,))
                existing = cursor.fetchone()
                if existing:
                    # Return already committed line and summary
                    txn_id = existing["transaction_id"]
                    return {
                        "status": "idempotent_duplicate_prevented",
                        "line_id": existing["id"],
                        "summary": self.get_basket_summary(txn_id)
                    }

            if not transaction_id:
                transaction_id = self.get_or_create_open_transaction(store_id, station_id)

            # 2. Look up catalog item & active store price
            query = """
                SELECT 
                    ci.id as item_id,
                    ci.retailer_sku,
                    ci.display_name,
                    ci.unit_of_sale,
                    ci.price_basis,
                    cm.plu_code,
                    p.amount as unit_price,
                    p.price_version
                FROM catalog_items ci
                LEFT JOIN catalog_mappings cm ON cm.catalog_item_id = ci.id AND cm.store_id = ?
                JOIN prices p ON p.catalog_item_id = ci.id 
                    AND p.store_id = ?
                    AND (p.effective_to IS NULL OR p.effective_to > CURRENT_TIMESTAMP)
                WHERE ci.id = ? AND ci.active = 1
                ORDER BY p.effective_from DESC LIMIT 1
            """
            cursor = conn.execute(query, (store_id, store_id, catalog_item_id))
            item = cursor.fetchone()
            if not item:
                raise ValueError(f"Catalog item '{catalog_item_id}' not found or active price missing in store '{store_id}'.")

            # 3. Calculate exact line total using PricingService
            calc = self.pricing_service.calculate_line_item(
                unit_price=float(item["unit_price"]),
                price_basis=item["price_basis"],
                weight_value=weight_value,
                tare_value=tare_value,
                quantity=quantity
            )

            # 4. Insert basket line
            line_id = f"LINE-{uuid.uuid4().hex[:10].upper()}"
            conn.execute("""
                INSERT INTO basket_lines 
                (id, transaction_id, catalog_item_id, weight_value, tare_value, weight_unit, quantity, unit_price, line_total, price_version, status, idempotency_key)
                VALUES (?, ?, ?, ?, ?, 'kg', ?, ?, ?, ?, 'active', ?)
            """, (
                line_id,
                transaction_id,
                catalog_item_id,
                calc.get("net_weight"),
                calc.get("tare_weight"),
                calc.get("quantity"),
                calc.get("unit_price"),
                calc.get("line_total"),
                item["price_version"],
                idempotency_key
            ))

        # Recalculate transaction totals
        self._recalculate_transaction_totals(transaction_id)

        # Audit event
        self.audit_service.log_event(
            actor_id=actor_id,
            store_id=store_id,
            station_id=station_id,
            entity_type="basket_line",
            entity_id=line_id,
            action="LINE_ADDED",
            reason="Item verified and added to basket",
            metadata={
                "sku": item["retailer_sku"],
                "plu": item["plu_code"],
                "price": calc.get("unit_price"),
                "total": calc.get("line_total"),
                "trace": calc.get("calculation_trace")
            }
        )

        return {
            "status": "added",
            "line_id": line_id,
            "summary": self.get_basket_summary(transaction_id)
        }

    def remove_line(self, line_id: str, actor_id: str = "shopper", reason: str = "Customer removed item") -> Dict[str, Any]:
        with get_db(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM basket_lines WHERE id = ?", (line_id,))
            line = cursor.fetchone()
            if not line:
                raise ValueError(f"Basket line '{line_id}' not found.")

            txn_id = line["transaction_id"]
            conn.execute("UPDATE basket_lines SET status = 'voided' WHERE id = ?", (line_id,))

        self._recalculate_transaction_totals(txn_id)

        # Audit removal
        with get_db(self.db_path) as conn:
            txn = conn.execute("SELECT store_id, station_id FROM transactions WHERE id = ?", (txn_id,)).fetchone()
            store_id = txn["store_id"] if txn else "STORE-IN-001"
            station_id = txn["station_id"] if txn else "STATION-BLR-01"

        self.audit_service.log_event(
            actor_id=actor_id,
            store_id=store_id,
            station_id=station_id,
            entity_type="basket_line",
            entity_id=line_id,
            action="LINE_VOIDED",
            reason=reason,
            metadata={"voided_line_total": float(line["line_total"])}
        )

        return {
            "status": "voided",
            "line_id": line_id,
            "summary": self.get_basket_summary(txn_id)
        }

    def get_basket_summary(self, transaction_id: str) -> Dict[str, Any]:
        with get_db(self.db_path) as conn:
            txn_cursor = conn.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,))
            txn = txn_cursor.fetchone()
            if not txn:
                raise ValueError(f"Transaction '{transaction_id}' not found.")

            lines_cursor = conn.execute("""
                SELECT 
                    bl.id,
                    bl.transaction_id,
                    bl.catalog_item_id,
                    ci.retailer_sku,
                    ci.display_name,
                    cm.plu_code,
                    bl.weight_value,
                    bl.tare_value,
                    bl.weight_unit,
                    bl.quantity,
                    bl.unit_price,
                    bl.line_total,
                    bl.price_version,
                    bl.status,
                    bl.created_at
                FROM basket_lines bl
                JOIN catalog_items ci ON bl.catalog_item_id = ci.id
                LEFT JOIN catalog_mappings cm ON cm.catalog_item_id = ci.id AND cm.store_id = ?
                WHERE bl.transaction_id = ? AND bl.status = 'active'
                ORDER BY bl.created_at ASC
            """, (txn["store_id"], transaction_id))

            lines = []
            for row in lines_cursor.fetchall():
                lines.append({
                    "id": row["id"],
                    "transaction_id": row["transaction_id"],
                    "catalog_item_id": row["catalog_item_id"],
                    "retailer_sku": row["retailer_sku"],
                    "display_name": row["display_name"],
                    "plu_code": row["plu_code"],
                    "weight_value": float(row["weight_value"]) if row["weight_value"] is not None else None,
                    "tare_value": float(row["tare_value"]) if row["tare_value"] is not None else 0.0,
                    "weight_unit": row["weight_unit"] or "kg",
                    "quantity": int(row["quantity"]),
                    "unit_price": float(row["unit_price"]),
                    "line_total": float(row["line_total"]),
                    "price_version": row["price_version"],
                    "status": row["status"],
                    "created_at": row["created_at"]
                })

            return {
                "transaction_id": txn["id"],
                "store_id": txn["store_id"],
                "station_id": txn["station_id"],
                "status": txn["status"],
                "subtotal": float(txn["subtotal"]),
                "tax_amount": float(txn["tax_amount"]),
                "total_amount": float(txn["total_amount"]),
                "currency": txn["currency"],
                "lines": lines
            }

    def checkout(self, transaction_id: str, tender_type: str = "POS_REDIRECT") -> Dict[str, Any]:
        summary = self.get_basket_summary(transaction_id)
        if len(summary["lines"]) == 0:
            raise ValueError("Cannot checkout an empty basket.")

        pos_result = self.pos_adapter.commit_transaction(summary)

        with get_db(self.db_path) as conn:
            conn.execute("""
                UPDATE transactions 
                SET status = 'completed', 
                    external_pos_reference = ?, 
                    completed_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            """, (pos_result["external_pos_reference"], transaction_id))

        self.audit_service.log_event(
            actor_id="shopper",
            store_id=summary["store_id"],
            station_id=summary["station_id"],
            entity_type="transaction",
            entity_id=transaction_id,
            action="CHECKOUT_COMPLETED",
            reason=f"Tender {tender_type}",
            metadata={
                "pos_ref": pos_result["external_pos_reference"],
                "line_count": len(summary["lines"]),
                "total_amount": summary["total_amount"]
            }
        )

        return {
            "status": "completed",
            "transaction_id": transaction_id,
            "pos_reference": pos_result["external_pos_reference"],
            "total_amount": summary["total_amount"],
            "receipt": pos_result["receipt_text"]
        }

    def _recalculate_transaction_totals(self, transaction_id: str):
        with get_db(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT line_total FROM basket_lines 
                WHERE transaction_id = ? AND status = 'active'
            """, (transaction_id,))
            totals = [float(r["line_total"]) for r in cursor.fetchall()]
            basket_calc = self.pricing_service.calculate_basket_totals(totals, tax_rate_percent=0.0)

            conn.execute("""
                UPDATE transactions 
                SET subtotal = ?, tax_amount = ?, total_amount = ? 
                WHERE id = ?
            """, (
                str(basket_calc["subtotal"]),
                str(basket_calc["tax_amount"]),
                str(basket_calc["total_amount"]),
                transaction_id
            ))

