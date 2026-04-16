# core/core_api.py
# API layer shared across modules.

from __future__ import annotations

import threading
from typing import Any, Dict, Optional, Tuple


class CoreAPI:
    """Central application API used by modules and UI layers."""

    def __init__(self, app, settings: Dict[str, Any], profile_manager, logger, tr):
        self.app = app
        self.settings = settings
        self.profile_manager = profile_manager
        self.logger = logger
        self.tr = tr

        self._sensors: Dict[str, Any] = {}
        self._current_sensor_name: Optional[str] = None
        self._lock = threading.RLock()

    def add_sensor(self, name: str, sensor) -> None:
        with self._lock:
            self._sensors[name] = sensor
            if self._current_sensor_name is None:
                self._current_sensor_name = name

    def remove_sensor(self, name: str) -> None:
        with self._lock:
            sensor = self._sensors.get(name)
            if sensor:
                try:
                    sensor.disconnect()
                except Exception:
                    pass
                del self._sensors[name]

            if self._current_sensor_name == name:
                self._current_sensor_name = next(iter(self._sensors), None)

    def get_sensor(self, name: Optional[str] = None):
        with self._lock:
            target_name = self._current_sensor_name if name is None else name
            return self._sensors.get(target_name)

    def list_sensors(self):
        with self._lock:
            return list(self._sensors.keys())

    def set_active_sensor(self, name: str) -> None:
        with self._lock:
            if name in self._sensors:
                self._current_sensor_name = name

    @property
    def sensor(self):
        """Backward compatibility for legacy code expecting single active sensor."""
        return self.get_sensor()

    @sensor.setter
    def sensor(self, value) -> None:
        # Legacy setter kept for compatibility. Use add_sensor/remove_sensor APIs.
        if value is None:
            return

    def get_current_profile_data(self, sensor_name: Optional[str] = None):
        sensor = self.get_sensor(sensor_name)
        return getattr(sensor, "profile_data", None) if sensor else None

    def get_sensor_by_port_and_address(self, port: str, addr: int) -> Tuple[Optional[str], Optional[Any]]:
        with self._lock:
            for name, sensor in self._sensors.items():
                if getattr(sensor, "port", None) == port and getattr(sensor, "slave_id", None) == addr:
                    return name, sensor
        return None, None

    def disconnect_all(self) -> None:
        with self._lock:
            for sensor in list(self._sensors.values()):
                try:
                    sensor.disconnect()
                except Exception:
                    pass
            self._sensors.clear()
            self._current_sensor_name = None

    def get_setting(self, key: str, default=None):
        """
        Reads setting by key.

        Supports dotted paths, e.g. "graph_settings.max_history".
        """
        data = self.settings
        try:
            for chunk in key.split("."):
                data = data[chunk]
            return data
        except Exception:
            return default

    def set_setting(self, key: str, value) -> None:
        """Writes setting by key. Supports dotted paths."""
        chunks = key.split(".")
        if not chunks:
            return

        data = self.settings
        for chunk in chunks[:-1]:
            if chunk not in data or not isinstance(data[chunk], dict):
                data[chunk] = {}
            data = data[chunk]
        data[chunks[-1]] = value
