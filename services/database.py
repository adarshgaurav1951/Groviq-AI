"""
Database layer for BarcodeLess Produce Assistant.
Provides SQLite connection management, schema initialization, and transactional safety.
"""

import os
import sqlite3
from typing import Generator
from contextlib import contextmanager

DEFAULT_DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "produce_assistant.db"))

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS stores (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    timezone TEXT NOT NULL DEFAULT 'Asia/Kolkata',
    currency TEXT NOT NULL DEFAULT 'INR',
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS stations (
    id TEXT PRIMARY KEY,
    store_id TEXT NOT NULL REFERENCES stores(id),
    station_code TEXT NOT NULL UNIQUE,
    location_label TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS devices (
    id TEXT PRIMARY KEY,
    station_id TEXT NOT NULL REFERENCES stations(id),
    device_type TEXT NOT NULL, -- camera, scale, pos_terminal
    manufacturer TEXT NOT NULL,
    model TEXT NOT NULL,
    firmware_version TEXT NOT NULL,
    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'online'
);

CREATE TABLE IF NOT EXISTS catalog_items (
    id TEXT PRIMARY KEY,
    retailer_sku TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'produce',
    unit_of_sale TEXT NOT NULL, -- kg, piece, bunch
    price_basis TEXT NOT NULL,  -- per_kg, per_piece
    image_url TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS catalog_mappings (
    id TEXT PRIMARY KEY,
    catalog_item_id TEXT NOT NULL REFERENCES catalog_items(id),
    visual_class TEXT NOT NULL,
    plu_code TEXT,
    store_id TEXT NOT NULL REFERENCES stores(id),
    effective_from TIMESTAMP NOT NULL,
    effective_to TIMESTAMP,
    mapping_source TEXT NOT NULL DEFAULT 'retailer_catalog_v1',
    verified_by TEXT NOT NULL DEFAULT 'compliance_system'
);

CREATE TABLE IF NOT EXISTS prices (
    id TEXT PRIMARY KEY,
    catalog_item_id TEXT NOT NULL REFERENCES catalog_items(id),
    store_id TEXT NOT NULL REFERENCES stores(id),
    amount NUMERIC NOT NULL, -- stored as decimal string / exact numeric
    currency TEXT NOT NULL DEFAULT 'INR',
    unit_basis TEXT NOT NULL, -- per_kg, per_piece
    effective_from TIMESTAMP NOT NULL,
    effective_to TIMESTAMP,
    price_version TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS model_versions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT NOT NULL UNIQUE,
    artifact_uri TEXT NOT NULL,
    checksum TEXT NOT NULL,
    metrics_json TEXT NOT NULL,
    approval_status TEXT NOT NULL DEFAULT 'approved',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deployed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS recognitions (
    id TEXT PRIMARY KEY,
    store_id TEXT NOT NULL REFERENCES stores(id),
    station_id TEXT NOT NULL REFERENCES stations(id),
    model_version TEXT NOT NULL,
    status TEXT NOT NULL, -- high_confidence, medium_confidence, low_confidence, rejected_quality
    top_candidates_json TEXT NOT NULL,
    selected_catalog_item_id TEXT REFERENCES catalog_items(id),
    confidence REAL,
    image_quality_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS scale_readings (
    id TEXT PRIMARY KEY,
    station_id TEXT NOT NULL REFERENCES stations(id),
    recognition_id TEXT REFERENCES recognitions(id),
    weight_value NUMERIC NOT NULL,
    tare_value NUMERIC NOT NULL DEFAULT 0.0,
    weight_unit TEXT NOT NULL DEFAULT 'kg',
    stable INTEGER NOT NULL DEFAULT 1,
    device_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS transactions (
    id TEXT PRIMARY KEY,
    store_id TEXT NOT NULL REFERENCES stores(id),
    station_id TEXT NOT NULL REFERENCES stations(id),
    external_pos_reference TEXT,
    status TEXT NOT NULL DEFAULT 'open', -- open, completed, cancelled, refunded
    subtotal NUMERIC NOT NULL DEFAULT '0.00',
    tax_amount NUMERIC NOT NULL DEFAULT '0.00',
    total_amount NUMERIC NOT NULL DEFAULT '0.00',
    currency TEXT NOT NULL DEFAULT 'INR',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS basket_lines (
    id TEXT PRIMARY KEY,
    transaction_id TEXT NOT NULL REFERENCES transactions(id),
    catalog_item_id TEXT NOT NULL REFERENCES catalog_items(id),
    weight_value NUMERIC,
    tare_value NUMERIC DEFAULT 0.0,
    weight_unit TEXT DEFAULT 'kg',
    quantity INTEGER DEFAULT 1,
    unit_price NUMERIC NOT NULL,
    line_total NUMERIC NOT NULL,
    price_version TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active', -- active, voided, updated
    idempotency_key TEXT UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_events (
    id TEXT PRIMARY KEY,
    actor_id TEXT NOT NULL,
    store_id TEXT NOT NULL REFERENCES stores(id),
    station_id TEXT NOT NULL REFERENCES stations(id),
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    action TEXT NOT NULL,
    reason TEXT,
    metadata_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indices for performance and tenant scoping
CREATE INDEX IF NOT EXISTS idx_stations_store ON stations(store_id);
CREATE INDEX IF NOT EXISTS idx_mappings_visual ON catalog_mappings(visual_class, store_id);
CREATE INDEX IF NOT EXISTS idx_mappings_plu ON catalog_mappings(plu_code);
CREATE INDEX IF NOT EXISTS idx_prices_item_store ON prices(catalog_item_id, store_id);
CREATE INDEX IF NOT EXISTS idx_basket_lines_txn ON basket_lines(transaction_id);
CREATE INDEX IF NOT EXISTS idx_audit_store_created ON audit_events(store_id, created_at);
"""


def get_db_path() -> str:
    path = os.environ.get("DATABASE_PATH", DEFAULT_DB_PATH)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    return path


def get_connection(db_path: str = None) -> sqlite3.Connection:
    if db_path is None:
        db_path = get_db_path()
    conn = sqlite3.connect(db_path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def get_db(db_path: str = None) -> Generator[sqlite3.Connection, None, None]:
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: str = None) -> None:
    """Initializes the database schema."""
    with get_db(db_path) as conn:
        conn.executescript(SCHEMA_SQL)

