from __future__ import annotations

import os
from collections import defaultdict
from typing import Dict, List, Optional

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt6.QtCore import QEvent, QTimer
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from qt_app.param_utils import ordered_param_keys, param_label
from qt_app.theme_utils import apply_matplotlib_theme, mark_styled_background
from qt_app.workers import MonitorPollThread
from utils.utils import log_error


class GraphSettingsDialog(QDialog):
    def __init__(
        self,
        graph_settings: Dict,
        param_keys: List[str],
        param_labels: Dict[str, str],
        texts: Dict[str, str],
        parent=None,
    ):
        super().__init__(parent)
        self._texts = dict(texts)
        self._param_labels = dict(param_labels)
        self.setWindowTitle(self._texts.get("settings_dialog_title", "Настройки графика"))

        self._default_limit = {
            "auto": True,
            "min": 0.0,
            "max": 100.0,
            "step": 10.0,
        }
        self._controls: Dict[str, Dict[str, QWidget]] = {}

        self.max_history_label = QLabel(self._texts.get("graph_max_points", "Макс. точек"))
        self.max_history_spin = QSpinBox()
        self.max_history_spin.setRange(10, 10000)
        self.max_history_spin.setValue(int(graph_settings.get("max_history", 300)))

        form = QFormLayout()
        form.addRow(self.max_history_label, self.max_history_spin)

        self.tabs = QTabWidget()

        y_limits = graph_settings.get("y_limits", {}) if isinstance(graph_settings, dict) else {}
        all_keys = ordered_param_keys({str(k) for k in list(param_keys) + list(y_limits.keys())})
        if all_keys:
            for key in all_keys:
                self._add_param_tab(key, y_limits.get(key, {}))
        else:
            empty = QWidget()
            empty_layout = QVBoxLayout(empty)
            empty_layout.addWidget(QLabel(self._texts.get("graph_empty_params", "Нет параметров для настройки")))
            empty_layout.addStretch(1)
            self.tabs.addTab(empty, "-")

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.tabs)
        layout.addWidget(buttons)

    def _sanitize_limit(self, raw: Dict) -> Dict:
        try:
            y_min = float(raw.get("min", self._default_limit["min"]))
        except Exception:
            y_min = self._default_limit["min"]

        try:
            y_max = float(raw.get("max", self._default_limit["max"]))
        except Exception:
            y_max = self._default_limit["max"]

        if y_max <= y_min:
            y_max = y_min + 1.0

        try:
            step = float(raw.get("step", self._default_limit["step"]))
        except Exception:
            step = self._default_limit["step"]

        return {
            "auto": bool(raw.get("auto", self._default_limit["auto"])),
            "min": y_min,
            "max": y_max,
            "step": max(0.1, step),
        }

    def _add_param_tab(self, param_key: str, raw_limit: Dict):
        page = QWidget()
        grid = QGridLayout(page)

        limit = self._sanitize_limit(raw_limit if isinstance(raw_limit, dict) else {})

        auto_cb = QCheckBox(self._texts.get("graph_auto", "Авто"))
        auto_cb.setChecked(bool(limit["auto"]))

        min_label = QLabel(self._texts.get("graph_min", "Мин"))
        max_label = QLabel(self._texts.get("graph_max", "Макс"))
        step_label = QLabel(self._texts.get("graph_step", "Шаг"))

        min_spin = QDoubleSpinBox()
        max_spin = QDoubleSpinBox()
        step_spin = QDoubleSpinBox()

        for spin in (min_spin, max_spin, step_spin):
            spin.setRange(-100000, 100000)
            spin.setDecimals(3)
            spin.setSingleStep(1.0)

        step_spin.setMinimum(0.1)

        min_spin.setValue(float(limit["min"]))
        max_spin.setValue(float(limit["max"]))
        step_spin.setValue(float(limit["step"]))

        grid.addWidget(auto_cb, 0, 0, 1, 2)
        grid.addWidget(min_label, 1, 0)
        grid.addWidget(min_spin, 1, 1)
        grid.addWidget(max_label, 2, 0)
        grid.addWidget(max_spin, 2, 1)
        grid.addWidget(step_label, 3, 0)
        grid.addWidget(step_spin, 3, 1)
        grid.setRowStretch(4, 1)

        controls = [min_spin, max_spin, step_spin, min_label, max_label, step_label]

        def apply_enabled(checked: bool):
            manual = not checked
            for control in controls:
                control.setEnabled(manual)

        auto_cb.toggled.connect(apply_enabled)
        apply_enabled(auto_cb.isChecked())

        self._controls[param_key] = {
            "auto": auto_cb,
            "min": min_spin,
            "max": max_spin,
            "step": step_spin,
        }
        self.tabs.addTab(page, self._param_labels.get(param_key, param_key))

    def values(self) -> Dict:
        y_limits = {}
        for param_key, controls in self._controls.items():
            y_min = float(controls["min"].value())
            y_max = float(controls["max"].value())
            if y_max <= y_min:
                y_max = y_min + 1.0

            y_limits[param_key] = {
                "auto": bool(controls["auto"].isChecked()),
                "min": y_min,
                "max": y_max,
                "step": max(0.1, float(controls["step"].value())),
            }

        return {
            "max_history": int(self.max_history_spin.value()),
            "y_limits": y_limits,
        }


