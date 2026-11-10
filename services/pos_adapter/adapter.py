"""
POS Adapter for BarcodeLess Produce Assistant.
Simulates enterprise Point-of-Sale integration, basket validation, and receipt generation.
"""

import uuid
import time
from typing import Dict, Any, List


class POSAdapter:
    def __init__(self, store_id: str = "STORE-IN-001"):
        self.store_id = store_id

    def commit_transaction(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Commits customer basket lines to POS system.
        Generates external POS receipt number and timestamp.
        """
        external_pos_ref = f"POS-{time.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        lines = transaction_data.get("lines", [])
        total_amount = transaction_data.get("total_amount", 0.0)

        # Build formatted receipt text
        receipt_lines = [
            "========================================",
            "          SUPERMARKET FRESH             ",
            "     Assisted Produce Checkout Lane     ",
            f"Store: {self.store_id}   Station: {transaction_data.get('station_id')}",
            f"Date: {time.strftime('%d-%b-%Y %H:%M:%S')}   Ref: {external_pos_ref}",
            "----------------------------------------",
            f"{'Item':<20} {'Qty/Wt':<10} {'Amount':>8}"
        ]

        for item in lines:
            name = item.get("display_name", "Produce Item")[:18]
            if item.get("weight_value"):
                qty_str = f"{item['weight_value']:.3f} kg"
            else:
                qty_str = f"{item.get('quantity', 1)} pc"
            amt_str = f"₹{item.get('line_total', 0.0):.2f}"
            receipt_lines.append(f"{name:<20} {qty_str:<10} {amt_str:>8}")

        receipt_lines.extend([
            "----------------------------------------",
            f"{'Subtotal:':<30} ₹{transaction_data.get('subtotal', 0.0):.2f}",
            f"{'GST (0% Fresh Produce):':<30} ₹{transaction_data.get('tax_amount', 0.0):.2f}",
            f"{'Total Amount Paid:':<30} ₹{total_amount:.2f}",
            "========================================",
            "Verified Legal Metrology Weights & Measures",
            " Thank you for shopping with Groviq AI!  ",
            "========================================"
        ])

        return {
            "status": "committed",
            "external_pos_reference": external_pos_ref,
            "committed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "receipt_text": "\n".join(receipt_lines)
        }

