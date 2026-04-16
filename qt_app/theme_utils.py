from __future__ import annotations

from collections.abc import Iterable

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette


def mark_styled_background(widget, object_name: str | None = None) -> None:
    """Ensure plain QWidget surfaces paint stylesheet backgrounds."""
    if object_name:
        widget.setObjectName(object_name)
    widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)


def apply_matplotlib_theme(widget, figure, axes) -> None:
    """Sync matplotlib colors with the widget palette."""
    palette = widget.palette()
    base = palette.color(QPalette.ColorRole.Base).name()
    text = palette.color(QPalette.ColorRole.Text).name()
    grid = palette.color(QPalette.ColorRole.Mid).name()
    frame = palette.color(QPalette.ColorRole.Midlight).name()

    if not isinstance(axes, Iterable):
        axes = [axes]

    figure.patch.set_facecolor(base)
    for axis in axes:
        axis.set_facecolor(base)
        axis.title.set_color(text)
        axis.xaxis.label.set_color(text)
        axis.yaxis.label.set_color(text)
        axis.tick_params(axis="both", colors=text)
        for spine in axis.spines.values():
            spine.set_color(frame)
        axis.grid(True, color=grid, alpha=0.35)