class MonitorChartDialog(QDialog):
    def __init__(self, low_power: bool, parent=None):
        super().__init__(parent)
        self._low_power = low_power
        self.param_key = ""
        self.param_label = ""
        self._last_render = None

        root = QWidget()
        mark_styled_background(root, "dialogSurface")

        self.figure = Figure(figsize=(7.6, 4.2), dpi=90 if low_power else 100)
        self.axes = self.figure.add_subplot(111)
        self.canvas = FigureCanvasQTAgg(self.figure)

        layout = QVBoxLayout(root)
        layout.addWidget(self.canvas)

        outer = QVBoxLayout(self)
        outer.addWidget(root)

        self.resize(860, 520)

    def set_param(self, param_key: str, param_label: str, title_prefix: str):
        self.param_key = param_key
        self.param_label = param_label or param_key
        self.setWindowTitle(f"{title_prefix}: {self.param_label}")

    def _set_axis_ticks(self, axis: str, start: float, stop: float, step: float):
        if step <= 0 or stop <= start:
            return
        count = int((stop - start) / step)
        if count > 220:
            return

        import numpy as np

        ticks = np.arange(start, stop + step * 0.5, step)
        if axis == "x":
            self.axes.set_xticks(ticks)
        else:
            self.axes.set_yticks(ticks)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.PaletteChange and self._last_render is not None:
            self.render(*self._last_render)

    def render(
        self,
        no_data_text: str,
        axis_time: str,
        axis_value: str,
        series_map: Dict[str, List[float]],
        y_limits: Dict,
    ):
        self._last_render = (no_data_text, axis_time, axis_value, dict(series_map), dict(y_limits))
        self.axes.clear()

        color_cycle = [
            "#0ea5a5",
            "#2563eb",
            "#dc2626",
            "#16a34a",
            "#f59e0b",
            "#9333ea",
            "#0891b2",
        ]

        idx = 0
        for sensor_name, values in series_map.items():
            if not values:
                continue
            x = list(range(len(values)))
            color = color_cycle[idx % len(color_cycle)]
            self.axes.plot(x, values, color=color, label=sensor_name, linewidth=1.2 if self._low_power else 1.6)
            idx += 1

        if idx == 0:
            self.axes.text(0.5, 0.5, no_data_text, ha="center", va="center")
        else:
            self.axes.legend(loc="upper left", fontsize=8)

        self.axes.set_title(self.param_label or self.param_key)
        self.axes.set_xlabel(axis_time)
        self.axes.set_ylabel(axis_value)
        self.axes.grid(True, alpha=0.35)

        if not y_limits.get("auto", True):
            y_from = float(y_limits.get("min", 0.0))
            y_to = float(y_limits.get("max", 100.0))
            y_step = float(y_limits.get("step", 10.0))
            if y_to > y_from:
                self.axes.set_ylim(y_from, y_to)
                self._set_axis_ticks("y", y_from, y_to, y_step)

        apply_matplotlib_theme(self, self.figure, self.axes)
        self.canvas.draw_idle()


