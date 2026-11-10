"""
Catalog and PLU resolution service for BarcodeLess Produce Assistant.
Maps computer vision visual class predictions to store-specific SKUs, PLUs, and pricing,
and supports dynamic registration of new products.
"""

import uuid
import sqlite3
from typing import List, Dict, Any, Optional
from services.database import get_db


class CatalogService:
    def __init__(self, db_path: str = None):
        self.db_path = db_path

    def register_new_product(
        self,
        display_name: str,
        unit_price: float,
        category: str = "Fresh Produce",
        unit_of_sale: str = "kg",
        price_basis: str = "per_kg",
        plu_code: Optional[str] = None,
        retailer_sku: Optional[str] = None,
        visual_class: Optional[str] = None,
        store_id: str = "STORE-IN-001"
    ) -> Dict[str, Any]:
        """
        Registers a new product into the store catalog, creates PLU mapping,
        and sets its active price.
        """
        if not retailer_sku:
            clean_prefix = "".join(c for c in display_name[:3].upper() if c.isalnum()) or "PRD"
            retailer_sku = f"SKU-{clean_prefix}-{uuid.uuid4().hex[:4].upper()}"

        item_id = f"ITEM-{retailer_sku}"
        v_class = visual_class or display_name
        price_version = "2026-11-v1"

        with get_db(self.db_path) as conn:
            # 1. Catalog item
            conn.execute("""
                INSERT OR REPLACE INTO catalog_items 
                (id, retailer_sku, display_name, category, unit_of_sale, price_basis, active)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (item_id, retailer_sku, display_name, category, unit_of_sale, price_basis))

            # 2. Visual to Catalog Mapping
            mapping_id = f"MAP-{retailer_sku}"
            conn.execute("""
                INSERT OR REPLACE INTO catalog_mappings 
                (id, catalog_item_id, visual_class, plu_code, store_id, effective_from, mapping_source, verified_by)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 'user_enrolled_product', 'attendant_verified')
            """, (mapping_id, item_id, v_class, plu_code, store_id))

            # 3. Store Price
            price_id = f"PRC-{retailer_sku}-{price_version}"
            conn.execute("""
                INSERT OR REPLACE INTO prices 
                (id, catalog_item_id, store_id, amount, currency, unit_basis, effective_from, price_version)
                VALUES (?, ?, ?, ?, 'INR', ?, CURRENT_TIMESTAMP, ?)
            """, (price_id, item_id, store_id, str(unit_price), price_basis, price_version))

        return {
            "catalog_item_id": item_id,
            "retailer_sku": retailer_sku,
            "display_name": display_name,
            "category": category,
            "unit_of_sale": unit_of_sale,
            "price_basis": price_basis,
            "plu_code": plu_code,
            "unit_price": float(unit_price),
            "currency": "INR",
            "price_version": price_version,
            "visual_class": v_class
        }

    def resolve_visual_candidates(self, visual_candidates: List[Dict[str, Any]], store_id: str = "STORE-IN-001") -> List[Dict[str, Any]]:
        """
        Takes candidate predictions and enriches them with store-specific SKU, PLU, display name, and pricing.
        """
        enriched_candidates = []
        with get_db(self.db_path) as conn:
            for cand in visual_candidates:
                v_class = cand["visual_class"]
                conf = cand["confidence"]
                is_new = cand.get("is_new_product", False)
                suggested_name = cand.get("suggested_name")

                if is_new:
                    enriched_candidates.append({
                        "visual_class": v_class,
                        "confidence": conf,
                        "is_new_product": True,
                        "suggested_name": suggested_name or v_class,
                        "catalog_item_id": None,
                        "retailer_sku": None,
                        "display_name": f"{suggested_name or v_class} (New Product)",
                        "plu_code": None,
                        "unit_of_sale": "kg",
                        "price_basis": "per_kg",
                        "unit_price": None,
                        "currency": "INR",
                        "price_version": None,
                        "image_url": None
                    })
                    continue

                # Query store-specific mapping and active price
                query = """
                    SELECT 
                        ci.id as catalog_item_id,
                        ci.retailer_sku,
                        ci.display_name,
                        ci.category,
                        ci.unit_of_sale,
                        ci.price_basis,
                        ci.image_url,
                        cm.plu_code,
                        p.amount as unit_price,
                        p.currency,
                        p.price_version
                    FROM catalog_mappings cm
                    JOIN catalog_items ci ON cm.catalog_item_id = ci.id
                    LEFT JOIN prices p ON p.catalog_item_id = ci.id 
                        AND p.store_id = cm.store_id
                        AND (p.effective_to IS NULL OR p.effective_to > CURRENT_TIMESTAMP)
                    WHERE (cm.visual_class = ? OR ci.display_name = ?)
                      AND cm.store_id = ?
                      AND ci.active = 1
                    ORDER BY p.effective_from DESC
                    LIMIT 1
                """
                cursor = conn.execute(query, (v_class, v_class, store_id))
                row = cursor.fetchone()

                if row:
                    enriched_candidates.append({
                        "visual_class": v_class,
                        "confidence": conf,
                        "is_new_product": False,
                        "catalog_item_id": row["catalog_item_id"],
                        "retailer_sku": row["retailer_sku"],
                        "display_name": row["display_name"],
                        "plu_code": row["plu_code"],
                        "unit_of_sale": row["unit_of_sale"],
                        "price_basis": row["price_basis"],
                        "unit_price": float(row["unit_price"]) if row["unit_price"] else None,
                        "currency": row["currency"] or "INR",
                        "price_version": row["price_version"],
                        "image_url": row["image_url"]
                    })
                else:
                    enriched_candidates.append({
                        "visual_class": v_class,
                        "confidence": conf,
                        "is_new_product": True,
                        "suggested_name": v_class,
                        "catalog_item_id": None,
                        "retailer_sku": None,
                        "display_name": f"{v_class} (Uncataloged)",
                        "plu_code": None,
                        "unit_of_sale": "kg",
                        "price_basis": "per_kg",
                        "unit_price": None,
                        "currency": "INR",
                        "price_version": None,
                        "image_url": None
                    })

        return enriched_candidates

    def search_catalog(self, query: str, store_id: str = "STORE-IN-001", limit: int = 15) -> List[Dict[str, Any]]:
        search_pattern = f"%{query.strip()}%"
        with get_db(self.db_path) as conn:
            sql = """
                SELECT 
                    ci.id as catalog_item_id,
                    ci.retailer_sku,
                    ci.display_name,
                    ci.category,
                    ci.unit_of_sale,
                    ci.price_basis,
                    ci.image_url,
                    cm.plu_code,
                    p.amount as unit_price,
                    p.currency,
                    p.price_version
                FROM catalog_items ci
                LEFT JOIN catalog_mappings cm ON cm.catalog_item_id = ci.id AND cm.store_id = ?
                LEFT JOIN prices p ON p.catalog_item_id = ci.id 
                    AND p.store_id = ?
                    AND (p.effective_to IS NULL OR p.effective_to > CURRENT_TIMESTAMP)
                WHERE ci.active = 1
                  AND (
                      ci.display_name LIKE ? OR 
                      ci.retailer_sku LIKE ? OR 
                      cm.plu_code LIKE ?
                  )
                GROUP BY ci.id
                ORDER BY ci.display_name ASC
                LIMIT ?
            """
            cursor = conn.execute(sql, (store_id, store_id, search_pattern, search_pattern, search_pattern, limit))
            results = []
            for row in cursor.fetchall():
                results.append({
                    "catalog_item_id": row["catalog_item_id"],
                    "retailer_sku": row["retailer_sku"],
                    "display_name": row["display_name"],
                    "category": row["category"],
                    "unit_of_sale": row["unit_of_sale"],
                    "price_basis": row["price_basis"],
                    "plu_code": row["plu_code"],
                    "unit_price": float(row["unit_price"]) if row["unit_price"] else None,
                    "currency": row["currency"] or "INR",
                    "price_version": row["price_version"],
                    "image_url": row["image_url"]
                })
            return results

    def get_item_by_id(self, item_id: str, store_id: str = "STORE-IN-001") -> Optional[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            sql = """
                SELECT 
                    ci.id as catalog_item_id,
                    ci.retailer_sku,
                    ci.display_name,
                    ci.category,
                    ci.unit_of_sale,
                    ci.price_basis,
                    ci.image_url,
                    cm.plu_code,
                    p.amount as unit_price,
                    p.currency,
                    p.price_version
                FROM catalog_items ci
                LEFT JOIN catalog_mappings cm ON cm.catalog_item_id = ci.id AND cm.store_id = ?
                LEFT JOIN prices p ON p.catalog_item_id = ci.id 
                    AND p.store_id = ?
                    AND (p.effective_to IS NULL OR p.effective_to > CURRENT_TIMESTAMP)
                WHERE ci.id = ? AND ci.active = 1
                LIMIT 1
            """
            cursor = conn.execute(sql, (store_id, store_id, item_id))
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "catalog_item_id": row["catalog_item_id"],
                "retailer_sku": row["retailer_sku"],
                "display_name": row["display_name"],
                "category": row["category"],
                "unit_of_sale": row["unit_of_sale"],
                "price_basis": row["price_basis"],
                "plu_code": row["plu_code"],
                "unit_price": float(row["unit_price"]) if row["unit_price"] else None,
                "currency": row["currency"] or "INR",
                "price_version": row["price_version"],
                "image_url": row["image_url"]
            }
