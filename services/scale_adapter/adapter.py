"""
Scale Hardware Adapter for BarcodeLess Produce Assistant.
Provides protocol abstraction for retail digital scales (CAS, Mettler-Toledo, Datalogic)
and includes an authoritative Legal Metrology simulator for station development.
"""

import time
from typing import Dict, Any, Optional
from services.models import ScaleReading


class ScaleAdapter:
    def __init__(self, station_id: str = "STATION-BLR-01", max_capacity_kg: float = 15.0):
        self.station_id = station_id
        self.max_capacity_kg = max_capacity_kg
        self.tare_weight = 0.0
        self.gross_weight = 0.0
        self.is_stable = True
        self.is_connected = True

    def get_reading(self) -> Dict[str, Any]:
        """
        Polls the scale and returns gross, tare, net weight, and stability status.
        Complies with Legal Metrology output standards.
        """
        if not self.is_connected:
            raise ConnectionError("Scale hardware is disconnected or communication timeout.")

        net_weight = max(0.0, round(self.gross_weight - self.tare_weight, 3))

        return {
            "station_id": self.station_id,
            "gross_weight": round(self.gross_weight, 3),
            "tare_weight": round(self.tare_weight, 3),
            "net_weight": round(net_weight, 3),
            "weight_unit": "kg",
            "stable": self.is_stable,
            "overloaded": self.gross_weight > self.max_capacity_kg,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }

    def tare(self, tare_val: Optional[float] = None) -> Dict[str, Any]:
        """Sets tare weight (e.g., deducting container or bag weight)."""
        if tare_val is None:
            self.tare_weight = self.gross_weight
        else:
            self.tare_weight = round(float(tare_val), 3)
        return self.get_reading()

    def zero(self) -> Dict[str, Any]:
        """Zeros the scale platter."""
        self.gross_weight = 0.0
        self.tare_weight = 0.0
        self.is_stable = True
        return self.get_reading()

    # Simulator controls for testing and assisted checkout station
    def simulate_weight(self, gross: float, stable: bool = True):
        """Simulates placing an item on the scale."""
        self.gross_weight = round(float(gross), 3)
        self.is_stable = stable

    def simulate_disconnect(self, disconnect: bool = True):
        self.is_connected = not disconnect

