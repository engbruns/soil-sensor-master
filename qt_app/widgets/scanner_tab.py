from __future__ import annotations

from typing import Dict, List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.constants import ADDRESS_HINTS, STANDARD_PARAMS
from modules.scanner.analyzer import analyze
from qt_app.backend.services import parse_address_list
from qt_app.param_utils import ordered_param_keys, param_label
from qt_app.theme_utils import mark_styled_background
from qt_app.workers import ScannerThread
from .address_search_dialog import AddressSearchDialog
from .scanner_assign_dialog import ScannerAssignDialog
from .scanner_graph_dialog import ScannerGraphDialog


class ScannerTab(QWidget):
    profiles_changed = pyqtSignal()
    COL_ADDR_HEX = 0
    COL_ADDR_DEC = 1
    COL_MEDIAN = 2
    COL_HEX = 3
    COL_GRAPH = 4
    COL_ASSIGN_ACTION = 5
    COL_ASSIGN_NAME = 6
    COL_PROB = 7

    def __init__(self, registry, profile_manager, parent=None):
        super().__init__(parent)
        self.registry = registry
        self.profile_manager = profile_manager
        mark_styled_background(self, "modulePanel")

        self.worker: Optional[ScannerThread] = None
        self.current_snapshot: List[Dict] = []
        self.manual_mapping: Dict[int, Dict] = {}
        self.references: List[Dict] = []
        self.last_probs: Optional[Dict] = None
        self._lang = "ru"

        self.sensor_combo = QComboBox()
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Диапазон", "Список"])
        self.range_start = QLineEdit("0x0000")
        self.range_end = QLineEdit("0x0030")
        self.list_edit = QLineEdit("0x0000-0x0008, 0x0022-0x0024, 0x0050-0x0053")
        self.cycles_spin = QSpinBox()
        self.cycles_spin.setRange(1, 100)
        self.cycles_spin.setValue(8)

        self.start_btn = QPushButton("Старт")
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.btn_search_address = QPushButton("Поиск адреса")

        self.ref_param_combo = QComboBox()
        self.ref_value_spin = QDoubleSpinBox()
        self.ref_value_spin.setRange(-100000, 100000)
        self.ref_value_spin.setDecimals(3)
        self.ref_tol_spin = QDoubleSpinBox()
        self.ref_tol_spin.setRange(0.001, 100000)
        self.ref_tol_spin.setValue(1.0)

        self.refs_table = QTableWidget(0, 3)
        self.refs_table.setHorizontalHeaderLabels(["Параметр", "Значение", "Допуск"])
        self.refs_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self.results_table = QTableWidget(0, 8)
        self.results_table.setHorizontalHeaderLabels([
            "Addr hex",
            "Addr dec",
            "Median",
            "Hex",
            "Назначение",
            "Вероятности",
        ])
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.results_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.results_table.verticalHeader().setVisible(False)

        self.results_table.setHorizontalHeaderLabels(
            ["Addr hex", "Addr dec", "Median", "Hex", "График", "Назначить", "Параметр", "Вероятности"]
        )

        self.assign_param_combo = QComboBox()
        self.assign_factor = QDoubleSpinBox()
        self.assign_factor.setRange(-100000, 100000)
        self.assign_factor.setDecimals(6)
        self.assign_factor.setValue(1.0)
        self.assign_offset = QDoubleSpinBox()
        self.assign_offset.setRange(-100000, 100000)
        self.assign_offset.setDecimals(6)

        self.btn_assign = QPushButton("Назначить выбранному")
        self.btn_analyze = QPushButton("Анализ")
        self.btn_save_profile = QPushButton("Сохранить профиль")

        self._build_ui()
        self._populate_param_combos()
        self._wire()

    def _build_ui(self):
        settings_box = QGroupBox("Сканирование")
        mark_styled_background(settings_box)
        settings_form = QGridLayout(settings_box)
        settings_form.addWidget(QLabel("Датчик:"), 0, 0)
        settings_form.addWidget(self.sensor_combo, 0, 1)
        settings_form.addWidget(QLabel("Режим адресов:"), 0, 2)
        settings_form.addWidget(self.mode_combo, 0, 3)

        self.lbl_start = QLabel("Start:")
        self.lbl_end = QLabel("End:")
        self.lbl_list = QLabel("Список:")

        settings_form.addWidget(self.lbl_start, 1, 0)
        settings_form.addWidget(self.range_start, 1, 1)
        settings_form.addWidget(self.lbl_end, 1, 2)
        settings_form.addWidget(self.range_end, 1, 3)

        settings_form.addWidget(self.lbl_list, 2, 0)
        settings_form.addWidget(self.list_edit, 2, 1, 1, 3)

        settings_form.addWidget(QLabel("Циклы:"), 3, 0)
        settings_form.addWidget(self.cycles_spin, 3, 1)
        settings_form.addWidget(self.start_btn, 3, 2)
        settings_form.addWidget(self.progress, 3, 3)

        refs_box = QGroupBox("Ориентиры")
        mark_styled_background(refs_box)
        refs_layout = QVBoxLayout(refs_box)

        ref_controls = QHBoxLayout()
        ref_controls.addWidget(QLabel("Параметр"))
        ref_controls.addWidget(self.ref_param_combo)
        ref_controls.addWidget(QLabel("Значение"))
        ref_controls.addWidget(self.ref_value_spin)
        ref_controls.addWidget(QLabel("Допуск"))
        ref_controls.addWidget(self.ref_tol_spin)

        self.btn_ref_add = QPushButton("Добавить")
        self.btn_ref_del = QPushButton("Удалить")
        ref_controls.addWidget(self.btn_ref_add)
        ref_controls.addWidget(self.btn_ref_del)

        refs_layout.addLayout(ref_controls)
        refs_layout.addWidget(self.refs_table)

        assign_box = QGroupBox("Назначение параметров")
        assign_layout = QHBoxLayout(assign_box)
        assign_layout.addWidget(QLabel("Параметр"))
        assign_layout.addWidget(self.assign_param_combo)
        assign_layout.addWidget(QLabel("Factor"))
        assign_layout.addWidget(self.assign_factor)
        assign_layout.addWidget(QLabel("Offset"))
        assign_layout.addWidget(self.assign_offset)
        assign_layout.addWidget(self.btn_assign)
        assign_layout.addWidget(self.btn_search_address)
        assign_layout.addWidget(self.btn_analyze)
        assign_layout.addWidget(self.btn_save_profile)

        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(self.COL_ADDR_HEX, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COL_ADDR_DEC, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COL_MEDIAN, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COL_HEX, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COL_GRAPH, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COL_ASSIGN_ACTION, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COL_ASSIGN_NAME, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(self.COL_PROB, QHeaderView.ResizeMode.Stretch)

        layout = QVBoxLayout(self)
        layout.addWidget(settings_box)
        layout.addWidget(refs_box)
        layout.addWidget(self.results_table, 2)
        layout.addWidget(assign_box)

        self._apply_mode_visibility()

    def _wire(self):
        self.mode_combo.currentIndexChanged.connect(self._apply_mode_visibility)
        self.start_btn.clicked.connect(self.toggle_scan)
        self.btn_ref_add.clicked.connect(self.add_reference)
        self.btn_ref_del.clicked.connect(self.remove_reference)
        self.btn_assign.clicked.connect(self.assign_selected)
        self.btn_search_address.clicked.connect(self.open_address_search)
        self.btn_analyze.clicked.connect(self.on_analyze)
        self.btn_save_profile.clicked.connect(self.on_save_profile)
        self.results_table.cellClicked.connect(self._on_results_cell_clicked)

    def set_language(self, language: str):
        self._lang = language if language in {"ru", "en", "zh"} else "ru"
        self._populate_param_combos()
        self._refresh_reference_table()
        self._fill_results_table(self.current_snapshot, self.last_probs)

    def set_active(self, active: bool):
        if active:
            return
        if self.worker and self.worker.isRunning():
            self.worker.stop()

    def _param_label(self, key: str) -> str:
        return param_label(key, self._lang)

    def _ordered_param_keys(self) -> List[str]:
        return ordered_param_keys(STANDARD_PARAMS.keys())

    def _populate_param_combos(self):
        ref_current = self.ref_param_combo.currentData()
        assign_current = self.assign_param_combo.currentData()

        self.ref_param_combo.clear()
        self.assign_param_combo.clear()

        for key in self._ordered_param_keys():
            label = self._param_label(key)
            self.ref_param_combo.addItem(label, key)
            self.assign_param_combo.addItem(label, key)

        if isinstance(ref_current, str):
            idx = self.ref_param_combo.findData(ref_current)
            if idx >= 0:
                self.ref_param_combo.setCurrentIndex(idx)
        if isinstance(assign_current, str):
            idx = self.assign_param_combo.findData(assign_current)
            if idx >= 0:
                self.assign_param_combo.setCurrentIndex(idx)

    @staticmethod
    def _combo_key(combo: QComboBox) -> str:
        data = combo.currentData()
        if isinstance(data, str) and data:
            return data
        return combo.currentText().strip()

    def on_sensors_changed(self):
        current = self.sensor_combo.currentText()
        names = self.registry.list_connected_names()
        self.sensor_combo.clear()
        self.sensor_combo.addItems(names)
        if current and current in names:
            self.sensor_combo.setCurrentText(current)

    def _apply_mode_visibility(self):
        use_list = self.mode_combo.currentText() == "Список"
        self.lbl_start.setVisible(not use_list)
        self.lbl_end.setVisible(not use_list)
        self.range_start.setVisible(not use_list)
        self.range_end.setVisible(not use_list)
        self.lbl_list.setVisible(use_list)
        self.list_edit.setVisible(use_list)

    def _parse_addresses(self) -> List[int]:
        if self.mode_combo.currentText() == "Список":
            addresses = parse_address_list(self.list_edit.text())
            if not addresses:
                raise ValueError("Список адресов пуст")
            if len(addresses) > 512:
                raise ValueError("Слишком много адресов (максимум 512)")
            return addresses

        start = int(self.range_start.text().strip(), 0)
        end = int(self.range_end.text().strip(), 0)
        if start > end:
            raise ValueError("Начальный адрес должен быть меньше или равен конечному")
        addresses = list(range(start, end + 1))
        if len(addresses) > 512:
            raise ValueError("Слишком большой диапазон (максимум 512 адресов)")
        return addresses

    def toggle_scan(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.start_btn.setEnabled(False)
            return

        sensor_name = self.sensor_combo.currentText().strip()
        connected = self.registry.get_connected(sensor_name) if sensor_name else None
        if not connected:
            QMessageBox.warning(self, "Сканер", "Выберите подключенный датчик")
            return

        try:
            addresses = self._parse_addresses()
        except Exception as exc:
            QMessageBox.warning(self, "Сканер", str(exc))
            return

        self.progress.setValue(0)
        self.start_btn.setText("Стоп")
        self.current_snapshot = []
        self.last_probs = None

        self.worker = ScannerThread(connected.sensor, addresses, self.cycles_spin.value())
        self.worker.progress_changed.connect(self.progress.setValue)
        self.worker.finished_with_result.connect(self._on_scan_finished)
        self.worker.start()

    def _on_scan_finished(self, snapshot, ok: bool, error_text: str):
        self.worker = None
        self.start_btn.setText("Старт")
        self.start_btn.setEnabled(True)
        self.progress.setValue(100 if ok else 0)

        if error_text:
            QMessageBox.critical(self, "Сканер", error_text)

        if not ok:
            QMessageBox.warning(self, "Сканер", "Сканирование остановлено или завершилось с ошибкой")
            return

        self.current_snapshot = snapshot or []
        self._fill_results_table(self.current_snapshot)

    def _fill_results_table(self, snapshot: List[Dict], probs: Optional[Dict] = None):
        self.results_table.setRowCount(len(snapshot))
        for row, item in enumerate(snapshot):
            addr_dec = int(item["addr_dec"])
            mapping = self.manual_mapping.get(addr_dec, {})
            assign_key = mapping.get("param", "")
            assign_text = self._param_label(assign_key) if assign_key else ""

            prob_text = ""
            if probs and addr_dec in probs and probs[addr_dec]:
                top = sorted(probs[addr_dec].items(), key=lambda kv: kv[1], reverse=True)[:2]
                prob_text = " | ".join([f"{self._param_label(k)}:{int(v*100)}%" for k, v in top])

            values = [
                item.get("addr_hex", ""),
                str(addr_dec),
                f"{item['value_dec']:.2f}" if item.get("value_dec") is not None else "---",
                item.get("value_hex", "---"),
                "График",
                "Назначить",
                assign_text,
                prob_text,
            ]
            for col, txt in enumerate(values):
                cell = self.results_table.item(row, col)
                if cell is None:
                    cell = QTableWidgetItem(txt)
                    if col != self.COL_ASSIGN_NAME and col != self.COL_PROB:
                        cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.results_table.setItem(row, col, cell)
                else:
                    cell.setText(txt)

    def _on_results_cell_clicked(self, row: int, column: int):
        if row < 0 or row >= self.results_table.rowCount():
            return
        if column == self.COL_GRAPH:
            self._open_graph_for_row(row)
        elif column == self.COL_ASSIGN_ACTION:
            self._open_assign_for_row(row)

    def _open_graph_for_row(self, row: int):
        if row < 0 or row >= len(self.current_snapshot):
            return
        snapshot = self.current_snapshot[row]
        dialog = ScannerGraphDialog(
            title=f"Регистр {snapshot.get('addr_hex', '')}",
            raw_values=snapshot.get("raw_values", []),
            median=snapshot.get("value_dec"),
            parent=self,
        )
        dialog.exec()

    def _open_assign_for_row(self, row: int):
        addr_item = self.results_table.item(row, self.COL_ADDR_DEC)
        if addr_item is None:
            return
        addr = int(addr_item.text())
        dialog = ScannerAssignDialog(addr, self.manual_mapping.get(addr), self._lang, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.manual_mapping[addr] = dialog.mapping()
        self._fill_results_table(self.current_snapshot, self.last_probs)

    def open_address_search(self):
        sensor_name = self.sensor_combo.currentText().strip()
        connected = self.registry.get_connected(sensor_name) if sensor_name else None
        dialog = AddressSearchDialog(sensor_name, connected.sensor if connected else None, self)
        dialog.exec()

    def add_reference(self):
        param_key = self._combo_key(self.ref_param_combo)
        ref = {
            "param": param_key,
            "value": float(self.ref_value_spin.value()),
            "tolerance": float(self.ref_tol_spin.value()),
        }
        self.references.append(ref)
        self._refresh_reference_table()

    def remove_reference(self):
        rows = self.refs_table.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        if 0 <= row < len(self.references):
            self.references.pop(row)
        self._refresh_reference_table()

    def _refresh_reference_table(self):
        self.refs_table.setRowCount(len(self.references))
        for row, ref in enumerate(self.references):
            self.refs_table.setItem(row, 0, QTableWidgetItem(self._param_label(ref["param"])))
            self.refs_table.setItem(row, 1, QTableWidgetItem(f"{ref['value']:.3f}"))
            self.refs_table.setItem(row, 2, QTableWidgetItem(f"{ref['tolerance']:.3f}"))

    def assign_selected(self):
        rows = self.results_table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.warning(self, "Сканер", "Выберите строку в таблице результатов")
            return

        self._open_assign_for_row(rows[0].row())

    def on_analyze(self):
        if not self.current_snapshot:
            QMessageBox.warning(self, "Сканер", "Нет данных для анализа")
            return
        if not self.references:
            QMessageBox.warning(self, "Сканер", "Добавьте ориентиры")
            return

        self.last_probs = analyze(self.current_snapshot, self.references, STANDARD_PARAMS, ADDRESS_HINTS)
        self._fill_results_table(self.current_snapshot, self.last_probs)

    def on_save_profile(self):
        if not self.current_snapshot:
            QMessageBox.warning(self, "Профиль", "Нет результатов сканирования")
            return
        if not self.manual_mapping:
            QMessageBox.warning(self, "Профиль", "Сначала назначьте параметры адресам")
            return

        display_name, ok = QInputDialog.getText(self, "Имя профиля", "Введите имя профиля:")
        if not ok or not display_name.strip():
            return

        description, _ = QInputDialog.getText(self, "Описание", "Краткое описание:")
        fname = display_name.strip().replace(" ", "_").lower() + ".json"

        params = []
        for addr, mapping in sorted(self.manual_mapping.items(), key=lambda kv: kv[0]):
            params.append(
                {
                    "key": mapping["param"],
                    "name_key": f"{mapping['param']}_name",
                    "unit": STANDARD_PARAMS.get(mapping["param"], {}).get("unit_key", ""),
                    "address": int(addr),
                    "function_code": 3,
                    "factor": mapping.get("factor", 1.0),
                    "offset": mapping.get("offset", 0.0),
                }
            )

        profile_data = {
            "name": display_name.strip(),
            "description": description.strip(),
            "device": {
                "default_address": 1,
                "default_baudrate": 4800,
                "available_baudrates": [2400, 4800, 9600],
            },
            "parameters": params,
            "system_registers": [],
            "calibration": None,
            "analysis": self.last_probs,
        }

        if self.profile_manager.save_profile(fname, profile_data):
            QMessageBox.information(self, "Профиль", f"Профиль сохранен: {fname}")
            self.profiles_changed.emit()
        else:
            QMessageBox.critical(self, "Профиль", "Не удалось сохранить профиль")
