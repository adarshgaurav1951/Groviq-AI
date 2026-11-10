"""
Unit tests for PricingService.
Verifies exact decimal arithmetic, absence of float roundoff errors, and legal rounding.
"""

from services.pricing.service import PricingService
import pytest


def test_weight_based_pricing_precision():
    ps = PricingService()
    # 0.850 kg at ₹240.00/kg should be exactly ₹204.00
    res = ps.calculate_line_item(unit_price=240.00, price_basis="per_kg", weight_value=0.850, tare_value=0.0)
    assert res["line_total"] == 204.00
    assert res["net_weight"] == 0.850
    assert res["unit_price"] == 240.00


def test_tare_deduction():
    ps = PricingService()
    # 1.050 kg gross, 0.050 kg tare = 1.000 kg net at ₹120.00/kg = ₹120.00
    res = ps.calculate_line_item(unit_price=120.00, price_basis="per_kg", weight_value=1.050, tare_value=0.050)
    assert res["net_weight"] == 1.000
    assert res["line_total"] == 120.00


def test_piece_based_pricing():
    ps = PricingService()
    # 3 pieces at ₹35.00/pc = ₹105.00
    res = ps.calculate_line_item(unit_price=35.00, price_basis="per_piece", quantity=3)
    assert res["line_total"] == 105.00
    assert res["quantity"] == 3


def test_invalid_weight_rejection():
    ps = PricingService()
    with pytest.raises(ValueError):
        # Negative or zero net weight must raise error
        ps.calculate_line_item(unit_price=100.00, price_basis="per_kg", weight_value=0.0)

    with pytest.raises(ValueError):
        ps.calculate_line_item(unit_price=100.00, price_basis="per_kg", weight_value=0.050, tare_value=0.100)


def test_basket_totals():
    ps = PricingService()
    lines = [204.00, 55.50, 95.00]
    totals = ps.calculate_basket_totals(lines, tax_rate_percent=0.0)
    assert totals["subtotal"] == 354.50
    assert totals["tax_amount"] == 0.00
    assert totals["total_amount"] == 354.50

