from __future__ import annotations

import random
import threading
import time
from typing import Dict, List, Optional, Tuple

from utils.utils import log_error
from utils.value_transform import convert_parameter_value

from .models import ConnectedSensor, SensorConfig
from .modbus_bus import ModbusBus


class BusSensorDevice:
    """Device wrapper bound to one Modbus bus and slave address."""

    def __init__(self, name: str, bus: ModbusBus, slave_id: int):
        self.name = name
        self.bus = bus
        self.slave_id = int(slave_id)
        self.connected = False
        self.port = bus.port
        self.baudrate = bus.baudrate
        self.profile_data = None

    def connect(self) -> bool:
        self.connected = self.bus.connect()
        return self.connected

    def disconnect(self) -> None:
        self.connected = False

    def ping(self) -> bool:
        if not self.connected and not self.connect():
            return False
        return self.bus.ping(self.slave_id)

    def read_registers(self, start_addr: int, num_regs: int, function_code: int = 0x03):
        if not self.connected and not self.connect():
            return None
        return self.bus.read_holding_registers(
            slave_id=self.slave_id,
            start_addr=start_addr,
            count=num_regs,
            function_code=function_code,
        )

    def write_register(self, reg_addr: int, value: int, function_code: int = 0x06) -> bool:
        if not self.connected and not self.connect():
            return False
        return self.bus.write_single_register(
            slave_id=self.slave_id,
            reg_addr=reg_addr,
            value=value,
            function_code=function_code,
        )


class SimulatedSensorDevice:
    """Simple but stable simulator with low jitter per register."""

    def __init__(self, name: str, profile_data: Dict):
        self.name = name
        self.profile_data = profile_data
        self.connected = True
        self.port = f"sim:{name}"
        self.baudrate = 9600
        self.slave_id = 1
        self._random = random.Random(hash(name) & 0xFFFFFFFF)
        self._register_state: Dict[int, int] = {}

    def connect(self) -> bool:
        self.connected = True
        return True

    def disconnect(self) -> None:
        self.connected = False

    def ping(self) -> bool:
        return self.connected

    def _next_register_value(self, address: int) -> int:
        if address not in self._register_state:
            self._register_state[address] = self._random.randint(100, 500)
        current = self._register_state[address]
        current += self._random.randint(-4, 4)
        current = max(0, min(65535, current))
        self._register_state[address] = current
        return current

    def read_registers(self, start_addr: int, num_regs: int, function_code: int = 0x03):
        if not self.connected:
            return None
        return [self._next_register_value(start_addr + i) for i in range(num_regs)]

    def write_register(self, reg_addr: int, value: int, function_code: int = 0x06) -> bool:
        if not self.connected:
            return False
        self._register_state[reg_addr] = max(0, min(65535, int(value)))
        return True


