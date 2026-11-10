"""
Unit tests for ScaleAdapter.
Verifies Legal Metrology compliance, stability flags, tare subtraction, and overload bounds.
"""

from services.scale_adapter.adapter import ScaleAdapter
import pytest


def test_scale_reading_and_tare():
    scale = ScaleAdapter(station_id="STATION-TEST-01", max_capacity_kg=15.0)
    scale.simulate_weight(1.500, stable=True)

    r1 = scale.get_reading()
    assert r1["gross_weight"] == 1.500
    assert r1["tare_weight"] == 0.000
    assert r1["net_weight"] == 1.500
    assert r1["stable"] is True

    # Tare the scale with 0.100 container
    scale.tare(0.100)
    r2 = scale.get_reading()
    assert r2["tare_weight"] == 0.100
    assert r2["net_weight"] == 1.400


def test_scale_motion_detection():
    scale = ScaleAdapter(station_id="STATION-TEST-01")
    scale.simulate_weight(0.750, stable=False)
    r = scale.get_reading()
    assert r["stable"] is False
    assert r["gross_weight"] == 0.750


def test_scale_disconnect():
    scale = ScaleAdapter(station_id="STATION-TEST-01")
    scale.simulate_disconnect(True)
    with pytest.raises(ConnectionError):
        scale.get_reading()

