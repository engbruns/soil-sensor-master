from __future__ import annotations

from typing import Iterable, Optional

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt6.QtCore import QEvent
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QWidget

from qt_app.theme_utils import apply_matplotlib_theme, mark_styled_background


class ScannerGraphDialog(QDialog):
    def __init__(self, title: str, raw_values: Iterable[Optional[float]], median: Optional[float], parent=None):
        super().__init__(parent)
        self._raw_values = list(raw_values or [])
        self._median = median

        self.setWindowTitle(title)
        self.resize(860, 480)

        root = QWidget()
        mark_styled_background(root, "dialogSurface")

        self.figure = Figure(figsize=(7.4, 4.2), dpi=100)
        self.axes = self.figure.add_subplot(111)
        self.canvas = FigureCanvasQTAgg(self.figure)

        layout = QVBoxLayout(root)
        layout.addWidget(self.canvas)

        outer = QVBoxLayout(self)
        outer.addWidget(root)

        self._render()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.PaletteChange:
            self._render()

    def _render(self):
        self.axes.clear()

        valid_pairs = [(idx + 1, value) for idx, value in enumerate(self._raw_values) if value is not None]
        if valid_pairs:
            x = [idx for idx, _ in valid_pairs]
            y = [value for _, value in valid_pairs]
            self.axes.scatter(x, y, color="#2563eb", s=26, label="Сырые значения")
            self.axes.plot(x, y, color="#2563eb", linewidth=1.1, alpha=0.55)
            if self._median is not None:
                self.axes.axhline(self._median, color="#dc2626", linestyle="--", linewidth=1.3, label=f"Медиана = {self._median:.4g}")
            self.axes.set_xlim(0.5, max(x) + 0.5)
            self.axes.margins(y=0.12)
            self.axes.legend(loc="best")
        else:
            self.axes.text(0.5, 0.5, "Нет данных для отображения", ha="center", va="center")

        self.axes.set_title("Сырые значения регистра")
        self.axes.set_xlabel("Измерение")
        self.axes.set_ylabel("Значение")
        apply_matplotlib_theme(self, self.figure, self.axes)
        self.canvas.draw_idle()