class SensorRegistry:
    """Central registry for connected sensors and shared Modbus buses."""

    RECONNECT_FAILURE_THRESHOLD = 2
    RECONNECT_COOLDOWN_SEC = 4.0

    def __init__(self, profile_manager):
        self.profile_manager = profile_manager
        self._lock = threading.RLock()
        self._sensors: Dict[str, ConnectedSensor] = {}
        self._buses: Dict[Tuple[str, int], Dict] = {}

    def _mark_sensor_ok(self, connected: ConnectedSensor) -> None:
        with self._lock:
            connected.status = "connected"
            connected.last_error = None
            connected.consecutive_failures = 0
            connected.last_ok_at = time.time()

    def _mark_sensor_unstable(self, connected: ConnectedSensor, reason: str) -> None:
        with self._lock:
            connected.status = "unstable"
            connected.last_error = reason
            connected.consecutive_failures = 0
            connected.last_ok_at = time.time()

    def _mark_sensor_failed(self, connected: ConnectedSensor, reason: str) -> None:
        with self._lock:
            connected.status = "degraded"
            connected.last_error = reason
            connected.consecutive_failures += 1

    def _maybe_reconnect(self, connected: ConnectedSensor, reason: str) -> None:
        if connected.config.simulated:
            return

        with self._lock:
            if connected.consecutive_failures < self.RECONNECT_FAILURE_THRESHOLD:
                return
            now = time.time()
            if now - connected.last_reconnect_at < self.RECONNECT_COOLDOWN_SEC:
                return
            connected.last_reconnect_at = now
            connected.status = "reconnecting"

        try:
            connected.sensor.disconnect()
        except Exception:
            pass

        if not connected.sensor.connect():
            self._mark_sensor_failed(connected, f"{reason}; reconnect open failed")
            return

        if not connected.sensor.ping():
            self._mark_sensor_failed(connected, f"{reason}; reconnect ping failed")
            return

        self._mark_sensor_ok(connected)

    def get_sensor_health(self, name: str) -> Optional[Dict[str, object]]:
        connected = self.get_connected(name)
        if not connected:
            return None
        with self._lock:
            return {
                "name": connected.config.name,
                "status": connected.status,
                "last_error": connected.last_error,
                "consecutive_failures": int(connected.consecutive_failures),
                "connected_at": float(connected.connected_at),
                "last_ok_at": float(connected.last_ok_at),
                "last_reconnect_at": float(connected.last_reconnect_at),
            }

    def list_sensor_health(self) -> List[Dict[str, object]]:
        with self._lock:
            names = sorted(self._sensors.keys())
        items = []
        for name in names:
            payload = self.get_sensor_health(name)
            if payload is not None:
                items.append(payload)
        return items

    def list_connected_names(self) -> List[str]:
        with self._lock:
            return sorted(self._sensors.keys())

    def get_connected(self, name: str) -> Optional[ConnectedSensor]:
        with self._lock:
            return self._sensors.get(name)

    def list_connected(self) -> List[ConnectedSensor]:
        with self._lock:
            return [self._sensors[n] for n in sorted(self._sensors.keys())]

    def _acquire_bus(self, name: str, port: str, baudrate: int, timeout: float) -> Optional[ModbusBus]:
        key = (port, int(baudrate))
        entry = self._buses.get(key)
        if entry:
            entry["users"].add(name)
            return entry["bus"]

        bus = ModbusBus(port=port, baudrate=baudrate, timeout=timeout)
        self._buses[key] = {"bus": bus, "users": {name}}
        return bus

    def _release_bus(self, name: str, port: str, baudrate: int) -> None:
        key = (port, int(baudrate))
        entry = self._buses.get(key)
        if not entry:
            return

        users = entry["users"]
        users.discard(name)
        if not users:
            try:
                entry["bus"].disconnect()
            except Exception:
                pass
            self._buses.pop(key, None)

    def connect_sensor(self, config: SensorConfig) -> Tuple[bool, str]:
        with self._lock:
            if not config.name:
                return False, "Sensor name is required"

            if config.name in self._sensors:
                return False, f"Sensor '{config.name}' is already connected"

            for existing in self._sensors.values():
                if (
                    not config.simulated
                    and not existing.config.simulated
                    and existing.config.port == config.port
                    and int(existing.config.address) == int(config.address)
                ):
                    return False, f"Port/address already used by {existing.config.name}"

            profile_data = self.profile_manager.get_profile(config.profile)
            if not profile_data:
                return False, f"Profile not found: {config.profile}"

            sensor = None
            if config.simulated:
                sensor = SimulatedSensorDevice(config.name, profile_data)
            else:
                bus = self._acquire_bus(
                    name=config.name,
                    port=config.port,
                    baudrate=config.baudrate,
                    timeout=config.timeout,
                )
                sensor = BusSensorDevice(config.name, bus, config.address)

            sensor.profile_data = profile_data
            if not sensor.connect():
                if not config.simulated:
                    self._release_bus(config.name, config.port, config.baudrate)
                return False, f"Failed to connect sensor {config.name}"

            if not sensor.ping():
                sensor.disconnect()
                if not config.simulated:
                    self._release_bus(config.name, config.port, config.baudrate)
                return False, f"No response from sensor {config.name}"

            self._sensors[config.name] = ConnectedSensor(
                config=config,
                sensor=sensor,
                profile_data=profile_data,
                status="connected",
                last_error=None,
            )
            return True, "Connected"

    def disconnect_sensor(self, name: str) -> None:
        with self._lock:
            connected = self._sensors.pop(name, None)
            if not connected:
                return

            try:
                connected.sensor.disconnect()
            except Exception:
                pass

            if not connected.config.simulated:
                self._release_bus(
                    name=name,
                    port=connected.config.port,
                    baudrate=connected.config.baudrate,
                )

    def disconnect_all(self) -> None:
        with self._lock:
            names = list(self._sensors.keys())
        for name in names:
            self.disconnect_sensor(name)

    def read_parameter_values(self, name: str, apply_profile_calibration: bool = True) -> Optional[Dict[str, Optional[float]]]:
        connected = self.get_connected(name)
        if not connected:
            return None

        sensor = connected.sensor
        profile = connected.profile_data
        if not sensor or not sensor.connected or not profile:
            self._mark_sensor_failed(connected, "Sensor is not ready")
            self._maybe_reconnect(connected, "Sensor is not ready")
            return None

        result: Dict[str, Optional[float]] = {}
        success_count = 0
        failed_count = 0
        last_failure_reason = ""
        for param in profile.get("parameters", []):
            addr = param.get("address")
            if addr is None:
                continue
            try:
                values = sensor.read_registers(addr, 1, function_code=param.get("function_code", 0x03))
                if values and len(values) == 1:
                    raw = values[0]
                    profile_for_transform = profile if apply_profile_calibration else None
                    converted = convert_parameter_value(raw, param, profile_for_transform)
                    result[param["key"]] = converted
                    if converted is not None:
                        success_count += 1
                    else:
                        failed_count += 1
                        last_failure_reason = f"Converted value is None for {param.get('key')}"
                else:
                    result[param["key"]] = None
                    failed_count += 1
                    last_failure_reason = f"No response for {param.get('key')}"
            except Exception as exc:
                result[param["key"]] = None
                failed_count += 1
                last_failure_reason = f"{param.get('key')}: {exc}"
                log_error(f"Read parameter failed for {name}/{param.get('key')}: {exc}")

        if success_count == 0:
            reason = last_failure_reason or "No data from sensor"
            self._mark_sensor_failed(connected, reason)
            self._maybe_reconnect(connected, reason)
            return None

        if failed_count > 0:
            self._mark_sensor_unstable(connected, f"{failed_count} parameter reads failed")
        else:
            self._mark_sensor_ok(connected)

        return result

    def read_raw_register(self, name: str, address: int, count: int = 1):
        connected = self.get_connected(name)
        if not connected:
            return None
        try:
            values = connected.sensor.read_registers(address, count)
            if values and len(values) == int(count):
                self._mark_sensor_ok(connected)
                return values
            self._mark_sensor_failed(connected, f"No response while reading raw register {address}")
            self._maybe_reconnect(connected, f"Raw register read failed at {address}")
            return None
        except Exception as exc:
            self._mark_sensor_failed(connected, f"Raw read exception at {address}: {exc}")
            self._maybe_reconnect(connected, f"Raw read exception at {address}")
            log_error(f"Read raw register failed for {name} addr={address}: {exc}")
            return None

    def write_raw_register(self, name: str, address: int, value: int) -> bool:
        connected = self.get_connected(name)
        if not connected:
            return False
        try:
            ok = bool(connected.sensor.write_register(address, value))
            if ok:
                self._mark_sensor_ok(connected)
                return True
            self._mark_sensor_failed(connected, f"Raw write rejected at {address}")
            self._maybe_reconnect(connected, f"Raw write rejected at {address}")
            return False
        except Exception as exc:
            self._mark_sensor_failed(connected, f"Raw write exception at {address}: {exc}")
            self._maybe_reconnect(connected, f"Raw write exception at {address}")
            log_error(f"Write raw register failed for {name} addr={address}: {exc}")
            return False
