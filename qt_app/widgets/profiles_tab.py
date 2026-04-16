from __future__ import annotations

import json

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from qt_app.theme_utils import mark_styled_background


class ProfilesTab(QWidget):
    profiles_changed = pyqtSignal()

    def __init__(self, profile_manager, parent=None):
        super().__init__(parent)
        self.profile_manager = profile_manager
        mark_styled_background(self, "modulePanel")

        self.list_widget = QListWidget()
        self.editor = QTextEdit()

        self.btn_reload = QPushButton("Обновить")
        self.btn_save = QPushButton("Сохранить JSON")
        self.btn_duplicate = QPushButton("Дублировать")
        self.btn_delete = QPushButton("Удалить")
        self.btn_new = QPushButton("Новый")

        self._build_ui()
        self._wire()
        self.refresh_profiles()

    def _build_ui(self):
        list_box = QGroupBox("Список профилей")
        list_layout = QVBoxLayout(list_box)
        list_layout.addWidget(self.list_widget)

        editor_box = QGroupBox("Редактор профиля")
        editor_layout = QVBoxLayout(editor_box)
        editor_layout.addWidget(self.editor)

        splitter = QSplitter()
        splitter.addWidget(list_box)
        splitter.addWidget(editor_box)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        actions_box = QGroupBox("Действия")
        controls = QHBoxLayout(actions_box)
        for btn in [self.btn_reload, self.btn_save, self.btn_duplicate, self.btn_delete, self.btn_new]:
            controls.addWidget(btn)

        layout = QVBoxLayout(self)
        layout.addWidget(splitter, 3)
        layout.addWidget(actions_box)

    def _wire(self):
        self.list_widget.currentTextChanged.connect(self.load_selected_profile)
        self.btn_reload.clicked.connect(self.refresh_profiles)
        self.btn_save.clicked.connect(self.save_current_profile)
        self.btn_duplicate.clicked.connect(self.duplicate_current_profile)
        self.btn_delete.clicked.connect(self.delete_current_profile)
        self.btn_new.clicked.connect(self.create_new_profile)

    def refresh_profiles(self):
        current = self.list_widget.currentItem().text() if self.list_widget.currentItem() else ""

        self.profile_manager._load_all()
        profiles = sorted(self.profile_manager.list_profiles())

        self.list_widget.clear()
        self.list_widget.addItems(profiles)

        if current in profiles:
            self.list_widget.setCurrentRow(profiles.index(current))
        elif profiles:
            self.list_widget.setCurrentRow(0)

    def load_selected_profile(self, fname: str):
        data = self.profile_manager.get_profile(fname)
        if not data:
            self.editor.clear()
            return

        self.editor.setPlainText(json.dumps(data, indent=2, ensure_ascii=False))

    def save_current_profile(self):
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.warning(self, "Профили", "Выберите профиль")
            return

        fname = item.text()
        text = self.editor.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Профили", "Редактор пуст")
            return

        try:
            data = json.loads(text)
        except Exception as exc:
            QMessageBox.critical(self, "Профили", f"Некорректный JSON: {exc}")
            return

        if self.profile_manager.save_profile(fname, data):
            QMessageBox.information(self, "Профили", "Профиль сохранён")
            self.refresh_profiles()
            self.profiles_changed.emit()
        else:
            QMessageBox.critical(self, "Профили", "Ошибка сохранения")

    def duplicate_current_profile(self):
        item = self.list_widget.currentItem()
        if not item:
            return

        source = item.text()
        new_name, ok = QInputDialog.getText(self, "Дубликат", "Имя нового профиля:")
        if not ok or not new_name.strip():
            return

        if self.profile_manager.copy_profile(source, new_name.strip()):
            self.refresh_profiles()
            self.profiles_changed.emit()
        else:
            QMessageBox.critical(self, "Профили", "Не удалось создать дубликат")

    def delete_current_profile(self):
        item = self.list_widget.currentItem()
        if not item:
            return

        fname = item.text()
        ok = QMessageBox.question(self, "Удаление", f"Удалить профиль {fname}?")
        if ok != QMessageBox.StandardButton.Yes:
            return

        if self.profile_manager.delete_profile(fname):
            self.refresh_profiles()
            self.profiles_changed.emit()
        else:
            QMessageBox.critical(self, "Профили", "Ошибка удаления")

    def create_new_profile(self):
        name, ok = QInputDialog.getText(self, "Новый профиль", "Имя профиля:")
        if not ok or not name.strip():
            return

        fname = name.strip().replace(" ", "_").lower() + ".json"
        data = {
            "name": name.strip(),
            "description": "",
            "device": {
                "default_address": 1,
                "default_baudrate": 4800,
                "available_baudrates": [2400, 4800, 9600],
            },
            "parameters": [],
            "system_registers": [],
            "calibration": None,
        }

        if self.profile_manager.save_profile(fname, data):
            self.refresh_profiles()
            self.profiles_changed.emit()
            items = self.list_widget.findItems(fname, 0)
            if items:
                self.list_widget.setCurrentItem(items[0])
        else:
            QMessageBox.critical(self, "Профили", "Ошибка создания профиля")
