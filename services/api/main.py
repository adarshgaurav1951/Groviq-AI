"""
FastAPI REST API Service for BarcodeLess Produce Assistant.
Exposes checkout station endpoints, computer vision recognition, scale interface,
basket management, admin telemetry, and health probes.
"""

import os
import io
import json
import uuid
import base64
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Query
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image

from services.database import get_db, init_db
from services.models import (
    RecognitionResponse,
    AddBasketLineRequest,
    RegisterProductRequest,
    AttendantOverrideRequest,
    CheckoutRequest,
    ScaleReading,
    BasketSummary,
    ImageQualityResult,
    VisualCandidate,
    DecisionPolicy
)
from services.catalog.service import CatalogService
from services.pricing.service import PricingService
from services.scale_adapter.adapter import ScaleAdapter
from services.basket.service import BasketService
from services.audit.service import AuditService
from ml.src.quality import ImageQualityGate
from ml.src.classifier import ProduceClassifier

app = FastAPI(
    title="BarcodeLess Produce Assistant API",
    version="1.0.0",
    description="Vision-powered produce identification and assisted checkout platform"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize core services
quality_gate = ImageQualityGate()
catalog_service = CatalogService()
pricing_service = PricingService()
scale_adapter = ScaleAdapter(station_id="STATION-BLR-01")
basket_service = BasketService()
audit_service = AuditService()

# Classifier model loader
classifier = None
try:
    classifier = ProduceClassifier()
    print("ProduceClassifier loaded successfully with MobileNetV3 backbone!")
except Exception as e:
    print(f"Warning: classifier could not be loaded at startup: {e}")


@app.on_event("startup")
def startup_event():
    init_db()


# ---------------- HEALTH & READINESS ----------------

@app.get("/health/live")
def liveness():
    return {"status": "ok", "service": "produce_assistant"}


@app.get("/health/ready")
def readiness():
    model_ready = classifier is not None and classifier.model is not None
    scale_ready = scale_adapter.is_connected
    with get_db() as conn:
        db_ready = conn.execute("SELECT 1").fetchone() is not None

    all_ready = model_ready and scale_ready and db_ready
    status_code = 200 if all_ready else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if all_ready else "not_ready",
            "model_ready": model_ready,
            "scale_ready": scale_ready,
            "db_ready": db_ready
        }
    )


# ---------------- RECOGNITION ENDPOINTS ----------------

@app.post("/api/v1/recognitions")
async def create_recognition(
    file: Optional[UploadFile] = File(None),
    image_base64: Optional[str] = Form(None),
    store_id: str = Form("STORE-IN-001"),
    station_id: str = Form("STATION-BLR-01")
):
    """
    Submits a camera frame for produce or new product identification.
    Evaluates quality gate, runs visual inference, maps to store catalog,
    and returns candidates with decision policy.
    """
    image = None
    if file:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
    elif image_base64:
        if "," in image_base64:
            image_base64 = image_base64.split(",")[1]
        decoded = base64.b64decode(image_base64)
        image = Image.open(io.BytesIO(decoded))
    else:
        raise HTTPException(status_code=400, detail="Either 'file' or 'image_base64' must be provided.")

    rec_id = f"REC-{uuid.uuid4().hex[:10].upper()}"

    # 1. Image Quality Gate
    quality_res = quality_gate.evaluate(image)
    if not quality_res["is_usable"]:
        with get_db() as conn:
            conn.execute("""
                INSERT INTO recognitions 
                (id, store_id, station_id, model_version, status, top_candidates_json, confidence, image_quality_json)
                VALUES (?, ?, ?, 'produce-classifier-1.0.0', 'rejected_quality', '[]', 0.0, ?)
            """, (rec_id, store_id, station_id, json.dumps(quality_res)))

        return {
            "recognition_id": rec_id,
            "model_version": "produce-classifier-1.0.0",
            "status": "rejected_quality",
            "candidates": [],
            "decision": {
                "action": "rejected_quality",
                "reason": quality_res["reason"]
            },
            "quality": quality_res
        }

    # 2. Isolate Produce & Classify
    if classifier is None:
        raise HTTPException(status_code=503, detail="Produce classifier model is not initialized.")

    cropped_img = quality_gate.isolate_produce(image)
    pred_res = classifier.predict(cropped_img, top_k=3)

    # 3. Resolve Visual Candidates to Active Store SKUs/PLUs
    enriched_candidates = catalog_service.resolve_visual_candidates(pred_res["candidates"], store_id=store_id)

    # 4. Persist Recognition Record
    with get_db() as conn:
        conn.execute("""
            INSERT INTO recognitions 
            (id, store_id, station_id, model_version, status, top_candidates_json, confidence, image_quality_json)
            VALUES (?, ?, ?, 'produce-classifier-1.0.0', ?, ?, ?, ?)
        """, (
            rec_id,
            store_id,
            station_id,
            pred_res["status"],
            json.dumps(enriched_candidates),
            pred_res["top_confidence"],
            json.dumps(quality_res)
        ))

    # Audit recognition
    audit_service.log_event(
        actor_id="shopper",
        store_id=store_id,
        station_id=station_id,
        entity_type="recognition",
        entity_id=rec_id,
        action="RECOGNITION_COMPLETED",
        reason=pred_res["decision"]["action"],
        metadata={
            "top_candidate": enriched_candidates[0]["display_name"] if enriched_candidates else None,
            "top_confidence": pred_res["top_confidence"],
            "open_set_dist": pred_res["open_set_distance"],
            "is_new_product": pred_res["is_unknown"]
        }
    )

    return {
        "recognition_id": rec_id,
        "model_version": "produce-classifier-1.0.0",
        "status": pred_res["status"],
        "candidates": enriched_candidates,
        "decision": pred_res["decision"],
        "quality": quality_res,
        "feature_vector": pred_res.get("feature_vector")
    }


