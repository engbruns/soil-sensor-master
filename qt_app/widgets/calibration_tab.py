from __future__ import annotations

import csv
import datetime
import json
import os
import tempfile
from typing import Dict, List, Optional

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt6.QtCore import QEvent, QTimer, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QSplitter,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)

from qt_app.backend import services
from qt_app.param_utils import ordered_param_keys, param_label
from qt_app.theme_utils import apply_matplotlib_theme, mark_styled_background
from qt_app.workers import CalibrationCollectThread
from .system_registers_dialog import SystemRegistersDialog


class ReferenceValuesDialog(QDialog):
    def __init__(self, params: List[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Эталонные значения")
        self._spins: Dict[str, QDoubleSpinBox] = {}

        root = QWidget()
        mark_styled_background(root, "dialogSurface")
        layout = QVBoxLayout(root)
        form = QFormLayout()

        for param in params:
            spin = QDoubleSpinBox()
            spin.setRange(-100000, 100000)
            spin.setDecimals(4)
            self._spins[param] = spin
            form.addRow(param, spin)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        outer = QVBoxLayout(self)
        outer.addWidget(root)

    def values(self) -> Dict[str, float]:
        return {k: float(v.value()) for k, v in self._spins.items()}


class CalibrationTab(QWidget):
    profiles_changed = pyqtSignal()
    COL_INDEX = 0
    COL_TIME = 1
    COL_TYPE = 2
    COL_SENSOR = 3
    COL_PARAM = 4
    COL_MEDIAN = 5
    COL_AVG = 6
    COL_MAX = 7
    COL_MIN = 8

    def __init__(self, registry, profile_manager, parent=None):
        super().__init__(parent)
        self.registry = registry
        self.profile_manager = profile_manager
        self._low_power = (os.cpu_count() or 2) <= 4
        self._lang = "ru"
        self._active = True

        mark_styled_background(self, "modulePanel")

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["lab", "ref"])

        self.calib_sensor_combo = QComboBox()
        self.lbl_active_sensor = QLabel("Датчик")
        self.lbl_targets = QLabel("Датчики в выборке")
        self.btn_add_target = QPushButton("Добавить датчик")
        self.btn_remove_target = QPushButton("Убрать датчик")
        self.targets_list = QListWidget()
        self.targets_list.setMaximumHeight(76)

        self.ref_sensor_combo = QComboBox()
        self.lbl_ref_sensor = QLabel("Эталон")

        self.samples_spin = QSpinBox()
        self.samples_spin.setRange(1, 100)
        self.samples_spin.setValue(8 if self._low_power else 10)

        self.btn_add_point = QPushButton("Собрать точки")
        self.btn_stop = QPushButton("Стоп")
        self.btn_stop.setEnabled(False)
        self.btn_system_registers = QPushButton("Системные регистры")
        self.progress = QProgressBar()

        self.params_box = QGroupBox("Параметры")
        mark_styled_background(self.params_box, "calibrationParamsBox")
        self.params_layout = QVBoxLayout(self.params_box)
        self.param_checks: Dict[str, QCheckBox] = {}

        self.params_scroll = QScrollArea()
        self.params_scroll.setObjectName("calibrationParamsScroll")
        self.params_scroll.viewport().setObjectName("calibrationParamsViewport")
        self.params_scroll.viewport().setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.params_scroll.setWidgetResizable(True)
        self.params_scroll.setWidget(self.params_box)
        self.params_scroll.setMinimumWidth(260)
        self.params_scroll.setMaximumWidth(360)

        self.points_table = QTableWidget(0, 9)
        self.points_table.setObjectName("calibrationPointsTable")
        self.points_table.setAlternatingRowColors(False)
        self.points_table.viewport().setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.points_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.points_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.points_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.points_table.verticalHeader().setVisible(False)
        self.points_table.verticalHeader().setDefaultSectionSize(28)
        self.points_table.setHorizontalHeaderLabels(
            [
                "№",
                "Время",
                "Датчик",
                "Параметр",
                "Тип",
                "Медиана",
                "Среднее",
                "Макс",
                "Мин",
                "Источник",
            ]
        )

        self.points_table.setHorizontalHeaderLabels(
            ["№", "Время", "Тип", "Датчик", "Параметр", "Медиана", "Среднее", "Макс", "Мин"]
        )

        self.graph_param_combo = QComboBox()
        self.graph_type_combo = QComboBox()
        self.graph_type_combo.addItems(["points", "regression"])

        self.model_combo = QComboBox()
        self.model_combo.addItems(["linear", "poly2", "poly3"])
        self.btn_remove_point = QPushButton("Удалить выбранную пробу")
        self.btn_remove_point.setEnabled(False)

        self.btn_calc = QPushButton("Рассчитать регрессию")
        self.btn_save = QPushButton("Сохранить калибровку")
        self.btn_export_csv = QPushButton("Экспорт CSV")
        self.btn_clear = QPushButton("Очистить точки")

        self.figure = Figure(figsize=(7.6, 4.6), dpi=90 if self._low_power else 100)
        self.axes = self.figure.add_subplot(111)
        self.figure.subplots_adjust(left=0.08, right=0.98, bottom=0.14, top=0.9)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setMinimumHeight(300)

        self.collect_thread: Optional[CalibrationCollectThread] = None
        self.points: List[Dict] = []
        self.calibration_results: Dict[str, Dict[str, Dict]] = {}
        self.param_defs: Dict[str, Dict] = {}
        self.ref_param_defs: Dict[str, Dict] = {}

        self._pending_target_entries: List[Dict] = []
        self._pending_selected_params: List[str] = []
        self._pending_ref_values: Optional[Dict[str, float]] = None
        self._pending_ref_name: str = ""
        self._pending_ref_param_defs: Dict[str, Dict] = {}
        self._collect_result_ready = False
        self._next_point_id = 1

        self._build_ui()
        self._wire()
        self._configure_points_table_columns()
        self._update_points_table_height()

    def _build_ui(self):
        top_box = QGroupBox("Режим и датчики")
        mark_styled_background(top_box)
        top = QGridLayout(top_box)

        top.addWidget(QLabel("Режим"), 0, 0)
        top.addWidget(self.mode_combo, 0, 1)
        top.addWidget(self.lbl_active_sensor, 0, 2)
        top.addWidget(self.calib_sensor_combo, 0, 3)
        top.addWidget(self.btn_add_target, 0, 4)
        top.addWidget(self.btn_remove_target, 0, 5)

        top.addWidget(self.lbl_targets, 1, 2)
        top.addWidget(self.targets_list, 1, 3, 1, 3)

        top.addWidget(self.lbl_ref_sensor, 2, 0)
        top.addWidget(self.ref_sensor_combo, 2, 1)
        top.addWidget(QLabel("Сэмплы"), 2, 2)
        top.addWidget(self.samples_spin, 2, 3)
        top.addWidget(self.btn_system_registers, 2, 4, 1, 2)

        top.addWidget(self.btn_add_point, 3, 0, 1, 2)
        top.addWidget(self.btn_stop, 3, 2)
        top.addWidget(self.progress, 3, 3, 1, 3)

        params_scroll = self.params_scroll
        params_scroll.setObjectName("calibrationParamsScroll")
        params_scroll.setWidgetResizable(True)
        params_scroll.setWidget(self.params_box)
        params_scroll.setMinimumWidth(260)
        params_scroll.setMaximumWidth(360)

        graph_controls_box = QGroupBox("Регрессия")
        mark_styled_background(graph_controls_box)
        graph_controls = QHBoxLayout(graph_controls_box)
        graph_controls.addWidget(QLabel("Параметр"))
        graph_controls.addWidget(self.graph_param_combo, 1)
        graph_controls.addWidget(QLabel("График"))
        graph_controls.addWidget(self.graph_type_combo)
        graph_controls.addWidget(QLabel("Модель"))
        graph_controls.addWidget(self.model_combo)
        graph_controls.addWidget(self.btn_calc)
        graph_controls.addWidget(self.btn_save)
        graph_controls.addWidget(self.btn_export_csv)
        graph_controls.addWidget(self.btn_remove_point)
        graph_controls.addWidget(self.btn_clear)

        chart_box = QGroupBox("График")
        mark_styled_background(chart_box)
        chart_layout = QVBoxLayout(chart_box)
        chart_layout.addWidget(self.canvas)

        points_box = QGroupBox("Точки")
        mark_styled_background(points_box, "calibrationPointsBox")
        points_layout = QVBoxLayout(points_box)
        points_layout.addWidget(self.points_table)

        graph_container = QWidget()
        mark_styled_background(graph_container)
        graph_container_layout = QVBoxLayout(graph_container)
        graph_container_layout.setContentsMargins(0, 0, 0, 0)
        graph_container_layout.addWidget(graph_controls_box)
        graph_container_layout.addWidget(chart_box, 1)

        content_splitter = QSplitter(Qt.Orientation.Vertical)
        content_splitter.setChildrenCollapsible(False)
        content_splitter.addWidget(points_box)
        content_splitter.addWidget(graph_container)
        content_splitter.setStretchFactor(0, 4)
        content_splitter.setStretchFactor(1, 5)

        layout = QVBoxLayout(self)
        top_row = QHBoxLayout()
        top_row.addWidget(top_box, 7)
        top_row.addWidget(params_scroll, 3)
        layout.addLayout(top_row)
        layout.addWidget(content_splitter, 1)

        self._apply_plot_theme()
        self._update_ref_visibility()

    def _wire(self):
        self.mode_combo.currentIndexChanged.connect(self._update_ref_visibility)
        self.calib_sensor_combo.currentIndexChanged.connect(self.on_calib_sensor_changed)
        self.ref_sensor_combo.currentIndexChanged.connect(self.on_ref_sensor_changed)
        self.graph_param_combo.currentIndexChanged.connect(self.update_graph)
        self.graph_type_combo.currentIndexChanged.connect(self.update_graph)
        self.points_table.itemSelectionChanged.connect(self._update_remove_point_button)

        self.btn_add_target.clicked.connect(self.add_target_from_combo)
        self.btn_remove_target.clicked.connect(self.remove_selected_target)

        self.btn_add_point.clicked.connect(self.on_add_point)
        self.btn_stop.clicked.connect(self.on_stop_collect)
        self.btn_system_registers.clicked.connect(self.open_system_registers)
        self.btn_calc.clicked.connect(self.on_calculate_regression)
        self.btn_save.clicked.connect(self.on_save_calibration)
        self.btn_export_csv.clicked.connect(self.export_points_csv)
        self.btn_remove_point.clicked.connect(self.remove_selected_point)
        self.btn_clear.clicked.connect(self.clear_points)

    def _mode(self) -> str:
        return self.mode_combo.currentText().strip()

    def _active_sensor_name(self) -> str:
        return self.calib_sensor_combo.currentText().strip()

    def _results_for_sensor(self, sensor_name: str, create: bool = False) -> Dict[str, Dict]:
        if not sensor_name:
            return {}
        if create:
            return self.calibration_results.setdefault(sensor_name, {})
        return self.calibration_results.get(sensor_name, {})

    def _point_sensor_names(self, point: Dict) -> List[str]:
        names = point.get("sensor_order") or list(point.get("sensor_points", {}).keys())
        if not names and point.get("sensor"):
            names = [point.get("sensor")]
        return [str(name) for name in names if name]

    def _visible_sensor_names(self) -> List[str]:
        seen = set()
        ordered: List[str] = []
        for point in self._active_points():
            for name in self._point_sensor_names(point):
                if name not in seen:
                    seen.add(name)
                    ordered.append(name)
        active_name = self._active_sensor_name()
        if active_name and active_name not in seen:
            ordered.insert(0, active_name)
        return ordered

    def _selected_point_id(self) -> Optional[int]:
        selected_items = self.points_table.selectedItems()
        if not selected_items:
            return None
        point_id = selected_items[0].data(Qt.ItemDataRole.UserRole)
        return int(point_id) if point_id is not None else None

    def _update_remove_point_button(self):
        self.btn_remove_point.setEnabled(self._selected_point_id() is not None)

    def set_language(self, language: str):
        self._lang = language if language in {"ru", "en", "zh"} else "ru"
        self._rebuild_param_checks()
        self._refresh_points_table()
        self.update_graph()

    def set_active(self, active: bool):
        self._active = bool(active)
        if not self._active and self.collect_thread and self.collect_thread.isRunning():
            self.on_stop_collect()

    def _configure_points_table_columns(self):
        header = self.points_table.horizontalHeader()
        header.setSectionResizeMode(self.COL_INDEX, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COL_TIME, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COL_TYPE, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COL_SENSOR, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(self.COL_PARAM, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(self.COL_MEDIAN, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COL_AVG, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COL_MAX, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COL_MIN, QHeaderView.ResizeMode.ResizeToContents)

    def _update_points_table_height(self):
        row_count = self.points_table.rowCount()
        visible_rows = max(1, min(row_count if row_count > 0 else 1, 10))
        row_height = self.points_table.verticalHeader().defaultSectionSize()
        header_height = self.points_table.horizontalHeader().height()
        frame = self.points_table.frameWidth() * 2
        total_height = header_height + row_height * visible_rows + frame + 8

        if row_count > 10:
            self.points_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            self.points_table.setMinimumHeight(total_height)
            self.points_table.setMaximumHeight(total_height)
        else:
            self.points_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.points_table.setMinimumHeight(total_height)
            self.points_table.setMaximumHeight(16777215)

    def _param_label(self, key: str) -> str:
        return param_label(key, self._lang)

    def _current_graph_param_key(self) -> str:
        data = self.graph_param_combo.currentData()
        if isinstance(data, str) and data:
            return data
        txt = self.graph_param_combo.currentText().strip()
        if txt in self.param_defs:
            return txt
        return ""

    def _update_ref_visibility(self):
        show_ref = self._mode() == "ref"
        self.lbl_ref_sensor.setVisible(show_ref)
        self.ref_sensor_combo.setVisible(show_ref)
        self._refresh_points_table()
        self.update_graph()

    def on_sensors_changed(self):
        names = self.registry.list_connected_names()

        current_calib = self.calib_sensor_combo.currentText()
        current_ref = self.ref_sensor_combo.currentText()

        self.calib_sensor_combo.clear()
        self.calib_sensor_combo.addItems(names)
        if current_calib in names:
            self.calib_sensor_combo.setCurrentText(current_calib)

        self.ref_sensor_combo.clear()
        self.ref_sensor_combo.addItems(names)
        if current_ref in names:
            self.ref_sensor_combo.setCurrentText(current_ref)

        self._prune_targets(names)
        if self.targets_list.count() == 0 and self.calib_sensor_combo.currentText().strip():
            self._add_target_name(self.calib_sensor_combo.currentText().strip())

        self.on_calib_sensor_changed()
        self.on_ref_sensor_changed()

    def _prune_targets(self, available_names: List[str]):
        allowed = set(available_names)
        for i in reversed(range(self.targets_list.count())):
            item = self.targets_list.item(i)
            if item and item.text() not in allowed:
                self.targets_list.takeItem(i)

    def _target_names(self) -> List[str]:
        names = []
        for i in range(self.targets_list.count()):
            item = self.targets_list.item(i)
            if item:
                names.append(item.text())
        return names

    def _add_target_name(self, name: str):
        if not name:
            return
        if name in self._target_names():
            return
        self.targets_list.addItem(QListWidgetItem(name))

    def add_target_from_combo(self):
        name = self.calib_sensor_combo.currentText().strip()
        if not name:
            return
        self._add_target_name(name)

    def remove_selected_target(self):
        row = self.targets_list.currentRow()
        if row >= 0:
            removed = self.targets_list.item(row)
            removed_name = removed.text() if removed else ""
            self.targets_list.takeItem(row)
            remaining = self._target_names()
            if removed_name and removed_name == self._active_sensor_name() and remaining:
                self.calib_sensor_combo.setCurrentText(remaining[0])

    def selected_target_names(self) -> List[str]:
        names = self._target_names()
        active_name = self._active_sensor_name()
        if active_name and active_name not in names:
            names.insert(0, active_name)
            self._add_target_name(active_name)
        return names

    def on_calib_sensor_changed(self):
        name = self._active_sensor_name()
        connected = self.registry.get_connected(name) if name else None

        self.param_defs = {}
        if connected:
            self.param_defs = {p["key"]: p for p in connected.profile_data.get("parameters", [])}
            self._add_target_name(name)

        self._rebuild_param_checks()
        self._refresh_points_table()
        self.update_graph()

    def on_ref_sensor_changed(self):
        name = self.ref_sensor_combo.currentText().strip()
        connected = self.registry.get_connected(name) if name else None

        self.ref_param_defs = {}
        if connected:
            self.ref_param_defs = {p["key"]: p for p in connected.profile_data.get("parameters", [])}

    def _rebuild_param_checks(self):
        while self.params_layout.count():
            item = self.params_layout.takeAt(0)
            widget = item.widget() if item else None
            if widget:
                widget.deleteLater()

        self.param_checks.clear()

        ordered_keys = ordered_param_keys(self.param_defs.keys())
        for key in ordered_keys:
            cb = QCheckBox(self._param_label(key))
            self.params_layout.addWidget(cb)
            self.param_checks[key] = cb
        self.params_layout.addStretch(1)

        current_key = self._current_graph_param_key()
        self.graph_param_combo.blockSignals(True)
        self.graph_param_combo.clear()
        for key in ordered_keys:
            self.graph_param_combo.addItem(self._param_label(key), key)
        if current_key in self.param_defs:
            idx = self.graph_param_combo.findData(current_key)
            if idx >= 0:
                self.graph_param_combo.setCurrentIndex(idx)
        elif ordered_keys:
            self.graph_param_combo.setCurrentIndex(0)
        self.graph_param_combo.blockSignals(False)

    def selected_params(self) -> List[str]:
        return [k for k, cb in self.param_checks.items() if cb.isChecked()]

    def open_system_registers(self):
        sensor_name = self.calib_sensor_combo.currentText().strip()
        connected = self.registry.get_connected(sensor_name) if sensor_name else None
        if not connected:
            QMessageBox.warning(self, "Калибровка", "Выберите подключенный датчик.")
            return

        profile_data = connected.profile_data or {}
        if not profile_data.get("system_registers"):
            QMessageBox.information(self, "Калибровка", "У текущего профиля нет системных регистров.")
            return

        dialog = SystemRegistersDialog(sensor_name, connected.sensor, profile_data, self)
        dialog.exec()

    def on_add_point(self):
        if self.collect_thread and self.collect_thread.isRunning():
            QMessageBox.warning(self, "Калибровка", "Сбор уже выполняется")
            return

        params = self.selected_params()
        if not params:
            QMessageBox.warning(self, "Калибровка", "Выберите параметры")
            return

        target_names = self.selected_target_names()
        if not target_names:
            QMessageBox.warning(self, "Калибровка", "Добавьте хотя бы один датчик в выборку")
            return

        target_entries: List[Dict] = []
        for name in target_names:
            connected = self.registry.get_connected(name)
            if not connected:
                QMessageBox.warning(self, "Калибровка", f"Датчик не подключен: {name}")
                return
            target_entries.append(
                {
                    "name": name,
                    "sensor": connected.sensor,
                    "profile": connected.profile_data or {},
                }
            )

        ref_connected = None
        ref_name = ""
        ref_param_defs: Dict[str, Dict] = {}
        if self._mode() == "ref":
            ref_name = self.ref_sensor_combo.currentText().strip()
            ref_connected = self.registry.get_connected(ref_name) if ref_name else None
            if not ref_connected:
                QMessageBox.warning(self, "Калибровка", "Выберите подключенный эталонный датчик")
                return
            ref_param_defs = {p["key"]: p for p in (ref_connected.profile_data or {}).get("parameters", [])}

        ref_values = None
        if self._mode() == "lab":
            dlg = ReferenceValuesDialog(params, self)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return
            ref_values = dlg.values()

        self._pending_target_entries = target_entries
        self._pending_selected_params = list(params)
        self._pending_ref_values = ref_values
        self._pending_ref_name = ref_name
        self._pending_ref_param_defs = ref_param_defs

        self.btn_add_point.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_remove_point.setEnabled(False)
        self.progress.setValue(0)

        self.collect_thread = CalibrationCollectThread(
            target_entries=target_entries,
            selected_params=self._pending_selected_params,
            num_samples=int(self.samples_spin.value()),
            ref_sensor=ref_connected.sensor if ref_connected else None,
            ref_profile=ref_connected.profile_data if ref_connected else None,
        )
        self.collect_thread.progress_changed.connect(self.progress.setValue)
        self.collect_thread.finished_with_result.connect(self._on_collect_finished)
        self.collect_thread.finished.connect(self._on_collect_thread_finished)
        self._collect_result_ready = False
        self.collect_thread.start()

    def on_stop_collect(self):
        self._collect_result_ready = False
        if self.collect_thread and self.collect_thread.isRunning():
            self.collect_thread.stop()
        else:
            self.btn_add_point.setEnabled(True)
            self.btn_stop.setEnabled(False)
            self.progress.setValue(0)

    def _on_collect_finished(self, raw_stats, ref_stats, error_text: str):
        if error_text:
            QMessageBox.critical(self, "Калибровка", error_text)
            self.progress.setValue(0)
        elif raw_stats is None:
            QMessageBox.warning(self, "Калибровка", "Сбор прерван")
            self.progress.setValue(0)
        else:
            sensor_order = [str(entry.get("name", "")) for entry in self._pending_target_entries if entry.get("name")]
            sensor_points = {}
            for entry in self._pending_target_entries:
                sensor_name = str(entry.get("name", ""))
                if not sensor_name:
                    continue
                profile = entry.get("profile") or {}
                sensor_points[sensor_name] = {
                    "raw_stats": (raw_stats or {}).get(sensor_name) or {},
                    "param_defs": {p["key"]: p for p in profile.get("parameters", [])},
                }

            point = {
                "id": self._next_point_id,
                "mode": self._mode(),
                "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
                "selected_params": list(self._pending_selected_params),
                "sensor_order": sensor_order,
                "sensor_points": sensor_points,
            }

            if self._mode() == "lab":
                point["ref_values"] = dict(self._pending_ref_values or {})
                point["ref_sensor"] = "Эталон"
            else:
                point["ref_stats"] = ref_stats or {}
                point["ref_sensor"] = self._pending_ref_name
                point["ref_param_defs"] = dict(self._pending_ref_param_defs)

            self.points.append(point)
            self._next_point_id += 1
            self.calibration_results.clear()
            self.progress.setValue(100)
            self._refresh_points_table()
            self.update_graph()

        self._collect_result_ready = True

    def _on_collect_thread_finished(self):
        if not self._collect_result_ready:
            QTimer.singleShot(0, self._on_collect_thread_finished)
            return

        thread = self.collect_thread
        if thread is not None:
            thread.deleteLater()
        self.collect_thread = None
        self._pending_target_entries = []
        self._pending_selected_params = []
        self._pending_ref_values = None
        self._pending_ref_name = ""
        self._pending_ref_param_defs = {}
        self.btn_add_point.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self._update_remove_point_button()

    def _active_points(self) -> List[Dict]:
        mode = self._mode()
        return [p for p in self.points if p.get("mode", "lab") == mode]

    def _sensor_entry_for_point(self, point: Dict, sensor_name: str) -> Dict:
        sensor_points = point.get("sensor_points")
        if isinstance(sensor_points, dict):
            entry = sensor_points.get(sensor_name)
            if isinstance(entry, dict):
                return entry
        if point.get("sensor") == sensor_name:
            return {"raw_stats": point.get("raw_stats", {})}
        return {}

    def _sensor_param_defs_for_point(self, point: Dict, sensor_name: str) -> Dict[str, Dict]:
        entry = self._sensor_entry_for_point(point, sensor_name)
        point_defs = entry.get("param_defs") if isinstance(entry, dict) else None
        if isinstance(point_defs, dict) and point_defs:
            return point_defs
        connected = self.registry.get_connected(sensor_name) if sensor_name else None
        if connected:
            return {p["key"]: p for p in (connected.profile_data or {}).get("parameters", [])}
        if sensor_name == self._active_sensor_name():
            return self.param_defs
        return {}

    def _convert_sensor_raw(self, point: Dict, sensor_name: str, raw_value: Optional[float], param_key: str) -> Optional[float]:
        if raw_value is None:
            return None
        defs = self._sensor_param_defs_for_point(point, sensor_name)
        param_def = defs.get(param_key, {"key": param_key})
        return services.convert_stat_value(raw_value, param_def)

    def _convert_ref_raw_for_point(self, point: Dict, raw_value: Optional[float], param_key: str) -> Optional[float]:
        if raw_value is None:
            return None
        defs = point.get("ref_param_defs") or self.ref_param_defs
        param_def = defs.get(param_key, {"key": param_key})
        return services.convert_stat_value(raw_value, param_def)

    def _row_display_text(self, value) -> str:
        if isinstance(value, float):
            return f"{value:.4f}"
        return "" if value is None else str(value)

    def _csv_value(self, value) -> str:
        return self._row_display_text(value)

    def _max_export_samples(self, points: List[Dict]) -> int:
        max_samples = 0
        for point in points:
            for sensor_name in self._point_sensor_names(point):
                sensor_entry = self._sensor_entry_for_point(point, sensor_name)
                raw_stats = sensor_entry.get("raw_stats", {}) if isinstance(sensor_entry, dict) else {}
                for raw_stat in raw_stats.values():
                    if raw_stat:
                        max_samples = max(max_samples, len(raw_stat.get("raw", [])))
            for ref_stat in point.get("ref_stats", {}).values():
                if ref_stat:
                    max_samples = max(max_samples, len(ref_stat.get("raw", [])))
        return max_samples

    def _append_export_row(self, writer, row_prefix: List[str], raw_values: List[Optional[float]], max_samples: int):
        row = list(row_prefix)
        for value in raw_values:
            row.append(self._csv_value(value))
        for _ in range(max(0, max_samples - len(raw_values))):
            row.append("")
        writer.writerow(row)

    def _write_points_csv(self, filename: str):
        points = self._active_points()
        if not points:
            raise ValueError("Нет точек для экспорта")

        max_samples = self._max_export_samples(points)
        header = ["Проба", "ID", "Время", "Режим", "Тип", "Датчик", "Параметр", "Медиана", "Среднее", "Макс", "Мин"]
        for i in range(max_samples):
            header.append(f"Значение {i + 1}")

        target_dir = os.path.dirname(filename) or "."
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                newline="",
                encoding="utf-8-sig",
                dir=target_dir,
                delete=False,
                suffix=".tmp",
            ) as handle:
                temp_path = handle.name
                writer = csv.writer(handle)
                writer.writerow(header)

                for point_num, point in enumerate(points, start=1):
                    point_id = int(point.get("id", point_num))
                    timestamp = point.get("timestamp", "")
                    mode = point.get("mode", self._mode())
                    params = point.get("selected_params", [])

                    if mode == "lab":
                        ref_label = point.get("ref_sensor") or "Эталон"
                        for param in params:
                            ref_value = point.get("ref_values", {}).get(param)
                            if ref_value is None:
                                continue
                            self._append_export_row(
                                writer,
                                [
                                    str(point_num),
                                    str(point_id),
                                    str(timestamp),
                                    str(mode),
                                    "ref",
                                    str(ref_label),
                                    self._param_label(param),
                                    self._csv_value(ref_value),
                                    self._csv_value(ref_value),
                                    self._csv_value(ref_value),
                                    self._csv_value(ref_value),
                                ],
                                [],
                                max_samples,
                            )
                    else:
                        ref_label = point.get("ref_sensor") or "ref"
                        for param in params:
                            ref_stat = point.get("ref_stats", {}).get(param)
                            if not ref_stat:
                                continue
                            raw_values = [
                                self._convert_ref_raw_for_point(point, raw_value, param) if raw_value is not None else None
                                for raw_value in ref_stat.get("raw", [])
                            ]
                            self._append_export_row(
                                writer,
                                [
                                    str(point_num),
                                    str(point_id),
                                    str(timestamp),
                                    str(mode),
                                    "ref",
                                    str(ref_label),
                                    self._param_label(param),
                                    self._csv_value(self._convert_ref_raw_for_point(point, ref_stat.get("median"), param)),
                                    self._csv_value(self._convert_ref_raw_for_point(point, ref_stat.get("avg"), param)),
                                    self._csv_value(self._convert_ref_raw_for_point(point, ref_stat.get("max"), param)),
                                    self._csv_value(self._convert_ref_raw_for_point(point, ref_stat.get("min"), param)),
                                ],
                                raw_values,
                                max_samples,
                            )

                    for sensor_name in self._point_sensor_names(point):
                        sensor_entry = self._sensor_entry_for_point(point, sensor_name)
                        raw_stats = sensor_entry.get("raw_stats", {}) if isinstance(sensor_entry, dict) else {}
                        for param in params:
                            raw_stat = raw_stats.get(param)
                            if not raw_stat:
                                continue
                            raw_values = [
                                self._convert_sensor_raw(point, sensor_name, raw_value, param) if raw_value is not None else None
                                for raw_value in raw_stat.get("raw", [])
                            ]
                            self._append_export_row(
                                writer,
                                [
                                    str(point_num),
                                    str(point_id),
                                    str(timestamp),
                                    str(mode),
                                    "sensor",
                                    str(sensor_name),
                                    self._param_label(param),
                                    self._csv_value(self._convert_sensor_raw(point, sensor_name, raw_stat.get("median"), param)),
                                    self._csv_value(self._convert_sensor_raw(point, sensor_name, raw_stat.get("avg"), param)),
                                    self._csv_value(self._convert_sensor_raw(point, sensor_name, raw_stat.get("max"), param)),
                                    self._csv_value(self._convert_sensor_raw(point, sensor_name, raw_stat.get("min"), param)),
                                ],
                                raw_values,
                                max_samples,
                            )

            os.replace(temp_path, filename)
            temp_path = None
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    def export_points_csv(self):
        points = self._active_points()
        if not points:
            QMessageBox.information(self, "Калибровка", "Нет точек для экспорта")
            return

        default_name = f"calibration_{self._mode()}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Экспорт CSV",
            default_name,
            "CSV files (*.csv)",
        )
        if not filename:
            return
        if not filename.lower().endswith(".csv"):
            filename += ".csv"

        try:
            self._write_points_csv(filename)
        except Exception as exc:
            QMessageBox.critical(self, "Калибровка", f"Не удалось экспортировать CSV:\n{exc}")
            return

        QMessageBox.information(self, "Калибровка", f"CSV сохранен:\n{filename}")
    def remove_selected_point(self):
        point_id = self._selected_point_id()
        if point_id is None:
            QMessageBox.information(self, "Калибровка", "Выберите пробу в таблице")
            return

        self.points = [point for point in self.points if int(point.get("id", -1)) != point_id]
        self.calibration_results.clear()
        self._refresh_points_table()
        self.update_graph()
    def _convert_raw(self, raw_value: Optional[float], param_key: str, ref: bool = False) -> Optional[float]:
        if raw_value is None:
            return None
        defs = self.ref_param_defs if ref else self.param_defs
        param_def = defs.get(param_key, {"key": param_key})
        return services.convert_stat_value(raw_value, param_def)

    def _refresh_points_table(self):
        rows = []

        for idx, point in enumerate(self._active_points(), start=1):
            point_id = int(point.get("id", idx))
            ts = point.get("timestamp", "")
            params = point.get("selected_params", [])
            ref_label = point.get("ref_sensor") or "Эталон"

            if point.get("mode", "lab") == "lab":
                for param in params:
                    ref_val = point.get("ref_values", {}).get(param)
                    if ref_val is None:
                        continue
                    rows.append(
                        (
                            point_id,
                            (
                                idx,
                                ts,
                                "ref",
                                ref_label,
                                self._param_label(param),
                                ref_val,
                                ref_val,
                                ref_val,
                                ref_val,
                            ),
                        )
                    )
            else:
                for param in params:
                    ref_stat = point.get("ref_stats", {}).get(param)
                    if not ref_stat:
                        continue
                    rows.append(
                        (
                            point_id,
                            (
                                idx,
                                ts,
                                "ref",
                                ref_label,
                                self._param_label(param),
                                self._convert_ref_raw_for_point(point, ref_stat.get("median"), param),
                                self._convert_ref_raw_for_point(point, ref_stat.get("avg"), param),
                                self._convert_ref_raw_for_point(point, ref_stat.get("max"), param),
                                self._convert_ref_raw_for_point(point, ref_stat.get("min"), param),
                            ),
                        )
                    )

            sensor_names = point.get("sensor_order") or list(point.get("sensor_points", {}).keys())
            if not sensor_names and point.get("sensor"):
                sensor_names = [point.get("sensor")]

            for sensor_name in sensor_names:
                sensor_entry = self._sensor_entry_for_point(point, sensor_name)
                raw_stats = sensor_entry.get("raw_stats", {}) if isinstance(sensor_entry, dict) else {}
                for param in params:
                    raw_stat = raw_stats.get(param)
                    if not raw_stat:
                        continue
                    rows.append(
                        (
                            point_id,
                            (
                                idx,
                                ts,
                                "sensor",
                                sensor_name,
                                self._param_label(param),
                                self._convert_sensor_raw(point, sensor_name, raw_stat.get("median"), param),
                                self._convert_sensor_raw(point, sensor_name, raw_stat.get("avg"), param),
                                self._convert_sensor_raw(point, sensor_name, raw_stat.get("max"), param),
                                self._convert_sensor_raw(point, sensor_name, raw_stat.get("min"), param),
                            ),
                        )
                    )

        self.points_table.setUpdatesEnabled(False)
        try:
            self.points_table.clearContents()
            self.points_table.setRowCount(len(rows))
            for row_idx, (point_id, row_data) in enumerate(rows):
                for col_idx, value in enumerate(row_data):
                    item = QTableWidgetItem(self._row_display_text(value))
                    if col_idx not in {self.COL_SENSOR, self.COL_PARAM}:
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    item.setData(Qt.ItemDataRole.UserRole, point_id)
                    self.points_table.setItem(row_idx, col_idx, item)
        finally:
            self.points_table.setUpdatesEnabled(True)

        self._update_points_table_height()
        self._update_remove_point_button()

    def _current_regression_result(self, param: str) -> Optional[Dict]:
        return self._results_for_sensor(self._active_sensor_name()).get(param)

    def on_calculate_regression(self):
        sensor_name = self._active_sensor_name()
        if not sensor_name:
            QMessageBox.warning(self, "Калибровка", "Выберите датчик")
            return

        param = self._current_graph_param_key()
        if not param:
            QMessageBox.warning(self, "Калибровка", "Выберите параметр")
            return

        X, y = services.build_regression_dataset(
            points=self._active_points(),
            param_key=param,
            mode=self._mode(),
            param_defs=self.param_defs,
            ref_param_defs=self.ref_param_defs,
            target_sensor=sensor_name,
        )

        result = services.calculate_regression(X, y, self.model_combo.currentText())
        if not result:
            QMessageBox.warning(self, "Калибровка", "Недостаточно данных для регрессии")
            return

        self._results_for_sensor(sensor_name, create=True)[param] = result
        QMessageBox.information(
            self,
            "Калибровка",
            f"{sensor_name} / {self._param_label(param)}: model={result['model']}\nR²={result['r2']:.4f}\ncoeff={result['coefficients']}",
        )

        self.graph_type_combo.setCurrentText("regression")
        self.update_graph()
    def update_graph(self):
        param = self._current_graph_param_key()
        self.axes.clear()

        if not param:
            self._apply_plot_theme()
            self.canvas.draw_idle()
            return

        if self.graph_type_combo.currentText() == "points":
            self._draw_points_graph(param)
        else:
            self._draw_regression_graph(param)

        self._apply_plot_theme()
        self.canvas.draw_idle()

    def _apply_plot_theme(self):
        apply_matplotlib_theme(self, self.figure, self.axes)
        palette = self.palette()
        self.points_table.setPalette(palette)
        self.points_table.viewport().setPalette(palette)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.PaletteChange:
            self.update_graph()

    def _autoscale_y(self, values: List[Optional[float]]):
        clean = [float(value) for value in values if value is not None]
        if not clean:
            return
        minimum = min(clean)
        maximum = max(clean)
        if maximum == minimum:
            margin = max(abs(maximum) * 0.1, 1.0)
            self.axes.set_ylim(minimum - margin, maximum + margin)
            return
        margin = max((maximum - minimum) * 0.12, 0.5)
        self.axes.set_ylim(minimum - margin, maximum + margin)

    def _draw_points_graph(self, param: str):
        points = self._active_points()
        sensor_names = self._visible_sensor_names()
        if not points or not sensor_names:
            self.axes.text(0.5, 0.5, "Нет точек для отображения", ha="center", va="center")
            return

        x: List[int] = list(range(1, len(points) + 1))
        all_values: List[Optional[float]] = []
        ref_y: List[Optional[float]] = []
        sensor_series: Dict[str, List[Optional[float]]] = {name: [] for name in sensor_names}

        for point in points:
            for sensor_name in sensor_names:
                sensor_entry = self._sensor_entry_for_point(point, sensor_name)
                raw_stat = sensor_entry.get("raw_stats", {}).get(param) if isinstance(sensor_entry, dict) else None
                value = None
                if raw_stat and raw_stat.get("median") is not None:
                    value = self._convert_sensor_raw(point, sensor_name, raw_stat.get("median"), param)
                sensor_series[sensor_name].append(value)
                all_values.append(value)

            if point.get("mode", "lab") == "lab":
                ref_value = point.get("ref_values", {}).get(param)
            else:
                ref_stat = point.get("ref_stats", {}).get(param)
                ref_value = self._convert_ref_raw_for_point(point, ref_stat.get("median"), param) if ref_stat else None
            ref_y.append(ref_value)
            all_values.append(ref_value)

        plotted = False
        active_name = self._active_sensor_name()
        color_cycle = ["#2563eb", "#dc2626", "#d97706", "#16a34a", "#0891b2", "#9333ea", "#ea580c"]
        for index, sensor_name in enumerate(sensor_names):
            series = sensor_series.get(sensor_name, [])
            if not any(value is not None for value in series):
                continue
            plotted = True
            self.axes.plot(
                x,
                series,
                marker="o",
                linewidth=2.2 if sensor_name == active_name else 1.5,
                alpha=1.0 if sensor_name == active_name else 0.78,
                color=color_cycle[index % len(color_cycle)],
                label=sensor_name,
            )

        if any(value is not None for value in ref_y):
            plotted = True
            self.axes.plot(x, ref_y, marker="s", color="#16a34a", linestyle="--", linewidth=1.5, label="ref")

        if plotted:
            self.axes.set_xlim(0.5, max(x) + 0.5)
            self._autoscale_y(all_values)
            self.axes.legend(loc="best")
        else:
            self.axes.text(0.5, 0.5, "Нет данных по выбранному параметру", ha="center", va="center")

        self.axes.set_title(f"Точки: {self._param_label(param)}")
        self.axes.set_xlabel("Проба")
        self.axes.set_ylabel("Значение")
    def _draw_regression_graph(self, param: str):
        sensor_name = self._active_sensor_name()
        result = self._current_regression_result(param)
        if not sensor_name:
            self.axes.text(0.5, 0.5, "Выберите датчик", ha="center", va="center")
            return
        if not result:
            self.axes.text(0.5, 0.5, "Сначала рассчитайте регрессию", ha="center", va="center")
            return

        X, y = services.build_regression_dataset(
            points=self._active_points(),
            param_key=param,
            mode=self._mode(),
            param_defs=self.param_defs,
            ref_param_defs=self.ref_param_defs,
            target_sensor=sensor_name,
        )
        if len(X) < 2:
            self.axes.text(0.5, 0.5, "Недостаточно данных", ha="center", va="center")
            return

        self.axes.scatter(X, y, color="#2563eb", label="points", s=28)

        import numpy as np

        x_min = min(X)
        x_max = max(X)
        if x_max == x_min:
            delta = max(abs(x_min) * 0.1, 1.0)
            x_min -= delta
            x_max += delta
        x_line = np.linspace(x_min, x_max, 120)
        coeff = result["coefficients"]
        if result["model"] == "linear":
            a, b = coeff
            y_line = a * x_line + b
        elif result["model"] == "poly2":
            c, b, a = coeff
            y_line = a * x_line**2 + b * x_line + c
        else:
            d, c, b, a = coeff
            y_line = a * x_line**3 + b * x_line**2 + c * x_line + d

        self.axes.plot(x_line, y_line, color="#dc2626", label=f"{result['model']} R²={result['r2']:.3f}")
        self.axes.set_xlim(x_min, x_max)
        self._autoscale_y(list(y) + list(y_line))
        self.axes.legend(loc="best")
        self.axes.set_title(f"Регрессия: {self._param_label(param)} / {sensor_name}")
        self.axes.set_xlabel("Calib")
        self.axes.set_ylabel("Ref")

    def on_save_calibration(self):
        sensor_name = self._active_sensor_name()
        sensor_results = self._results_for_sensor(sensor_name)
        if not sensor_results:
            QMessageBox.warning(self, "Калибровка", "Нет результатов регрессии для выбранного датчика")
            return

        calib_connected = self.registry.get_connected(sensor_name) if sensor_name else None
        if not calib_connected:
            QMessageBox.warning(self, "Калибровка", "Не найден выбранный датчик")
            return

        base_profile = calib_connected.config.profile
        base_data = self.profile_manager.get_profile(base_profile)
        if not base_data:
            QMessageBox.critical(self, "Калибровка", f"Профиль не найден: {base_profile}")
            return

        data = json.loads(json.dumps(base_data))
        calibration_map = data.get("calibration") or {}
        for param, result in sensor_results.items():
            calibration_map[param] = {
                "model": result["model"],
                "coefficients": result["coefficients"],
                "r2": result["r2"],
            }
        data["calibration"] = calibration_map

        default_name = base_profile.replace(".json", "") + "_calibrated"
        profile_name, ok = QInputDialog.getText(
            self,
            "Сохранение",
            "Имя нового профиля:",
            text=default_name,
        )
        if not ok or not profile_name.strip():
            return

        fname = profile_name.strip().replace(" ", "_")
        if not fname.lower().endswith(".json"):
            fname += ".json"

        if self.profile_manager.save_profile(fname, data):
            QMessageBox.information(self, "Калибровка", f"Калибровка сохранена в {fname}")
            self.profiles_changed.emit()
        else:
            QMessageBox.critical(self, "Калибровка", "Ошибка сохранения профиля")

    def clear_points(self):
        self.points.clear()
        self.calibration_results.clear()
        self._next_point_id = 1
        self.points_table.clearContents()
        self.points_table.setRowCount(0)
        self._update_points_table_height()
        self._update_remove_point_button()
        self.update_graph()
