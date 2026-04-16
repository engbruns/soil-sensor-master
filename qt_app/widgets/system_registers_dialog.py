from __future__ import annotations

from typing import Dict, List

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)

from qt_app.backend import services
from qt_app.theme_utils import mark_styled_background


def _register_label(reg_def: Dict) -> str:
    label = reg_def.get("name") or reg_def.get("title") or reg_def.get("name_key") or reg_def.get("key", "")
    return str(label).replace("_", " ").strip()


class EditSystemRegisterDialog(QDialog):
    def __init__(self, sensor, reg_def: Dict, current_value: float | None, parent=None):
        super().__init__(parent)
        self.sensor = sensor
        self.reg_def = dict(reg_def)

        self.setWindowTitle(f"Редактировать: {_register_label(self.reg_def)}")
        self.setModal(True)
        self.resize(420, 220)

        root = QWidget()
        mark_styled_background(root, "dialogSurface")

        self.value_edit = QLineEdit("" if current_value is None else f"{current_value:.6g}")

        form = QFormLayout()
        form.addRow("Регистр", QLabel(_register_label(self.reg_def)))
        form.addRow("Адрес", QLabel(f"0x{int(self.reg_def.get('address', 0)):04X}"))
        form.addRow("Текущее значение", QLabel("---" if current_value is None else f"{current_value:.6g}"))
        form.addRow("Новое значение", self.value_edit)

        hints = []
        if "min" in self.reg_def or "max" in self.reg_def:
            hints.append(f"Пределы raw: {self.reg_def.get('min', '-inf')} .. {self.reg_def.get('max', '+inf')}")
        allowed = self.reg_def.get("values")
        if isinstance(allowed, list) and allowed:
            hints.append(f"Допустимые raw: {allowed}")
        if self.reg_def.get("signed"):
            hints.append("Знаковый 16-битный регистр")

        hint_label = QLabel("\n".join(hints))
        hint_label.setWordWrap(True)
        hint_label.setVisible(bool(hints))

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._write_value)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(root)
        layout.addLayout(form)
        layout.addWidget(hint_label)
        layout.addStretch(1)
        layout.addWidget(buttons)

        outer = QVBoxLayout(self)
        outer.addWidget(root)

    def _write_value(self):
        text = self.value_edit.text().strip().replace(",", ".")
        if not text:
            QMessageBox.warning(self, "Системные регистры", "Введите значение.")
            return

        try:
            value = float(text)
            ok = services.write_system_register_value(self.sensor, self.reg_def, value)
        except Exception as exc:
            QMessageBox.critical(self, "Системные регистры", str(exc))
            return

        if not ok:
            QMessageBox.critical(self, "Системные регистры", "Не удалось записать регистр.")
            return
        self.accept()


class SystemRegistersDialog(QDialog):
    def __init__(self, sensor_name: str, sensor, profile_data: Dict, parent=None):
        super().__init__(parent)
        self.sensor_name = sensor_name
        self.sensor = sensor
        self.profile_data = profile_data or {}
        self.system_regs: List[Dict] = list(self.profile_data.get("system_registers") or [])
        self._values: List[float | None] = []

        self.setWindowTitle(f"Системные регистры: {sensor_name}")
        self.resize(920, 480)

        root = QWidget()
        mark_styled_background(root, "dialogSurface")

        header_box = QGroupBox("Выбранный датчик")
        mark_styled_background(header_box)
        header_layout = QGridLayout(header_box)
        header_layout.addWidget(QLabel("Датчик"), 0, 0)
        header_layout.addWidget(QLabel(sensor_name), 0, 1)
        header_layout.addWidget(QLabel("Профиль"), 1, 0)
        header_layout.addWidget(QLabel(str(self.profile_data.get("name", ""))), 1, 1)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Регистр", "Адрес", "Значение", "Ед.", "Запись", "Действие"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)

        self.btn_refresh = QPushButton("Обновить")
        self.btn_close = QPushButton("Закрыть")

        actions = QHBoxLayout()
        actions.addWidget(self.btn_refresh)
        actions.addStretch(1)
        actions.addWidget(self.btn_close)

        layout = QVBoxLayout(root)
        layout.addWidget(header_box)
        layout.addWidget(self.table, 1)
        layout.addLayout(actions)

        outer = QVBoxLayout(self)
        outer.addWidget(root)

        self.btn_refresh.clicked.connect(self.refresh_values)
        self.btn_close.clicked.connect(self.close)
        self.refresh_values()

    def refresh_values(self):
        if not self.sensor or not getattr(self.sensor, "connected", False):
            QMessageBox.warning(self, "Системные регистры", "Датчик не подключен.")
            self.table.setRowCount(0)
            return

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self._values = [services.read_system_register_value(self.sensor, reg) for reg in self.system_regs]
        finally:
            QApplication.restoreOverrideCursor()

        self.table.setRowCount(len(self.system_regs))
        for row, reg in enumerate(self.system_regs):
            value = self._values[row] if row < len(self._values) else None
            unit = str(reg.get("unit", "") or "")
            writable = "Да" if reg.get("writable", True) else "Нет"

            items = [
                QTableWidgetItem(_register_label(reg)),
                QTableWidgetItem(f"0x{int(reg.get('address', 0)):04X}"),
                QTableWidgetItem("---" if value is None else f"{value:.6g}"),
                QTableWidgetItem(unit),
                QTableWidgetItem(writable),
            ]
            for col, item in enumerate(items):
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter if col else Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row, col, item)

            button = QPushButton("Изменить")
            button.setEnabled(bool(reg.get("writable", True)))
            button.clicked.connect(lambda _checked=False, row_index=row: self._edit_register(row_index))
            self.table.setCellWidget(row, 5, button)

    def _edit_register(self, row: int):
        if row < 0 or row >= len(self.system_regs):
            return

        reg = self.system_regs[row]
        dlg = EditSystemRegisterDialog(
            sensor=self.sensor,
            reg_def=reg,
            current_value=self._values[row] if row < len(self._values) else None,
            parent=self,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh_values()
