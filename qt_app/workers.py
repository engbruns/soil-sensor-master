from __future__ import annotations

import threading
from typing import List, Optional

from PyQt6.QtCore import QThread, pyqtSignal

from .backend import services


class ScannerThread(QThread):
    progress_changed = pyqtSignal(int)
    finished_with_result = pyqtSignal(object, bool, str)

    def __init__(self, sensor, addresses: List[int], cycles: int):
        super().__init__()
        self.sensor = sensor
        self.addresses = addresses
        self.cycles = cycles
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def run(self):
        try:
            snapshot, ok = services.scan_registers(
                sensor=self.sensor,
                addresses=self.addresses,
                num_cycles=self.cycles,
                stop_event=self._stop_event,
                progress_callback=lambda p: self.progress_changed.emit(p),
            )
            self.finished_with_result.emit(snapshot, ok, "")
        except Exception as exc:
            self.finished_with_result.emit([], False, str(exc))


class CalibrationCollectThread(QThread):
    progress_changed = pyqtSignal(int)
    finished_with_result = pyqtSignal(object, object, str)

    def __init__(
        self,
        target_entries,
        selected_params,
        num_samples,
        ref_sensor=None,
        ref_profile=None,
    ):
        super().__init__()
        self.target_entries = list(target_entries or [])
        self.selected_params = selected_params
        self.num_samples = num_samples
        self.ref_sensor = ref_sensor
        self.ref_profile = ref_profile
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def run(self):
        try:
            raw_stats, ref_stats = services.collect_calibration_batch(
                target_entries=self.target_entries,
                selected_params=self.selected_params,
                num_samples=self.num_samples,
                ref_sensor=self.ref_sensor,
                ref_profile=self.ref_profile,
                stop_event=self._stop_event,
                progress_callback=lambda p: self.progress_changed.emit(p),
            )
            self.finished_with_result.emit(raw_stats, ref_stats, "")
        except Exception as exc:
            self.finished_with_result.emit(None, None, str(exc))


class MonitorPollThread(QThread):
    """Single monitor poll worker to keep serial I/O off the GUI thread."""

    finished_with_result = pyqtSignal(object, object, object, str)

    def __init__(self, registry, sensor_names: Optional[List[str]] = None):
        super().__init__()
        self.registry = registry
        self.sensor_names = list(sensor_names or [])
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def run(self):
        try:
            names = list(self.sensor_names)
            if not names:
                connected = self.registry.list_connected()
                names = [c.config.name for c in connected]

            all_data = {}
            fresh_flags = {}
            for sensor_name in names:
                if self._stop_event.is_set():
                    self.finished_with_result.emit([], {}, {}, "monitor poll cancelled")
                    return
                data = self.registry.read_parameter_values(sensor_name, apply_profile_calibration=True)
                if data is not None and not any(value is not None for value in data.values()):
                    data = None
                all_data[sensor_name] = data
                fresh_flags[sensor_name] = data is not None

            self.finished_with_result.emit(names, all_data, fresh_flags, "")
        except Exception as exc:
            self.finished_with_result.emit([], {}, {}, str(exc))
