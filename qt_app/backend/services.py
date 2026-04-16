from __future__ import annotations

import threading
import time
import struct
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures

from .modbus_bus import ModbusBus
from utils.utils import log_error, safe_median
from utils.value_transform import convert_parameter_value


def parse_address_list(text: str) -> List[int]:
    addresses: List[int] = []
    for raw_part in text.split(","):
        part = raw_part.strip()
        if not part:
            continue
        if "-" in part:
            left, right = part.split("-", 1)
            lo = _parse_addr(left.strip())
            hi = _parse_addr(right.strip())
            if lo > hi:
                raise ValueError(f"Invalid range: {part}")
            addresses.extend(range(lo, hi + 1))
        else:
            addresses.append(_parse_addr(part))
    return sorted(set(addresses))


def _parse_addr(value: str) -> int:
    v = value.strip()
    if v.lower().startswith("0x"):
        return int(v, 16)
    try:
        return int(v, 10)
    except ValueError:
        return int(v, 16)


def scan_registers(
    sensor,
    addresses: Iterable[int],
    num_cycles: int,
    stop_event: Optional[threading.Event] = None,
    progress_callback=None,
) -> Tuple[List[Dict], bool]:
    addresses = list(addresses)
    raw_data: Dict[int, List[Optional[int]]] = {addr: [] for addr in addresses}

    if not sensor or not sensor.connected:
        return [], False

    for cycle in range(num_cycles):
        if stop_event and stop_event.is_set():
            return [], False

        for addr in addresses:
            if stop_event and stop_event.is_set():
                return [], False
            try:
                values = sensor.read_registers(addr, 1)
                if values and len(values) == 1:
                    raw_data[addr].append(values[0])
                else:
                    raw_data[addr].append(None)
            except Exception as exc:
                log_error(f"Scanner read error addr={addr}: {exc}")
                raw_data[addr].append(None)
            time.sleep(0.05)

        if progress_callback:
            progress_callback(int((cycle + 1) / num_cycles * 100))

        if cycle < num_cycles - 1:
            time.sleep(1.0)

    snapshot = []
    for addr in addresses:
        clean = [v for v in raw_data[addr] if v is not None]
        median = safe_median(clean) if clean else None
        snapshot.append(
            {
                "addr_dec": addr,
                "addr_hex": f"0x{addr:04X}",
                "value_dec": median,
                "value_hex": f"{int(median):04X}" if median is not None else "---",
                "raw_values": raw_data[addr],
            }
        )
    return snapshot, True


def collect_calibration_point(
    calib_sensor,
    calib_profile: Dict,
    selected_params: List[str],
    num_samples: int,
    ref_sensor=None,
    ref_profile: Optional[Dict] = None,
    stop_event: Optional[threading.Event] = None,
    progress_callback=None,
    sample_delay: float = 0.5,
):
    if not calib_sensor or not calib_sensor.connected:
        return None, None

    param_defs = {p["key"]: p for p in calib_profile.get("parameters", [])}
    ref_defs = {p["key"]: p for p in (ref_profile or {}).get("parameters", [])}

    raw_data = {param: [] for param in selected_params}
    ref_data = {param: [] for param in selected_params} if ref_sensor and ref_profile else None

    for i in range(num_samples):
        if stop_event and stop_event.is_set():
            return None, None

        for param in selected_params:
            p = param_defs.get(param)
            addr = p.get("address") if p else None
            if addr is None:
                raw_data[param].append(None)
                continue

            try:
                vals = calib_sensor.read_registers(addr, 1, function_code=p.get("function_code", 0x03))
                raw_data[param].append(vals[0] if vals and len(vals) == 1 else None)
            except Exception as exc:
                log_error(f"Calibration collect read failed ({param}): {exc}")
                raw_data[param].append(None)

        if ref_data is not None:
            for param in selected_params:
                p = ref_defs.get(param)
                addr = p.get("address") if p else None
                if addr is None:
                    ref_data[param].append(None)
                    continue
                try:
                    vals = ref_sensor.read_registers(addr, 1, function_code=p.get("function_code", 0x03))
                    ref_data[param].append(vals[0] if vals and len(vals) == 1 else None)
                except Exception as exc:
                    log_error(f"Calibration collect ref read failed ({param}): {exc}")
                    ref_data[param].append(None)

        if progress_callback:
            progress_callback(int((i + 1) / max(1, num_samples) * 100))

        if i < num_samples - 1:
            time.sleep(sample_delay)

    return _build_stats(raw_data), _build_stats(ref_data) if ref_data is not None else None


