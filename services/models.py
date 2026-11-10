"""
Pydantic schemas and domain models for BarcodeLess Produce Assistant.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ImageQualityResult(BaseModel):
    is_usable: bool
    blur_score: float
    glare_ratio: float
    mean_luminance: float
    reason: Optional[str] = None


class VisualCandidate(BaseModel):
    visual_class: str
    confidence: float
    is_new_product: bool = False
    suggested_name: Optional[str] = None
    catalog_item_id: Optional[str] = None
    display_name: Optional[str] = None
    retailer_sku: Optional[str] = None
    plu_code: Optional[str] = None
    unit_price: Optional[float] = None
    price_basis: Optional[str] = None
    unit_of_sale: Optional[str] = None
    image_url: Optional[str] = None


class DecisionPolicy(BaseModel):
    action: str  # confirm_top_candidate, select_from_top_k, verify_new_product, manual_lookup_required, rejected_quality
    reason: str


class RecognitionResponse(BaseModel):
    recognition_id: str
    model_version: str
    status: str
    candidates: List[VisualCandidate]
    decision: DecisionPolicy
    quality: ImageQualityResult
    feature_vector: Optional[List[float]] = None


class ScaleReading(BaseModel):
    station_id: str
    weight_value: float
    tare_value: float = 0.0
    net_weight: float
    weight_unit: str = "kg"
    stable: bool = True
    device_timestamp: Optional[str] = None


class BasketLineItem(BaseModel):
    id: str
    transaction_id: str
    catalog_item_id: str
    display_name: str
    retailer_sku: str
    plu_code: Optional[str] = None
    weight_value: Optional[float] = None
    tare_value: Optional[float] = 0.0
    weight_unit: Optional[str] = "kg"
    quantity: int = 1
    unit_price: float
    line_total: float
    price_version: str
    status: str = "active"
    created_at: Optional[str] = None


class BasketSummary(BaseModel):
    transaction_id: str
    store_id: str
    station_id: str
    status: str
    subtotal: float
    tax_amount: float
    total_amount: float
    currency: str = "INR"
    lines: List[BasketLineItem]


class AddBasketLineRequest(BaseModel):
    transaction_id: Optional[str] = None
    store_id: str = "STORE-IN-001"
    station_id: str = "STATION-BLR-01"
    catalog_item_id: str
    recognition_id: Optional[str] = None
    weight_value: Optional[float] = None
    tare_value: Optional[float] = 0.0
    quantity: int = 1
    idempotency_key: str


class RegisterProductRequest(BaseModel):
    display_name: str
    category: str = "Fresh Produce"
    unit_of_sale: str = "kg"  # kg or piece
    price_basis: str = "per_kg"  # per_kg or per_piece
    unit_price: float
    plu_code: Optional[str] = None
    retailer_sku: Optional[str] = None
    visual_class: Optional[str] = None
    store_id: str = "STORE-IN-001"
    feature_vector: Optional[List[float]] = None
    image_base64: Optional[str] = None


class AttendantOverrideRequest(BaseModel):
    actor_id: str
    pin: str
    action: str  # manual_item_assign, price_override, void_line
    line_id: Optional[str] = None
    catalog_item_id: Optional[str] = None
    override_amount: Optional[float] = None
    reason: str


class CheckoutRequest(BaseModel):
    transaction_id: str
    store_id: str = "STORE-IN-001"
    station_id: str = "STATION-BLR-01"
    tender_type: str = "POS_REDIRECT"


class CatalogItemModel(BaseModel):
    id: str
    retailer_sku: str
    display_name: str
    category: str
    unit_of_sale: str
    price_basis: str
    plu_code: Optional[str] = None
    current_price: Optional[float] = None
    price_version: Optional[str] = None
    active: bool = True