@app.post("/api/v1/recognitions/{rec_id}/confirm")
def confirm_recognition(
    rec_id: str,
    catalog_item_id: str = Form(...),
    actor_id: str = Form("shopper"),
    store_id: str = Form("STORE-IN-001"),
    station_id: str = Form("STATION-BLR-01")
):
    with get_db() as conn:
        conn.execute("""
            UPDATE recognitions 
            SET selected_catalog_item_id = ? 
            WHERE id = ?
        """, (catalog_item_id, rec_id))

    audit_service.log_event(
        actor_id=actor_id,
        store_id=store_id,
        station_id=station_id,
        entity_type="recognition",
        entity_id=rec_id,
        action="ITEM_CONFIRMED",
        reason="User confirmed catalog item selection",
        metadata={"selected_item_id": catalog_item_id}
    )
    return {"status": "confirmed", "recognition_id": rec_id, "selected_catalog_item_id": catalog_item_id}


# ---------------- SCALE ENDPOINTS ----------------

@app.get("/api/v1/scale/readings")
@app.post("/api/v1/scale/readings")
def get_scale_reading():
    return scale_adapter.get_reading()


@app.post("/api/v1/scale/tare")
def tare_scale(tare_value: Optional[float] = Form(None)):
    return scale_adapter.tare(tare_value)


@app.post("/api/v1/scale/zero")
def zero_scale():
    return scale_adapter.zero()


@app.post("/api/v1/scale/simulate")
def simulate_scale(
    weight: float = Form(...),
    stable: bool = Form(True)
):
    scale_adapter.simulate_weight(weight, stable=stable)
    return scale_adapter.get_reading()


# ---------------- CATALOG & NEW PRODUCT ENROLLMENT ----------------

@app.get("/api/v1/catalog/items")
def search_catalog_items(
    query: Optional[str] = Query("", description="Search by name, SKU, or PLU"),
    store_id: str = Query("STORE-IN-001")
):
    return catalog_service.search_catalog(query=query, store_id=store_id, limit=30)