def collect_calibration_batch(
    target_entries: List[Dict],
    selected_params: List[str],
    num_samples: int,
    ref_sensor=None,
    ref_profile: Optional[Dict] = None,
    stop_event: Optional[threading.Event] = None,
    progress_callback=None,
    sample_delay: float = 0.5,
):
    active_targets = [entry for entry in target_entries if entry.get("sensor") and entry.get("profile")]
    if not active_targets:
        return None, None

    target_param_defs = {
        str(entry["name"]): {p["key"]: p for p in entry["profile"].get("parameters", [])}
        for entry in active_targets
    }
    raw_data = {
        str(entry["name"]): {param: [] for param in selected_params}
        for entry in active_targets
    }

    ref_defs = {p["key"]: p for p in (ref_profile or {}).get("parameters", [])}
    ref_data = {param: [] for param in selected_params} if ref_sensor and ref_profile else None

    total_steps = max(1, num_samples * len(selected_params) * (len(active_targets) + (1 if ref_data is not None else 0)))
    completed_steps = 0

    for sample_index in range(num_samples):
        if stop_event and stop_event.is_set():
            return None, None

        for entry in active_targets:
            sensor_name = str(entry["name"])
            sensor = entry["sensor"]
            defs = target_param_defs[sensor_name]
            for param in selected_params:
                if stop_event and stop_event.is_set():
                    return None, None
                param_def = defs.get(param)
                addr = param_def.get("address") if param_def else None
                if addr is None:
                    raw_data[sensor_name][param].append(None)
                else:
                    try:
                        vals = sensor.read_registers(addr, 1, function_code=param_def.get("function_code", 0x03))
                        raw_data[sensor_name][param].append(vals[0] if vals and len(vals) == 1 else None)
                    except Exception as exc:
                        log_error(f"Calibration batch read failed ({sensor_name}/{param}): {exc}")
                        raw_data[sensor_name][param].append(None)
                completed_steps += 1
                if progress_callback:
                    progress_callback(int(completed_steps / total_steps * 100))

        if ref_data is not None:
            for param in selected_params:
                if stop_event and stop_event.is_set():
                    return None, None
                param_def = ref_defs.get(param)
                addr = param_def.get("address") if param_def else None
                if addr is None:
                    ref_data[param].append(None)
                else:
                    try:
                        vals = ref_sensor.read_registers(addr, 1, function_code=param_def.get("function_code", 0x03))
                        ref_data[param].append(vals[0] if vals and len(vals) == 1 else None)
                    except Exception as exc:
                        log_error(f"Calibration batch ref read failed ({param}): {exc}")
                        ref_data[param].append(None)
                completed_steps += 1
                if progress_callback:
                    progress_callback(int(completed_steps / total_steps * 100))

        if sample_index < num_samples - 1:
            time.sleep(sample_delay)

    batch_stats = {sensor_name: _build_stats(param_map) for sensor_name, param_map in raw_data.items()}
    return batch_stats, _build_stats(ref_data) if ref_data is not None else None


def _build_stats(raw_map: Optional[Dict[str, List[Optional[int]]]]):
    if raw_map is None:
        return None
    stats = {}
    for param, values in raw_map.items():
        clean = [v for v in values if v is not None]
        if clean:
            stats[param] = {
                "median": safe_median(clean),
                "min": min(clean),
                "max": max(clean),
                "avg": sum(clean) / len(clean),
                "raw": values,
            }
        else:
            stats[param] = None
    return stats


def convert_stat_value(raw_value: Optional[float], param_def: Dict) -> Optional[float]:
    if raw_value is None:
        return None
    # For calibration workflow we keep engineering units only (without saved model).
    return convert_parameter_value(raw_value, param_def, None)


def build_regression_dataset(
    points: List[Dict],
    param_key: str,
    mode: str,
    param_defs: Dict[str, Dict],
    ref_param_defs: Dict[str, Dict],
    target_sensor: Optional[str] = None,
) -> Tuple[List[float], List[float]]:
    X: List[float] = []
    y: List[float] = []
    param_def = param_defs.get(param_key, {"key": param_key})
    ref_param_def = ref_param_defs.get(param_key, {"key": param_key})

    for point in points:
        raw_stats = None
        sensor_points = point.get("sensor_points")
        if isinstance(sensor_points, dict):
            sensor_name = target_sensor or next(iter(sensor_points.keys()), "")
            target_entry = sensor_points.get(sensor_name, {})
            if isinstance(target_entry, dict):
                raw_stats = target_entry.get("raw_stats", {}).get(param_key)
        else:
            raw_stats = point.get("raw_stats", {}).get(param_key)
        if not raw_stats:
            continue

        raw_median = raw_stats.get("median")
        conv = convert_stat_value(raw_median, param_def)
        if conv is None:
            continue

        if mode == "lab":
            ref_val = point.get("ref_values", {}).get(param_key)
            if ref_val is None:
                continue
            X.append(float(conv))
            y.append(float(ref_val))
        else:
            ref_stats = point.get("ref_stats", {}).get(param_key)
            if not ref_stats:
                continue
            ref_median = ref_stats.get("median")
            conv_ref = convert_stat_value(ref_median, ref_param_def)
            if conv_ref is None:
                continue
            X.append(float(conv))
            y.append(float(conv_ref))

    return X, y


