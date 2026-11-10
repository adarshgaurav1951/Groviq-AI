"""
Integration test for BasketService idempotency, line additions, and POS checkout.
"""

import os
import tempfile
from services.database import init_db
from scripts.seed_database import seed_database
from services.basket.service import BasketService


def test_basket_idempotency_and_checkout():
    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        db_path = f.name
        seed_database(db_path=db_path)

        bs = BasketService(db_path=db_path)
        store_id = "STORE-IN-001"
        station_id = "STATION-BLR-01"

        # Item 1: Royal Gala Apple (SKU-APL-RED) at ₹240.00/kg
        item_id = "ITEM-SKU-APL-RED"
        idempotency_key = "IDEMP-TEST-KEY-001"

        # First add call
        res1 = bs.add_line(
            store_id=store_id,
            station_id=station_id,
            catalog_item_id=item_id,
            idempotency_key=idempotency_key,
            weight_value=0.850
        )
        assert res1["status"] == "added"
        summary1 = res1["summary"]
        assert len(summary1["lines"]) == 1
        assert summary1["total_amount"] == 204.00

        # Duplicate retry call with same idempotency key
        res2 = bs.add_line(
            store_id=store_id,
            station_id=station_id,
            catalog_item_id=item_id,
            idempotency_key=idempotency_key,
            weight_value=0.850
        )
        assert res2["status"] == "idempotent_duplicate_prevented"
        summary2 = res2["summary"]
        # Must still have exactly 1 line, NOT duplicated
        assert len(summary2["lines"]) == 1
        assert summary2["total_amount"] == 204.00

        # Add second item: Robusta Banana at ₹55.00/kg
        res3 = bs.add_line(
            store_id=store_id,
            station_id=station_id,
            catalog_item_id="ITEM-SKU-BAN-CAV",
            idempotency_key="IDEMP-TEST-KEY-002",
            weight_value=1.000
        )
        assert len(res3["summary"]["lines"]) == 2
        assert res3["summary"]["total_amount"] == 259.00  # 204.00 + 55.00

        # Checkout
        txn_id = res3["summary"]["transaction_id"]
        checkout_res = bs.checkout(transaction_id=txn_id)
        assert checkout_res["status"] == "completed"
        assert "SUPERMARKET FRESH" in checkout_res["receipt"]
        assert checkout_res["total_amount"] == 259.00

