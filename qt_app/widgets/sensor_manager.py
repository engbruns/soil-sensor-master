from __future__ import annotations

from typing import Dict, Optional

import serial.tools.list_ports
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from config import MODBUS_BAUDRATES
from qt_app.backend.models import SensorConfig
from qt_app.theme_utils import mark_styled_background


class SensorManagerWidget(QGroupBox):
    sensors_changed = pyqtSignal()
    sensor_rows_changed = pyqtSignal()

    COL_NAME = 0
    COL_PORT = 1
    COL_ADDR = 2
    COL_BAUD = 3
    COL_PROFILE = 4
    COL_STATUS = 5

    def __init__(self, registry, profile_manager, settings, parent=None):
        super().__init__("Датчики", parent)
        self.registry = registry
        self.profile_manager = profile_manager
        self.settings = settings
        mark_styled_background(self)

        self._connected_rows: Dict[int, str] = {}
        self._add_simulated_next = False

        self._status_unstable = "Unstable"
        self._status_reconnecting = "Reconnecting"

        self._status_connect = "Подключить"
        self._status_disconnect = "Отключить"
        self._status_error = "Ошибка"

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Имя", "Порт", "Адрес", "Скорость", "Профиль", "Статус"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.SelectedClicked)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(26)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setMinimumHeight(84)
        self.setMinimumHeight(132)

        self.btn_add = QPushButton("+")
        self.btn_add.setToolTip("Добавить датчик. Ctrl+Shift+клик: добавить симулятор")
        self.btn_remove = QPushButton("Удалить")
        self.btn_refresh_ports = QPushButton("Обновить")

        for btn in [self.btn_add, self.btn_remove, self.btn_refresh_ports]:
            btn.setFixedHeight(24)

        top_controls = QHBoxLayout()
        top_controls.addStretch(1)
        top_controls.addWidget(self.btn_add)
        top_controls.addWidget(self.btn_remove)
        top_controls.addWidget(self.btn_refresh_ports)

        layout = QVBoxLayout(self)
        layout.addLayout(top_controls)
        layout.addWidget(self.table)

        self.btn_add.pressed.connect(self._capture_add_click_modifiers)
        self.btn_add.clicked.connect(self.on_add_button_clicked)
        self.btn_remove.clicked.connect(self.remove_selected_row)
        self.btn_refresh_ports.clicked.connect(self.refresh_ports)
        self.table.cellClicked.connect(self._on_table_cell_clicked)

        self.load_rows_from_settings()

        self._health_timer = QTimer(self)
        self._health_timer.setInterval(900)
        self._health_timer.timeout.connect(self.refresh_runtime_statuses)
        self._health_timer.start()

    def set_texts(self, text_map: Dict[str, str]):
        self.setTitle(text_map.get("group_title", self.title()))
        self.btn_add.setText(text_map.get("btn_add", self.btn_add.text()))
        self.btn_remove.setText(text_map.get("btn_remove", self.btn_remove.text()))
        self.btn_refresh_ports.setText(text_map.get("btn_refresh_ports", self.btn_refresh_ports.text()))
        self.btn_add.setToolTip(text_map.get("btn_add_tooltip", self.btn_add.toolTip()))

        self._status_connect = text_map.get("status_connect", self._status_connect)
        self._status_disconnect = text_map.get("status_disconnect", self._status_disconnect)
        self._status_error = text_map.get("status_error", self._status_error)
        self._status_unstable = text_map.get("status_unstable", self._status_unstable)
        self._status_reconnecting = text_map.get("status_reconnecting", self._status_reconnecting)

        self.table.setHorizontalHeaderLabels(
            [
                text_map.get("col_name", "Имя"),
                text_map.get("col_port", "Порт"),
                text_map.get("col_addr", "Адрес"),
                text_map.get("col_baud", "Скорость"),
                text_map.get("col_profile", "Профиль"),
                text_map.get("col_status", "Статус"),
            ]
        )

        for row in range(self.table.rowCount()):
            self._set_status(row, self._status_disconnect if row in self._connected_rows else self._status_connect)

    def _capture_add_click_modifiers(self):
        modifiers = QApplication.keyboardModifiers()
        self._add_simulated_next = bool(
            (modifiers & Qt.KeyboardModifier.ControlModifier)
            and (modifiers & Qt.KeyboardModifier.ShiftModifier)
        )

    def on_add_button_clicked(self):
        simulated = self._add_simulated_next
        self._add_simulated_next = False
        self.add_row(simulated=simulated)

    def _available_ports(self):
        return [p.device for p in serial.tools.list_ports.comports()]

    def _available_profiles(self):
        return self.profile_manager.list_profiles()

    def _on_table_cell_clicked(self, row: int, col: int):
        if row < 0:
            return
        if col == self.COL_STATUS:
            self.toggle_row_connection(row)

    def add_row(self, simulated: bool = False, cfg: Optional[SensorConfig] = None):
        row = self.table.rowCount()
        self.table.insertRow(row)

        if cfg is None:
            existing_names = {
                self.table.item(r, self.COL_NAME).text()
                for r in range(self.table.rowCount() - 1)
                if self.table.item(r, self.COL_NAME)
            }
            idx = 1
            while f"Датчик {idx}" in existing_names:
                idx += 1
            profiles = self._available_profiles()
            cfg = SensorConfig(
                name=f"Датчик {idx}",
                port="sim" if simulated else "",
                address=1,
                baudrate=4800,
                profile=profiles[0] if profiles else "",
                simulated=simulated,
            )

        name_item = QTableWidgetItem(cfg.name)
        name_item.setData(Qt.ItemDataRole.UserRole, bool(cfg.simulated))
        self.table.setItem(row, self.COL_NAME, name_item)

        port_combo = QComboBox()
        ports = ["sim"] + self._available_ports()
        port_combo.addItems(ports)
        if cfg.port and cfg.port in ports:
            port_combo.setCurrentText(cfg.port)
        elif bool(cfg.simulated):
            port_combo.setCurrentText("sim")
        self.table.setCellWidget(row, self.COL_PORT, port_combo)

        addr_spin = QSpinBox()
        addr_spin.setRange(1, 247)
        addr_spin.setValue(int(cfg.address))
        self.table.setCellWidget(row, self.COL_ADDR, addr_spin)

        baud_combo = QComboBox()
        baud_combo.addItems([str(v) for v in MODBUS_BAUDRATES])
        baud_combo.setCurrentText(str(cfg.baudrate))
        self.table.setCellWidget(row, self.COL_BAUD, baud_combo)

        profile_combo = QComboBox()
        profile_combo.addItems(self._available_profiles())
        if cfg.profile:
            profile_combo.setCurrentText(cfg.profile)
        self.table.setCellWidget(row, self.COL_PROFILE, profile_combo)

        status_item = QTableWidgetItem(self._status_connect)
        status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        status_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        self.table.setItem(row, self.COL_STATUS, status_item)

        self.sensor_rows_changed.emit()

    def _row_simulated(self, row: int) -> bool:
        port_combo = self.table.cellWidget(row, self.COL_PORT)
        if isinstance(port_combo, QComboBox):
            return port_combo.currentText().strip().lower() == "sim"
        return False

    def _row_config(self, row: int) -> Optional[SensorConfig]:
        name_item = self.table.item(row, self.COL_NAME)
        if not name_item:
            return None

        name = name_item.text().strip()
        if not name:
            return None

        port_combo = self.table.cellWidget(row, self.COL_PORT)
        addr_spin = self.table.cellWidget(row, self.COL_ADDR)
        baud_combo = self.table.cellWidget(row, self.COL_BAUD)
        profile_combo = self.table.cellWidget(row, self.COL_PROFILE)

        port = port_combo.currentText().strip() if isinstance(port_combo, QComboBox) else ""
        simulated = port.lower() == "sim"

        if not simulated and not port:
            return None

        address = addr_spin.value() if isinstance(addr_spin, QSpinBox) else 1
        baud = int(baud_combo.currentText()) if isinstance(baud_combo, QComboBox) and baud_combo.currentText() else 4800
        profile = profile_combo.currentText().strip() if isinstance(profile_combo, QComboBox) else ""

        return SensorConfig(
            name=name,
            port=port if port else ("sim" if simulated else ""),
            address=address,
            baudrate=baud,
            profile=profile,
            simulated=simulated,
        )

    def _set_status(self, row: int, text: str, tooltip: Optional[str] = None):
        item = self.table.item(row, self.COL_STATUS)
        if item:
            item.setText(text)
            item.setToolTip(tooltip or "")

    def _set_row_editable(self, row: int, editable: bool):
        name_item = self.table.item(row, self.COL_NAME)
        if name_item:
            flags = name_item.flags()
            if editable:
                name_item.setFlags(flags | Qt.ItemFlag.ItemIsEditable)
            else:
                name_item.setFlags(flags & ~Qt.ItemFlag.ItemIsEditable)

        for col in [self.COL_PORT, self.COL_ADDR, self.COL_BAUD, self.COL_PROFILE]:
            widget = self.table.cellWidget(row, col)
            if widget:
                widget.setEnabled(editable)

    def selected_row(self) -> int:
        indexes = self.table.selectionModel().selectedRows()
        return indexes[0].row() if indexes else -1

    def toggle_row_connection(self, row: int):
        if row < 0:
            return

        try:
            if row in self._connected_rows:
                name = self._connected_rows.pop(row)
                self.registry.disconnect_sensor(name)
                self._set_status(row, self._status_connect)
                self._set_row_editable(row, True)
                self.sensors_changed.emit()
                return

            cfg = self._row_config(row)
            if cfg is None:
                QMessageBox.warning(self, "Датчики", "Проверьте заполнение строки")
                return

            ok, msg = self.registry.connect_sensor(cfg)
            if not ok:
                QMessageBox.critical(self, "Ошибка подключения", msg)
                self._set_status(row, self._status_error, msg)
                return

            self._connected_rows[row] = cfg.name
            self._set_status(row, self._status_disconnect)
            self._set_row_editable(row, False)
            self.sensors_changed.emit()
        except Exception as exc:
            QMessageBox.critical(self, "Датчики", f"Ошибка операции с датчиком: {exc}")


    def refresh_runtime_statuses(self):
        for row, name in list(self._connected_rows.items()):
            health = self.registry.get_sensor_health(name)
            if not health:
                self._set_status(row, self._status_error, "Disconnected")
                continue

            status = str(health.get("status", "connected"))
            err = str(health.get("last_error", "") or "")
            if status == "connected":
                self._set_status(row, self._status_disconnect)
            elif status == "unstable":
                self._set_status(row, self._status_unstable, err)
            elif status == "reconnecting":
                self._set_status(row, self._status_reconnecting, err or "Auto reconnect in progress")
            else:
                self._set_status(row, self._status_error, err or "Device degraded")

    def toggle_selected_connection(self):
        row = self.selected_row()
        if row < 0:
            QMessageBox.warning(self, "Датчики", "Выберите строку датчика")
            return
        self.toggle_row_connection(row)

    def remove_selected_row(self):
        row = self.selected_row()
        if row < 0:
            return

        if row in self._connected_rows:
            name = self._connected_rows.pop(row)
            self.registry.disconnect_sensor(name)

        self.table.removeRow(row)

        new_map = {}
        for r, n in self._connected_rows.items():
            new_map[r - 1 if r > row else r] = n
        self._connected_rows = new_map

        self.sensors_changed.emit()
        self.sensor_rows_changed.emit()

    def refresh_ports(self):
        ports = ["sim"] + self._available_ports()
        for row in range(self.table.rowCount()):
            combo = self.table.cellWidget(row, self.COL_PORT)
            if not isinstance(combo, QComboBox):
                continue

            current = combo.currentText()
            combo.blockSignals(True)
            combo.clear()
            combo.addItems(ports)
            if current in ports:
                combo.setCurrentText(current)
            elif self._row_simulated(row):
                combo.setCurrentText("sim")
            combo.blockSignals(False)

    def refresh_profiles(self):
        profiles = self._available_profiles()
        for row in range(self.table.rowCount()):
            combo = self.table.cellWidget(row, self.COL_PROFILE)
            if not isinstance(combo, QComboBox):
                continue
            current = combo.currentText()
            combo.clear()
            combo.addItems(profiles)
            if current in profiles:
                combo.setCurrentText(current)

    def load_rows_from_settings(self):
        rows = self.settings.get("sensors", [])
        for raw in rows:
            cfg = SensorConfig(
                name=raw.get("name", "Датчик"),
                port=raw.get("port", ""),
                address=int(raw.get("address", 1)),
                baudrate=int(raw.get("baudrate", 4800)),
                profile=raw.get("profile", ""),
                simulated=bool(raw.get("simulated", False)),
            )
            self.add_row(simulated=cfg.simulated, cfg=cfg)

        if self.table.rowCount() == 0:
            self.add_row(simulated=False)

    def save_rows_to_settings(self):
        sensors = []
        for row in range(self.table.rowCount()):
            cfg = self._row_config(row)
            if not cfg:
                continue
            sensors.append(
                {
                    "name": cfg.name,
                    "port": cfg.port,
                    "address": cfg.address,
                    "baudrate": cfg.baudrate,
                    "profile": cfg.profile,
                    "simulated": cfg.simulated,
                }
            )
        self.settings["sensors"] = sensors
