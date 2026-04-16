from __future__ import annotations

from typing import Dict, Optional

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from core.constants import STANDARD_PARAMS
from qt_app.param_utils import ordered_param_keys, param_label
from qt_app.theme_utils import mark_styled_background


class ScannerAssignDialog(QDialog):
    def __init__(self, address: int, mapping: Optional[Dict], language: str = "ru", parent=None):
        super().__init__(parent)
        self.address = int(address)
        self.language = language if language in {"ru", "en", "zh"} else "ru"
        current = mapping or {}

        self.setWindowTitle(f"Назначение параметра: 0x{self.address:04X}")
        self.resize(380, 220)

        root = QWidget()
        mark_styled_background(root, "dialogSurface")

        self.param_combo = QComboBox()
        for key in ordered_param_keys(STANDARD_PARAMS.keys()):
            self.param_combo.addItem(param_label(key, self.language), key)

        current_param = current.get("param")
        if isinstance(current_param, str):
            index = self.param_combo.findData(current_param)
            if index >= 0:
                self.param_combo.setCurrentIndex(index)

        self.factor_spin = QDoubleSpinBox()
        self.factor_spin.setRange(-100000.0, 100000.0)
        self.factor_spin.setDecimals(6)
        self.factor_spin.setValue(float(current.get("factor", 1.0)))

        self.offset_spin = QDoubleSpinBox()
        self.offset_spin.setRange(-100000.0, 100000.0)
        self.offset_spin.setDecimals(6)
        self.offset_spin.setValue(float(current.get("offset", 0.0)))

        self.param_combo.currentIndexChanged.connect(self._apply_defaults_for_selected_param)

        form = QFormLayout()
        form.addRow("Параметр", self.param_combo)
        form.addRow("Factor", self.factor_spin)
        form.addRow("Offset", self.offset_spin)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._accept_if_valid)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(root)
        layout.addLayout(form)
        layout.addStretch(1)
        layout.addWidget(buttons)

        outer = QVBoxLayout(self)
        outer.addWidget(root)

        if not current_param:
            self._apply_defaults_for_selected_param()

    def _apply_defaults_for_selected_param(self):
        key = self.param_combo.currentData()
        if not isinstance(key, str):
            return
        defaults = STANDARD_PARAMS.get(key, {})
        self.factor_spin.setValue(float(defaults.get("factor", self.factor_spin.value())))
        self.offset_spin.setValue(float(defaults.get("offset", self.offset_spin.value())))

    def _accept_if_valid(self):
        key = self.param_combo.currentData()
        if not isinstance(key, str) or not key:
            QMessageBox.warning(self, "Сканер", "Выберите параметр.")
            return
        self.accept()

    def mapping(self) -> Dict:
        return {
            "param": str(self.param_combo.currentData()),
            "factor": float(self.factor_spin.value()),
            "offset": float(self.offset_spin.value()),
        }
