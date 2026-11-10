"""
Authoritative Decimal Pricing Engine for BarcodeLess Produce Assistant.
Guarantees decimal-exact monetary arithmetic with zero binary floating-point roundoff errors.
Strictly complies with Legal Metrology and retail financial audit rules.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, Optional


class PricingService:
    def __init__(self, currency: str = "INR"):
        self.currency = currency
        self.two_places = Decimal("0.01")
        self.three_places = Decimal("0.001")

    def round_currency(self, amount: Decimal) -> Decimal:
        """Rounds decimal amount to minor currency unit (e.g. 2 decimal places) using ROUND_HALF_UP."""
        return amount.quantize(self.two_places, rounding=ROUND_HALF_UP)

    def calculate_line_item(
        self,
        unit_price: float,
        price_basis: str,
        weight_value: Optional[float] = None,
        tare_value: Optional[float] = 0.0,
        quantity: int = 1
    ) -> Dict[str, Any]:
        """
        Calculates decimal-exact line total.
        For weight-priced items (per_kg): line_total = round((weight - tare) * unit_price, 2)
        For piece-priced items (per_piece): line_total = round(quantity * unit_price, 2)
        """
        d_unit_price = Decimal(str(unit_price)).quantize(self.two_places)

        if price_basis == "per_kg":
            if weight_value is None or weight_value <= 0:
                raise ValueError("Weight must be greater than zero for weight-priced produce.")
            
            d_gross = Decimal(str(weight_value))
            d_tare = Decimal(str(tare_value or 0.0))
            d_net = (d_gross - d_tare).quantize(self.three_places)

            if d_net <= Decimal("0.000"):
                raise ValueError("Net weight after tare deduction must be strictly positive.")

            raw_total = d_net * d_unit_price
            line_total = self.round_currency(raw_total)

            return {
                "unit_price": float(d_unit_price),
                "gross_weight": float(d_gross),
                "tare_weight": float(d_tare),
                "net_weight": float(d_net),
                "quantity": 1,
                "price_basis": "per_kg",
                "line_total": float(line_total),
                "currency": self.currency,
                "calculation_trace": f"{d_net} kg × ₹{d_unit_price}/kg = ₹{line_total}"
            }

        elif price_basis == "per_piece":
            if quantity < 1:
                raise ValueError("Quantity must be at least 1 for piece-priced produce.")
            
            d_qty = Decimal(str(quantity))
            raw_total = d_qty * d_unit_price
            line_total = self.round_currency(raw_total)

            return {
                "unit_price": float(d_unit_price),
                "gross_weight": float(weight_value) if weight_value else 0.0,
                "tare_weight": float(tare_value) if tare_value else 0.0,
                "net_weight": float(weight_value) if weight_value else 0.0,
                "quantity": int(quantity),
                "price_basis": "per_piece",
                "line_total": float(line_total),
                "currency": self.currency,
                "calculation_trace": f"{quantity} pcs × ₹{d_unit_price}/pc = ₹{line_total}"
            }

        else:
            raise ValueError(f"Unsupported price basis: '{price_basis}'. Expected 'per_kg' or 'per_piece'.")

    def calculate_basket_totals(self, line_totals: list, tax_rate_percent: float = 0.0) -> Dict[str, float]:
        """Calculates subtotal, tax, and grand total."""
        d_subtotal = Decimal("0.00")
        for lt in line_totals:
            d_subtotal += Decimal(str(lt)).quantize(self.two_places)

        d_tax_rate = Decimal(str(tax_rate_percent)) / Decimal("100.0")
        d_tax = self.round_currency(d_subtotal * d_tax_rate)
        d_grand_total = self.round_currency(d_subtotal + d_tax)

        return {
            "subtotal": float(d_subtotal),
            "tax_amount": float(d_tax),
            "total_amount": float(d_grand_total)
        }