@app.get("/api/v1/catalog/items/{item_id}")
def get_catalog_item(item_id: str, store_id: str = Query("STORE-IN-001")):
    item = catalog_service.get_item_by_id(item_id, store_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Catalog item '{item_id}' not found.")
    return item


@app.post("/api/v1/catalog/items")
def register_new_catalog_item(req: RegisterProductRequest):
    """
    Onboards and registers a new product into the store catalog, sets price,
    and updates the ML visual prototype so future camera scans recognize it immediately!
    """
    try:
        item = catalog_service.register_new_product(
            display_name=req.display_name,
            unit_price=req.unit_price,
            category=req.category,
            unit_of_sale=req.unit_of_sale,
            price_basis=req.price_basis,
            plu_code=req.plu_code,
            retailer_sku=req.retailer_sku,
            visual_class=req.visual_class or req.display_name,
            store_id=req.store_id
        )

        # Register prototype vector into classifier memory
        if req.feature_vector and classifier:
            classifier.register_product(visual_class=req.display_name, embedding=req.feature_vector)

        # Log audit event
        audit_service.log_event(
            actor_id="attendant_or_shopper",
            store_id=req.store_id,
            station_id="STATION-BLR-01",
            entity_type="catalog_item",
            entity_id=item["catalog_item_id"],
            action="NEW_PRODUCT_ENROLLED",
            reason="User/Cashier enrolled new product into store catalog",
            metadata={
                "sku": item["retailer_sku"],
                "name": item["display_name"],
                "price": item["unit_price"],
                "unit": item["unit_of_sale"]
            }
        )

        return item
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------- BASKET ENDPOINTS ----------------

@app.get("/api/v1/basket")
def get_basket(
    store_id: str = Query("STORE-IN-001"),
    station_id: str = Query("STATION-BLR-01")
):
    txn_id = basket_service.get_or_create_open_transaction(store_id, station_id)
    return basket_service.get_basket_summary(txn_id)


@app.post("/api/v1/basket/lines")
def add_basket_line(req: AddBasketLineRequest):
    try:
        return basket_service.add_line(
            store_id=req.store_id,
            station_id=req.station_id,
            catalog_item_id=req.catalog_item_id,
            idempotency_key=req.idempotency_key,
            transaction_id=req.transaction_id,
            weight_value=req.weight_value,
            tare_value=req.tare_value,
            quantity=req.quantity
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/v1/basket/lines/{line_id}")
def remove_basket_line(
    line_id: str,
    actor_id: str = Query("shopper"),
    reason: str = Query("Customer voided line")
):
    try:
        return basket_service.remove_line(line_id=line_id, actor_id=actor_id, reason=reason)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/basket/checkout")
def checkout_basket(req: CheckoutRequest):
    try:
        return basket_service.checkout(transaction_id=req.transaction_id, tender_type=req.tender_type)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------- ATTENDANT & OVERRIDE ----------------

@app.post("/api/v1/attendant/override")
def attendant_override(req: AttendantOverrideRequest):
    if req.pin != "1234":
        raise HTTPException(status_code=403, detail="Invalid Attendant PIN.")

    audit_service.log_event(
        actor_id=req.actor_id,
        store_id="STORE-IN-001",
        station_id="STATION-BLR-01",
        entity_type="override",
        entity_id=req.line_id or req.catalog_item_id or "STATION",
        action=req.action,
        reason=req.reason,
        metadata={"amount": req.override_amount}
    )
    return {"status": "authorized", "action": req.action, "reason": req.reason}


# ---------------- ADMIN & MONITORING ----------------

@app.get("/api/v1/admin/devices")
def get_devices(store_id: str = Query("STORE-IN-001")):
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT d.*, s.station_code 
            FROM devices d
            JOIN stations s ON d.station_id = s.id
            WHERE s.store_id = ?
        """, (store_id,))
        devices = [dict(row) for row in cursor.fetchall()]
        return devices


@app.get("/api/v1/admin/metrics")
def get_operational_metrics(store_id: str = Query("STORE-IN-001")):
    with get_db() as conn:
        tot_rec = conn.execute("SELECT count(*) as c FROM recognitions WHERE store_id = ?", (store_id,)).fetchone()["c"]
        high_conf = conn.execute("SELECT count(*) as c FROM recognitions WHERE store_id = ? AND status = 'high_confidence'", (store_id,)).fetchone()["c"]
        med_conf = conn.execute("SELECT count(*) as c FROM recognitions WHERE store_id = ? AND status = 'medium_confidence'", (store_id,)).fetchone()["c"]
        low_conf = conn.execute("SELECT count(*) as c FROM recognitions WHERE store_id = ? AND status = 'low_confidence'", (store_id,)).fetchone()["c"]
        new_prod = conn.execute("SELECT count(*) as c FROM recognitions WHERE store_id = ? AND status = 'new_product_detected'", (store_id,)).fetchone()["c"]
        rej_qual = conn.execute("SELECT count(*) as c FROM recognitions WHERE store_id = ? AND status = 'rejected_quality'", (store_id,)).fetchone()["c"]

        tot_txn = conn.execute("SELECT count(*) as c, sum(total_amount) as s FROM transactions WHERE store_id = ? AND status = 'completed'", (store_id,)).fetchone()
        tot_overrides = conn.execute("SELECT count(*) as c FROM audit_events WHERE store_id = ? AND action LIKE '%OVERRIDE%'", (store_id,)).fetchone()["c"]

        return {
            "total_recognitions": tot_rec,
            "high_confidence_count": high_conf,
            "medium_confidence_count": med_conf,
            "low_confidence_count": low_conf,
            "new_product_detections": new_prod,
            "quality_rejections": rej_qual,
            "completed_transactions": tot_txn["c"],
            "total_produce_revenue": float(tot_txn["s"] or 0.0),
            "attendant_overrides": tot_overrides,
            "active_model_version": "mobilenet-v3-produce-1.0.0",
            "active_model_metrics": {
                "top_1_accuracy": 0.9885,
                "top_3_accuracy": 1.0,
                "macro_f1": 0.9882,
                "latency_p95_ms": 15.81
            }
        }


@app.get("/api/v1/admin/audit")
def get_audit_logs(
    store_id: str = Query("STORE-IN-001"),
    entity_type: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    limit: int = Query(50)
):
    return audit_service.list_events(store_id=store_id, entity_type=entity_type, action=action, limit=limit)


# ---------------- STATIC APPS SERVING ----------------
apps_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "apps")
checkout_ui_dir = os.path.join(apps_dir, "checkout_ui")
admin_dashboard_dir = os.path.join(apps_dir, "admin_dashboard")

if os.path.exists(checkout_ui_dir):
    app.mount("/checkout", StaticFiles(directory=checkout_ui_dir, html=True), name="checkout_ui")

if os.path.exists(admin_dashboard_dir):
    app.mount("/admin", StaticFiles(directory=admin_dashboard_dir, html=True), name="admin_dashboard")

@app.get("/")
def index_redirect():
    return FileResponse(os.path.join(checkout_ui_dir, "index.html"))
