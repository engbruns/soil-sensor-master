"""Helpers for converting raw register values into user-facing measurements."""

from __future__ import annotations

from typing import Any, Dict, Optional


def to_signed_16(value: int) -> int:
    """Converts unsigned 16-bit register value to signed integer."""
    if value >= 0x8000:
        return value - 0x10000
    return value


def apply_calibration_model(value: float, calibration: Optional[Dict[str, Any]]) -> float:
    """Applies optional profile calibration model to already scaled value."""
    if not calibration:
        return value

    model = calibration.get("model")
    coeffs = calibration.get("coefficients", [])
    if not model or not isinstance(coeffs, list):
        return value

    try:
        if model == "linear" and len(coeffs) >= 2:
            a, b = coeffs[:2]
            return a * value + b
        if model == "poly2" and len(coeffs) >= 3:
            c, b, a = coeffs[:3]
            return a * value**2 + b * value + c
        if model == "poly3" and len(coeffs) >= 4:
            d, c, b, a = coeffs[:4]
            return a * value**3 + b * value**2 + c * value + d
    except Exception:
        return value

    return value


def convert_parameter_value(raw_value: int, param: Dict[str, Any], profile_data: Optional[Dict[str, Any]] = None) -> float:
    """
    Converts raw register value using parameter metadata:
    - optional signed 16-bit interpretation
    - factor/offset
    - optional profile calibration model for this parameter
    """
    signed_flag = param.get("signed")
    if signed_flag is None:
        # Sensible fallback for common SN-3002 profile keys.
        signed_flag = param.get("key") in {"temperature", "temp_calib"}
    value = to_signed_16(raw_value) if signed_flag else raw_value
    scaled = value * param.get("factor", 1) + param.get("offset", 0)

    calibration = None
    if profile_data:
        calibration_map = profile_data.get("calibration") or {}
        calibration = calibration_map.get(param.get("key"))

    return apply_calibration_model(float(scaled), calibration)
