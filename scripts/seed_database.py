"""
Database Seeder for BarcodeLess Produce Assistant.
Populates standard store, checkout station, hardware devices, produce catalog,
IFPS standard PLU mappings, and effective-dated retail prices.
"""

from services.database import get_db, init_db

PRODUCE_SEED_DATA = [
    ("SKU-APL-RED", "Apple Red Delicious", "Royal Gala / Red Delicious Apple", "kg", "per_kg", "4133", 240.00),
    ("SKU-APL-GLD", "Apple Golden", "Golden Delicious Sweet Apple", "kg", "per_kg", "4021", 260.00),
    ("SKU-APL-GRN", "Apple Granny Smith", "Granny Smith Tart Green Apple", "kg", "per_kg", "4017", 280.00),
    ("SKU-BAN-CAV", "Banana", "Robusta Cavendish Banana", "kg", "per_kg", "4011", 55.00),
    ("SKU-ORG-VAL", "Orange", "Nagpur / Valencia Fresh Orange", "kg", "per_kg", "4012", 90.00),
    ("SKU-LMN-YEL", "Lemon", "Fresh Juicy Yellow Lemon", "kg", "per_kg", "4053", 120.00),
    ("SKU-LIM-GRN", "Limes", "Fresh Green Limes (Nimbu)", "kg", "per_kg", "4048", 140.00),
    ("SKU-TOM-HYB", "Tomato", "Farm Fresh Hybrid Salad Tomato", "kg", "per_kg", "4087", 38.00),
    ("SKU-POT-WHT", "Potato", "Jyoti Clean White Potato", "kg", "per_kg", "4072", 42.00),
    ("SKU-ONI-RED", "Onion Red", "Nasik Export Red Onion", "kg", "per_kg", "4082", 48.00),
    ("SKU-CAR-ORG", "Carrot", "Ooty Sweet Orange Carrot", "kg", "per_kg", "4562", 65.00),
    ("SKU-CUC-GRN", "Cucumber", "Crisp Green Salad Cucumber", "kg", "per_kg", "4062", 45.00),
    ("SKU-PEA-GRE", "Pear", "Imported Sweet Green Pear", "kg", "per_kg", "4409", 180.00),
    ("SKU-PCH-FRE", "Peach", "Fresh Soft Peach", "kg", "per_kg", "4044", 220.00),
    ("SKU-MNG-ALF", "Mango", "Premium Ratnagiri Alphonso Mango", "kg", "per_kg", "4051", 350.00),
    ("SKU-STR-BOX", "Strawberry", "Mahabaleshwar Fresh Strawberry Pack", "piece", "per_piece", "4249", 120.00),
    ("SKU-GRP-BLU", "Grape Blue", "Bangalore Blue Seeded Grapes", "kg", "per_kg", "4056", 110.00),
    ("SKU-GRP-WHT", "Grape White", "Thompson Seedless White Grapes", "kg", "per_kg", "4022", 130.00),
    ("SKU-AVO-HAS", "Avocado", "Fresh Hass Creamy Avocado", "piece", "per_piece", "4225", 95.00),
    ("SKU-EGG-LNG", "Eggplant", "Purple Long Brinjal / Eggplant", "kg", "per_kg", "4081", 50.00),
    ("SKU-PIN-DEL", "Pineapple", "Queen Sweet Ripe Pineapple", "piece", "per_piece", "4430", 85.00),
    ("SKU-KIW-GRE", "Kiwi", "Zespri Fresh Green Kiwi", "piece", "per_piece", "4030", 35.00),
    ("SKU-POM-RED", "Pomegranate", "Ruby Red Sweet Pomegranate", "kg", "per_kg", "4445", 190.00),
    ("SKU-WAT-RED", "Watermelon", "Striped Juicy Red Watermelon", "kg", "per_kg", "4032", 32.00),
    ("SKU-PEP-GRN", "Pepper Green", "Fresh Green Capsicum Bell Pepper", "kg", "per_kg", "4065", 70.00),
    ("SKU-PEP-RED", "Pepper Red", "Sweet Red Bell Pepper", "kg", "per_kg", "4688", 180.00),
]


def seed_database(db_path: str = None):
    print("=== Initializing and Seeding Database ===")
    init_db(db_path)

    store_id = "STORE-IN-001"
    station_id = "STATION-BLR-01"

    with get_db(db_path) as conn:
        # 1. Store
        conn.execute("""
            INSERT OR REPLACE INTO stores (id, name, timezone, currency, status)
            VALUES (?, 'Supermarket Fresh - Indiranagar', 'Asia/Kolkata', 'INR', 'active')
        """, (store_id,))

        # 2. Station
        conn.execute("""
            INSERT OR REPLACE INTO stations (id, store_id, station_code, location_label, status)
            VALUES (?, ?, 'LANE-PRODUCE-01', 'Produce Assisted Self-Checkout Platter 1', 'active')
        """, (station_id, store_id))

        # 3. Hardware Devices
        devices = [
            ("DEV-CAM-01", station_id, "camera", "Logitech", "C920-HD Pro", "v1.0.4", "online"),
            ("DEV-SCALE-01", station_id, "scale", "CAS", "PD-II Digital Scale", "v2.1.0", "online"),
            ("DEV-POS-01", station_id, "pos_terminal", "NCR", "RealPOS 70XRT", "v4.5.1", "online")
        ]
        for dev in devices:
            conn.execute("""
                INSERT OR REPLACE INTO devices 
                (id, station_id, device_type, manufacturer, model, firmware_version, last_seen_at, status)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
            """, dev)

        # 4. Catalog Items, Mappings, and Prices
        price_version = "2026-11-v1"
        for sku, visual_class, name, unit_sale, price_basis, plu, price_val in PRODUCE_SEED_DATA:
            item_id = f"ITEM-{sku}"
            # Catalog Item
            conn.execute("""
                INSERT OR REPLACE INTO catalog_items 
                (id, retailer_sku, display_name, category, unit_of_sale, price_basis, active)
                VALUES (?, ?, ?, 'fresh_produce', ?, ?, 1)
            """, (item_id, sku, name, unit_sale, price_basis))

            # Visual to Catalog Mapping
            mapping_id = f"MAP-{sku}"
            conn.execute("""
                INSERT OR REPLACE INTO catalog_mappings 
                (id, catalog_item_id, visual_class, plu_code, store_id, effective_from, mapping_source, verified_by)
                VALUES (?, ?, ?, ?, ?, '2026-01-01 00:00:00', 'ifps_standard_mapping', 'produce_merchandiser')
            """, (mapping_id, item_id, visual_class, plu, store_id))

            # Store Pricing
            price_id = f"PRC-{sku}-{price_version}"
            conn.execute("""
                INSERT OR REPLACE INTO prices 
                (id, catalog_item_id, store_id, amount, currency, unit_basis, effective_from, price_version)
                VALUES (?, ?, ?, ?, 'INR', ?, '2026-01-01 00:00:00', ?)
            """, (price_id, item_id, store_id, str(price_val), price_basis, price_version))

    print(f"Successfully seeded store '{store_id}', station '{station_id}', 3 devices, and {len(PRODUCE_SEED_DATA)} produce catalog items with active prices & PLUs.")


if __name__ == "__main__":
    seed_database()