def calculate_regression(X: List[float], y: List[float], model_type: str = "linear") -> Optional[Dict]:
    if len(X) < 2:
        return None

    Xnp = np.array(X).reshape(-1, 1)
    ynp = np.array(y)

    if model_type == "linear":
        model = LinearRegression()
        model.fit(Xnp, ynp)
        r2 = float(model.score(Xnp, ynp))
        return {
            "model": "linear",
            "coefficients": [float(model.coef_[0]), float(model.intercept_)],
            "r2": r2,
        }

    if model_type == "poly2":
        poly = PolynomialFeatures(degree=2)
        Xpoly = poly.fit_transform(Xnp)
        model = LinearRegression()
        model.fit(Xpoly, ynp)
        r2 = float(model.score(Xpoly, ynp))
        return {
            "model": "poly2",
            "coefficients": [float(model.intercept_)] + [float(v) for v in model.coef_[1:].tolist()],
            "r2": r2,
        }

    if model_type == "poly3":
        poly = PolynomialFeatures(degree=3)
        Xpoly = poly.fit_transform(Xnp)
        model = LinearRegression()
        model.fit(Xpoly, ynp)
        r2 = float(model.score(Xpoly, ynp))
        return {
            "model": "poly3",
            "coefficients": [float(model.intercept_)] + [float(v) for v in model.coef_[1:].tolist()],
            "r2": r2,
        }

    return None


def read_system_register_value(sensor, reg_def: Dict) -> Optional[float]:
    if not sensor or not getattr(sensor, "connected", False):
        return None

    address = int(reg_def.get("address", 0))
    function_code = int(reg_def.get("function_code", 0x03))

    if reg_def.get("type") == "float32":
        values = sensor.read_registers(address, 2, function_code=function_code)
        if not values or len(values) != 2:
            return None
        packed = struct.pack(">HH", int(values[0]), int(values[1]))
        return float(struct.unpack(">f", packed)[0])

    values = sensor.read_registers(address, 1, function_code=function_code)
    if not values or len(values) != 1:
        return None
    return convert_parameter_value(int(values[0]), reg_def, None)


def write_system_register_value(sensor, reg_def: Dict, engineering_value: float) -> bool:
    if not sensor or not getattr(sensor, "connected", False):
        raise ValueError("Sensor is not connected")

    if not reg_def.get("writable", True):
        raise ValueError("Register is read-only")

    if reg_def.get("type") == "float32":
        raise ValueError("float32 register writing is not supported in this build")

    factor = float(reg_def.get("factor", 1) or 1)
    offset = float(reg_def.get("offset", 0) or 0)
    if factor == 0:
        raise ValueError("Register factor cannot be zero")
    raw_value = (float(engineering_value) - offset) / factor
    rounded = round(raw_value)
    if abs(raw_value - rounded) > 1e-6:
        raise ValueError("Value cannot be represented by register step")

    raw_int = int(rounded)
    if "min" in reg_def and raw_int < int(reg_def["min"]):
        raise ValueError(f"Value is below minimum {reg_def['min']}")
    if "max" in reg_def and raw_int > int(reg_def["max"]):
        raise ValueError(f"Value is above maximum {reg_def['max']}")

    allowed_values = reg_def.get("values")
    if isinstance(allowed_values, list) and allowed_values and raw_int not in allowed_values:
        raise ValueError(f"Allowed values: {allowed_values}")

    if reg_def.get("signed"):
        if raw_int < -32768 or raw_int > 32767:
            raise ValueError("Signed register value is out of range")
        value_to_write = raw_int & 0xFFFF
    else:
        if raw_int < 0 or raw_int > 0xFFFF:
            raise ValueError("Register value is out of range")
        value_to_write = raw_int

    return bool(
        sensor.write_register(
            int(reg_def.get("address", 0)),
            int(value_to_write),
            function_code=int(reg_def.get("write_function_code", 0x06)),
        )
    )


def search_device_addresses(
    sensor=None,
    port: str | None = None,
    baudrate: int = 4800,
    timeout: float = 0.35,
    address_min: int = 1,
    address_max: int = 247,
    stop_event: Optional[threading.Event] = None,
    progress_callback=None,
) -> List[int]:
    address_min = max(1, int(address_min))
    address_max = min(247, int(address_max))
    if address_max < address_min:
        raise ValueError("Invalid address range")

    shared_bus = getattr(sensor, "bus", None) if sensor is not None else None
    temp_bus = None
    bus = shared_bus
    if bus is None:
        if not port:
            raise ValueError("Port is required")
        temp_bus = ModbusBus(port=port, baudrate=int(baudrate), timeout=float(timeout))
        bus = temp_bus

    try:
        if not bus.connect():
            raise ValueError("Failed to open Modbus bus")

        found: List[int] = []
        total = max(1, address_max - address_min + 1)
        for index, address in enumerate(range(address_min, address_max + 1), start=1):
            if stop_event and stop_event.is_set():
                break
            try:
                if bus.ping(address):
                    found.append(address)
            except Exception as exc:
                log_error(f"Address search failed for addr={address}: {exc}")

            if progress_callback:
                progress_callback(int(index / total * 100))
            time.sleep(0.03)
        return found
    finally:
        if temp_bus is not None:
            temp_bus.disconnect()