class MonitorTab(QWidget):
    def __init__(self, registry, settings, parent=None):
        super().__init__(parent)
        self.registry = registry
        self.settings = settings
        mark_styled_background(self, "modulePanel")

        self._low_power = (os.cpu_count() or 2) <= 4
        self._active = True
        self._poll_tick = 0
        self._lang = "ru"
        self._poll_worker: Optional[MonitorPollThread] = None
        self._poll_pending = False

        self._texts = {
            "group_monitor": "Мониторинг",
            "group_data": "Текущие данные",
            "poll_interval": "Интервал, мс:",
            "click_hint": "График открывается кликом по строке параметра",
            "btn_graph_settings": "Настройки графика",
            "settings_dialog_title": "Настройки графика",
            "header_state": "Состояние",
            "header_param": "Параметр",
            "no_sensors": "Нет подключенных датчиков",
            "chart_title": "График",
            "chart_no_data": "Нет данных для отображения",
            "axis_time": "t",
            "axis_value": "value",
            "graph_auto": "Авто",
            "graph_max_points": "Макс. точек",
            "graph_min": "Мин",
            "graph_max": "Макс",
            "graph_step": "Шаг",
            "graph_empty_params": "Нет параметров для настройки",
        }

        self.last_sensor_names: List[str] = []
        self.row_param_keys: List[str] = []
        self.last_good_data: Dict[str, Dict[str, Optional[float]]] = {}
        self.history: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))

        self.table = QTableWidget(0, 0)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)

        self.poll_interval = QSpinBox()
        self.poll_interval.setRange(500, 15000)
        self.poll_interval.setValue(2500 if self._low_power else 2000)
        self.poll_interval.setSingleStep(250)

        self.controls_group = QGroupBox(self._texts["group_monitor"])
        self.poll_label = QLabel(self._texts["poll_interval"])
        self.click_hint_label = QLabel(self._texts["click_hint"])
        self.btn_graph_settings = QPushButton(self._texts["btn_graph_settings"])

        self.data_group = QGroupBox(self._texts["group_data"])

        self.chart_dialog: Optional[MonitorChartDialog] = None

        self._load_graph_settings()
        self._build_ui()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll_once)
        self.timer.start(self.poll_interval.value())

    def set_language(self, language: str):
        self._lang = language if language in {"ru", "en", "zh"} else "ru"
        self._retranslate_param_rows()
        if self.chart_dialog and self.chart_dialog.param_key:
            self.chart_dialog.set_param(
                self.chart_dialog.param_key,
                self._param_label(self.chart_dialog.param_key),
                self._texts["chart_title"],
            )
            self._refresh_chart_dialog()

    def _param_label(self, key: str) -> str:
        return param_label(key, self._lang)

    def _default_graph_settings(self) -> Dict:
        return {
            "max_history": 300,
            "y_limits": {},
        }

    def _default_graph_window(self) -> Dict:
        return {
            "auto": True,
            "x_from": 0.0,
            "x_to": 120.0,
            "x_step": 10.0,
            "y_from": 0.0,
            "y_to": 100.0,
            "y_step": 10.0,
        }

    def _sanitize_limits(self, raw: Dict) -> Dict:
        try:
            y_min = float(raw.get("min", 0.0))
        except Exception:
            y_min = 0.0

        try:
            y_max = float(raw.get("max", 100.0))
        except Exception:
            y_max = 100.0

        if y_max <= y_min:
            y_max = y_min + 1.0

        try:
            step = float(raw.get("step", 10.0))
        except Exception:
            step = 10.0

        return {
            "auto": bool(raw.get("auto", True)),
            "min": y_min,
            "max": y_max,
            "step": max(0.1, step),
        }

    def _load_graph_settings(self):
        cfg = self.settings.setdefault("graph_settings", self._default_graph_settings())
        if not isinstance(cfg, dict):
            cfg = self._default_graph_settings()
            self.settings["graph_settings"] = cfg

        try:
            max_history = int(cfg.get("max_history", 300))
        except Exception:
            max_history = 300

        y_limits_cfg = cfg.get("y_limits", {})
        y_limits: Dict[str, Dict] = {}
        if isinstance(y_limits_cfg, dict):
            for key, limits in y_limits_cfg.items():
                if isinstance(limits, dict):
                    y_limits[str(key)] = self._sanitize_limits(limits)

        self._graph_settings_cfg = {
            "max_history": max(10, min(max_history, 10000)),
            "y_limits": y_limits,
        }

    def _graph_settings(self) -> Dict:
        return {
            "max_history": int(self._graph_settings_cfg.get("max_history", 300)),
            "y_limits": {
                key: dict(value)
                for key, value in self._graph_settings_cfg.get("y_limits", {}).items()
            },
        }

    def _graph_window(self) -> Dict:
        cfg = self.settings.get("graph_window", self._default_graph_window())
        if not isinstance(cfg, dict):
            return self._default_graph_window()
        base = self._default_graph_window()
        merged = dict(base)
        merged.update(cfg)
        return merged

    def _build_ui(self):
        controls_layout = QVBoxLayout(self.controls_group)
        form = QFormLayout()
        form.addRow(self.poll_label, self.poll_interval)
        controls_layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.btn_graph_settings)
        btn_row.addStretch(1)
        controls_layout.addLayout(btn_row)
        controls_layout.addWidget(self.click_hint_label)

        data_layout = QVBoxLayout(self.data_group)
        data_layout.addWidget(self.table)

        layout = QVBoxLayout(self)
        layout.addWidget(self.controls_group)
        layout.addWidget(self.data_group, 3)

        self.poll_interval.valueChanged.connect(self._on_poll_interval_changed)
        self.table.cellClicked.connect(self._on_table_cell_clicked)
        self.btn_graph_settings.clicked.connect(self._open_graph_settings_dialog)

    def _known_param_keys(self) -> List[str]:
        keys = set(self.row_param_keys)
        keys.update(self.history.keys())
        keys.update(self._graph_settings_cfg.get("y_limits", {}).keys())
        return ordered_param_keys(keys)

    def _param_graph_limits(self, param_key: str) -> Dict:
        limits = self._graph_settings_cfg.get("y_limits", {}).get(param_key)
        if isinstance(limits, dict):
            return dict(limits)
        return self._sanitize_limits({})

    def _open_graph_settings_dialog(self):
        keys = self._known_param_keys()
        labels = {k: self._param_label(k) for k in keys}
        dlg = GraphSettingsDialog(
            graph_settings=self._graph_settings_cfg,
            param_keys=keys,
            param_labels=labels,
            texts=self._texts,
            parent=self,
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        self._graph_settings_cfg = dlg.values()
        self.settings["graph_settings"] = self._graph_settings()

        if self.chart_dialog and self.chart_dialog.isVisible():
            self._refresh_chart_dialog()

    def set_texts(self, text_map: Dict[str, str]):
        self._texts.update(text_map)

        self.controls_group.setTitle(self._texts["group_monitor"])
        self.data_group.setTitle(self._texts["group_data"])

        self.poll_label.setText(self._texts["poll_interval"])
        self.click_hint_label.setText(self._texts["click_hint"])
        self.btn_graph_settings.setText(self._texts["btn_graph_settings"])

        if self.table.columnCount() <= 1:
            if self.table.columnCount() == 0:
                return
            self.table.setHorizontalHeaderLabels([self._texts["header_state"]])
            if self.table.rowCount() > 0 and self.table.item(0, 0):
                self.table.item(0, 0).setText(self._texts["no_sensors"])
        else:
            headers = [self._texts["header_param"]] + self.last_sensor_names
            self.table.setHorizontalHeaderLabels(headers)
            self._retranslate_param_rows()

        if self.chart_dialog and self.chart_dialog.param_key:
            self.chart_dialog.set_param(
                self.chart_dialog.param_key,
                self._param_label(self.chart_dialog.param_key),
                self._texts["chart_title"],
            )

    def _retranslate_param_rows(self):
        for row, key in enumerate(self.row_param_keys):
            item = self.table.item(row, 0)
            if item is None:
                self.table.setItem(row, 0, QTableWidgetItem(self._param_label(key)))
            else:
                item.setText(self._param_label(key))

    def set_active(self, active: bool):
        self._active = bool(active)
        if self._active:
            self.timer.start(self.poll_interval.value())
            self.poll_once()
        else:
            self.timer.stop()
            self._poll_pending = False

    def shutdown(self, wait_ms: int = 2500):
        self._active = False
        self.timer.stop()
        self._poll_pending = False

        worker = self._poll_worker
        if worker and worker.isRunning():
            worker.stop()
            if not worker.wait(wait_ms):
                log_error("Monitor poll worker did not stop before timeout")
                return

        if worker is not None and self._poll_worker is worker:
            self._poll_worker = None
            worker.deleteLater()

    def _on_poll_interval_changed(self, value: int):
        if self._active:
            self.timer.start(int(value))

    def on_sensors_changed(self):
        self.last_sensor_names = []
        if self._active:
            self.poll_once()

    def poll_once(self):
        if not self._active:
            return
        if self._poll_worker and self._poll_worker.isRunning():
            self._poll_pending = True
            return

        sensor_names = self.registry.list_connected_names()
        self._poll_worker = MonitorPollThread(self.registry, sensor_names=sensor_names)
        self._poll_worker.finished_with_result.connect(self._on_poll_finished)
        self._poll_worker.finished.connect(self._on_poll_worker_finished)
        self._poll_worker.start()

    def _on_poll_finished(
        self,
        _polled_names: List[str],
        polled_data: Dict[str, Optional[Dict[str, Optional[float]]]],
        polled_fresh_flags: Dict[str, bool],
        error_text: str,
    ):
        if error_text and error_text != "monitor poll cancelled":
            log_error(f"Monitor poll worker failed: {error_text}")

        if not self._active:
            return

        connected = self.registry.list_connected()
        names = [c.config.name for c in connected]

        if names != self.last_sensor_names:
            self._rebuild_table(connected)

        for stale_name in list(self.last_good_data.keys()):
            if stale_name not in names:
                self.last_good_data.pop(stale_name, None)

        all_data: Dict[str, Optional[Dict[str, Optional[float]]]] = {}
        fresh_flags: Dict[str, bool] = {}

        for sensor_name in names:
            data = polled_data.get(sensor_name)
            fresh = bool(polled_fresh_flags.get(sensor_name, False))

            if data and self._is_suspicious_snapshot(data):
                log_error(f"Monitor suspicious snapshot for {sensor_name}; fallback to last-good")
                data = None
                fresh = False

            if data is not None:
                self.last_good_data[sensor_name] = data
                all_data[sensor_name] = data
                fresh_flags[sensor_name] = fresh
            else:
                all_data[sensor_name] = self.last_good_data.get(sensor_name)
                fresh_flags[sensor_name] = False

        self._update_table_rows(names, all_data, fresh_flags)
        self._update_history(names, all_data, fresh_flags)

        self._poll_tick += 1
        if self.chart_dialog and self.chart_dialog.isVisible():
            if not self._low_power or (self._poll_tick % 2 == 0):
                self._refresh_chart_dialog()

    def _on_poll_worker_finished(self):
        worker = self._poll_worker
        self._poll_worker = None
        if worker is not None:
            worker.deleteLater()

        if self._active and self._poll_pending:
            self._poll_pending = False
            self.poll_once()

    def _is_suspicious_snapshot(self, data: Dict[str, Optional[float]]) -> bool:
        numeric = [float(v) for v in data.values() if isinstance(v, (int, float))]
        if len(numeric) < 4:
            return False
        rounded = {round(v, 3) for v in numeric}
        return len(rounded) == 1

    def _rebuild_table(self, connected):
        self.last_sensor_names = [c.config.name for c in connected]
        self.table.clear()
        self.table.setRowCount(0)

        if not connected:
            self.table.setColumnCount(1)
            self.table.setHorizontalHeaderLabels([self._texts["header_state"]])
            self.table.setRowCount(1)
            self.table.setItem(0, 0, QTableWidgetItem(self._texts["no_sensors"]))
            self.row_param_keys = []
            return

        all_params = []
        seen = set()
        for conn in connected:
            for p in conn.profile_data.get("parameters", []):
                key = p.get("key")
                if key and key not in seen:
                    seen.add(key)
                    all_params.append(key)

        self.row_param_keys = ordered_param_keys(all_params)
        self.table.setColumnCount(len(connected) + 1)
        self.table.setHorizontalHeaderLabels([self._texts["header_param"]] + [c.config.name for c in connected])
        self.table.setRowCount(len(self.row_param_keys))

        for row, key in enumerate(self.row_param_keys):
            self.table.setItem(row, 0, QTableWidgetItem(self._param_label(key)))
            for col in range(1, len(connected) + 1):
                self.table.setItem(row, col, QTableWidgetItem("---"))

    def _update_table_rows(self, names, all_data, fresh_flags):
        self.table.setUpdatesEnabled(False)
        try:
            for row, param_key in enumerate(self.row_param_keys):
                for col, sensor_name in enumerate(names, start=1):
                    value = None
                    sensor_data = all_data.get(sensor_name)
                    if sensor_data:
                        value = sensor_data.get(param_key)

                    text = "---"
                    if value is not None:
                        text = f"{value:.2f}" if isinstance(value, float) else str(value)
                        if not fresh_flags.get(sensor_name, False):
                            text = f"~{text}"

                    item = self.table.item(row, col)
                    if item is None:
                        item = QTableWidgetItem(text)
                        self.table.setItem(row, col, item)
                    elif item.text() != text:
                        item.setText(text)
        finally:
            self.table.setUpdatesEnabled(True)

    def _update_history(self, names, all_data, fresh_flags):
        max_hist = int(self._graph_settings_cfg.get("max_history", 300))
        if self._low_power:
            max_hist = min(max_hist, 180)

        for sensor_name in names:
            if not fresh_flags.get(sensor_name, False):
                continue
            sensor_data = all_data.get(sensor_name)
            if not sensor_data:
                continue
            for param_key, val in sensor_data.items():
                if val is None:
                    continue
                self.history[param_key][sensor_name].append(float(val))
                if len(self.history[param_key][sensor_name]) > max_hist:
                    self.history[param_key][sensor_name].pop(0)

    def _on_table_cell_clicked(self, row: int, _col: int):
        if row < 0 or row >= len(self.row_param_keys):
            return

        self._open_chart(self.row_param_keys[row])

    def _open_chart(self, param_key: str):
        if self.chart_dialog is None:
            self.chart_dialog = MonitorChartDialog(self._low_power, self)
            self.chart_dialog.destroyed.connect(self._on_chart_destroyed)

        self.chart_dialog.set_param(param_key, self._param_label(param_key), self._texts["chart_title"])
        self.chart_dialog.show()
        self.chart_dialog.raise_()
        self.chart_dialog.activateWindow()
        self._refresh_chart_dialog()

    def _on_chart_destroyed(self, *_):
        self.chart_dialog = None

    def _refresh_chart_dialog(self):
        if not self.chart_dialog or not self.chart_dialog.isVisible():
            return

        param = self.chart_dialog.param_key
        if not param:
            return

        self.chart_dialog.render(
            no_data_text=self._texts["chart_no_data"],
            axis_time=self._texts["axis_time"],
            axis_value=self._texts["axis_value"],
            series_map=self.history.get(param, {}),
            y_limits=self._param_graph_limits(param),
        )
