from __future__ import annotations

import threading

import serial.tools.list_ports
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)

from qt_app.backend import services
from qt_app.theme_utils import mark_styled_background


class AddressSearchThread(QThread):
    progress_changed = pyqtSignal(int)
    finished_with_result = pyqtSignal(object, str)

    def __init__(self, sensor=None, port: str | None = None, baudrate: int = 4800):
        super().__init__()
        self.sensor = sensor
        self.port = port
        self.baudrate = int(baudrate)
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def run(self):
        try:
            found = services.search_device_addresses(
                sensor=self.sensor,
                port=self.port,
                baudrate=self.baudrate,
                stop_event=self._stop_event,
                progress_callback=lambda value: self.progress_changed.emit(value),
            )
            self.finished_with_result.emit(found, "")
        except Exception as exc:
            self.finished_with_result.emit([], str(exc))


class AddressSearchDialog(QDialog):
    def __init__(self, sensor_name: str, sensor, parent=None):
        super().__init__(parent)
        self.sensor_name = sensor_name
        self.sensor = sensor
        self.worker: AddressSearchThread | None = None

        self.setWindowTitle("Поиск адресов датчиков")
        self.resize(520, 420)

        root = QWidget()
        mark_styled_background(root, "dialogSurface")

        self.port_combo = QComboBox()
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["2400", "4800", "9600"])
        self.progress = QProgressBar()
        self.btn_start = QPushButton("Старт")
        self.status_label = QLabel("")

        self.results_table = QTableWidget(0, 1)
        self.results_table.setHorizontalHeaderLabels(["Найденные адреса"])
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.results_table.itemDoubleClicked.connect(self._copy_selected_address)

        info_box = QGroupBox("Параметры поиска")
        mark_styled_background(info_box)
        info_layout = QGridLayout(info_box)
        info_layout.addWidget(QLabel("Датчик"), 0, 0)
        info_layout.addWidget(QLabel(sensor_name or "---"), 0, 1)
        info_layout.addWidget(QLabel("COM-порт"), 1, 0)
        info_layout.addWidget(self.port_combo, 1, 1)
        info_layout.addWidget(QLabel("Скорость"), 2, 0)
        info_layout.addWidget(self.baud_combo, 2, 1)
        info_layout.addWidget(self.btn_start, 3, 0, 1, 2)
        info_layout.addWidget(self.progress, 4, 0, 1, 2)
        info_layout.addWidget(self.status_label, 5, 0, 1, 2)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)

        layout = QVBoxLayout(root)
        layout.addWidget(info_box)
        layout.addWidget(self.results_table, 1)
        layout.addWidget(buttons)

        outer = QVBoxLayout(self)
        outer.addWidget(root)

        self.btn_start.clicked.connect(self._toggle_search)
        self._refresh_ports()

    def _refresh_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        if not ports and self.sensor and getattr(self.sensor, "port", "") and str(self.sensor.port).lower() != "sim":
            ports = [str(self.sensor.port)]

        self.port_combo.clear()
        self.port_combo.addItems(ports)

        sensor_port = str(getattr(self.sensor, "port", "") or "")
        sensor_baud = str(getattr(self.sensor, "baudrate", "") or "")
        if sensor_port and sensor_port in ports:
            self.port_combo.setCurrentText(sensor_port)
        if sensor_baud and self.baud_combo.findText(sensor_baud) >= 0:
            self.baud_combo.setCurrentText(sensor_baud)

    def _toggle_search(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.btn_start.setEnabled(False)
            return

        port = self.port_combo.currentText().strip()
        if not self.sensor and not port:
            QMessageBox.warning(self, "Поиск адресов", "Выберите COM-порт.")
            return

        self.progress.setValue(0)
        self.status_label.setText("Сканирование...")
        self.results_table.setRowCount(0)
        self.btn_start.setText("Стоп")

        self.worker = AddressSearchThread(
            sensor=self.sensor if self.sensor and str(getattr(self.sensor, "port", "")).lower() != "sim" else None,
            port=None if self.sensor and str(getattr(self.sensor, "port", "")).lower() != "sim" else port,
            baudrate=int(self.baud_combo.currentText() or "4800"),
        )
        self.worker.progress_changed.connect(self.progress.setValue)
        self.worker.finished_with_result.connect(self._on_search_finished)
        self.worker.start()

    def _on_search_finished(self, found, error_text: str):
        self.btn_start.setText("Старт")
        self.btn_start.setEnabled(True)
        self.worker = None

        if error_text:
            self.status_label.setText("Ошибка поиска")
            QMessageBox.critical(self, "Поиск адресов", error_text)
            return

        found = list(found or [])
        self.progress.setValue(100 if found else self.progress.value())
        self.status_label.setText("Ничего не найдено" if not found else f"Найдено адресов: {len(found)}")
        self.results_table.setRowCount(len(found))
        for row, address in enumerate(found):
            item = QTableWidgetItem(str(address))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.results_table.setItem(row, 0, item)

    def _copy_selected_address(self, item: QTableWidgetItem):
        if item is None:
            return
        QApplication.clipboard().setText(item.text())
        QMessageBox.information(self, "Поиск адресов", f"Адрес {item.text()} скопирован в буфер обмена.")

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(1500)
        super().closeEvent(event)
