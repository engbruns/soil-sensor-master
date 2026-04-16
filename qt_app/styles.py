from __future__ import annotations

THEME_LIGHT = "light"
THEME_MATRIX = "matrix"
THEME_DARK = "dark"

THEME_CHOICES = {
    THEME_LIGHT: "Светлая",
    THEME_MATRIX: "Matrix (тёмно-зелёная)",
    THEME_DARK: "Тёмная",
}


def list_themes():
    return list(THEME_CHOICES.keys())


def theme_label(theme_name: str) -> str:
    return THEME_CHOICES.get(theme_name, theme_name)


def build_stylesheet(theme_name: str = THEME_LIGHT) -> str:
    if theme_name == THEME_MATRIX:
        return _matrix_theme()
    if theme_name == THEME_DARK:
        return _dark_theme()
    return _light_theme()


def _light_theme() -> str:
    return """
QMainWindow, QWidget {
    background-color: #f0f0f0;
    color: #202020;
}
QMenuBar {
    background-color: #efefef;
    color: #202020;
    border-bottom: 1px solid #bdbdbd;
}
QMenuBar::item {
    background: transparent;
    padding: 4px 10px;
}
QMenuBar::item:selected {
    background: #dfdfdf;
}
QMenu {
    background-color: #f5f5f5;
    color: #202020;
    border: 1px solid #b7b7b7;
}
QMenu::item:selected {
    background-color: #dfdfdf;
}
QPushButton {
    background-color: #ececec;
    color: #202020;
    border: 1px solid #a9a9a9;
    border-radius: 2px;
    padding: 4px 8px;
}
QPushButton:hover {
    background-color: #e3e3e3;
}
QPushButton:pressed {
    background-color: #d6d6d6;
}
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox, QAbstractSpinBox, QListWidget, QTableWidget {
    background-color: #ffffff;
    color: #202020;
    border: 1px solid #adadad;
    selection-background-color: #d9d9d9;
    selection-color: #202020;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    color: #202020;
    selection-background-color: #d9d9d9;
    selection-color: #202020;
}
QGroupBox {
    border: 1px solid #b3b3b3;
    border-radius: 2px;
    margin-top: 10px;
    padding-top: 4px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
    color: #303030;
}
QTabWidget::pane {
    border: 1px solid #b3b3b3;
    background: #f3f3f3;
}
QTabBar::tab {
    background: #e7e7e7;
    color: #202020;
    border: 1px solid #b3b3b3;
    border-bottom: none;
    padding: 5px 10px;
    margin-right: 1px;
}
QTabBar::tab:selected {
    background: #f3f3f3;
}
QHeaderView::section {
    background-color: #e5e5e5;
    color: #202020;
    border: 1px solid #b5b5b5;
    padding: 4px;
}
QTableWidget {
    gridline-color: #cdcdcd;
}
QSplitter::handle {
    background: #d3d3d3;
}
QSplitter::handle:hover {
    background: #c5c5c5;
}
QStatusBar {
    background: #efefef;
    color: #202020;
    border-top: 1px solid #bdbdbd;
}
QScrollBar:vertical, QScrollBar:horizontal {
    background: #efefef;
    border: 1px solid #c1c1c1;
}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background: #c7c7c7;
    min-height: 22px;
    min-width: 22px;
    border-radius: 2px;
}
QToolTip {
    background-color: #f8f8f8;
    color: #202020;
    border: 1px solid #b7b7b7;
}
"""


def _dark_theme() -> str:
    return """
QMainWindow, QWidget {
    background-color: #1e1f22;
    color: #e8e8e8;
}
QMenuBar {
    background-color: #25272b;
    color: #e8e8e8;
}
QMenuBar::item {
    background: transparent;
    padding: 4px 10px;
}
QMenuBar::item:selected {
    background: #34373d;
}
QMenu {
    background-color: #25272b;
    color: #e8e8e8;
    border: 1px solid #3b3f45;
}
QMenu::item:selected {
    background-color: #3a4f74;
}
QPushButton {
    background-color: #34373d;
    color: #f0f0f0;
    border: 1px solid #4a4f58;
    border-radius: 4px;
    padding: 4px 8px;
}
QPushButton:hover {
    background-color: #40444c;
}
QPushButton:pressed {
    background-color: #2a2d33;
}
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox, QAbstractSpinBox, QListWidget, QTableWidget {
    background-color: #25272b;
    color: #f0f0f0;
    border: 1px solid #4a4f58;
    selection-background-color: #3a4f74;
    selection-color: #ffffff;
}
QComboBox QAbstractItemView {
    background-color: #25272b;
    color: #f0f0f0;
    selection-background-color: #3a4f74;
}
QGroupBox {
    border: 1px solid #4a4f58;
    border-radius: 5px;
    margin-top: 10px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
    color: #d5d8dd;
}
QTabWidget::pane {
    border: 1px solid #4a4f58;
}
QTabBar::tab {
    background: #2b2e33;
    color: #d6d9de;
    border: 1px solid #4a4f58;
    padding: 6px 10px;
}
QTabBar::tab:selected {
    background: #3a4f74;
    color: #ffffff;
}
QHeaderView::section {
    background-color: #2f3238;
    color: #dce0e6;
    border: 1px solid #454a52;
    padding: 4px;
}
QScrollBar:vertical, QScrollBar:horizontal {
    background: #23252a;
}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background: #4a4f58;
    min-height: 24px;
    min-width: 24px;
    border-radius: 4px;
}
QToolTip {
    background-color: #2d3035;
    color: #f0f0f0;
    border: 1px solid #616670;
}
"""


def _matrix_theme() -> str:
    return """
QMainWindow, QWidget {
    background-color: #07110a;
    color: #b7efc5;
}
QMenuBar {
    background-color: #0c1b12;
    color: #b7efc5;
}
QMenuBar::item {
    background: transparent;
    padding: 4px 10px;
}
QMenuBar::item:selected {
    background: #143221;
}
QMenu {
    background-color: #0c1b12;
    color: #b7efc5;
    border: 1px solid #1c4730;
}
QMenu::item:selected {
    background-color: #1b4f34;
}
QPushButton {
    background-color: #12301f;
    color: #d9ffe3;
    border: 1px solid #2b7048;
    border-radius: 4px;
    padding: 4px 8px;
}
QPushButton:hover {
    background-color: #18452c;
}
QPushButton:pressed {
    background-color: #0f2518;
}
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox, QAbstractSpinBox, QListWidget, QTableWidget {
    background-color: #0f2518;
    color: #c8ffd9;
    border: 1px solid #2b7048;
    selection-background-color: #1f6b43;
    selection-color: #e9fff0;
}
QComboBox QAbstractItemView {
    background-color: #0f2518;
    color: #c8ffd9;
    selection-background-color: #1f6b43;
}
QGroupBox {
    border: 1px solid #2b7048;
    border-radius: 5px;
    margin-top: 10px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
    color: #9ee5b2;
}
QTabWidget::pane {
    border: 1px solid #2b7048;
}
QTabBar::tab {
    background: #12301f;
    color: #b7efc5;
    border: 1px solid #2b7048;
    padding: 6px 10px;
}
QTabBar::tab:selected {
    background: #1f6b43;
    color: #e9fff0;
}
QHeaderView::section {
    background-color: #12301f;
    color: #c8ffd9;
    border: 1px solid #2b7048;
    padding: 4px;
}
QScrollBar:vertical, QScrollBar:horizontal {
    background: #0b1b12;
}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background: #2b7048;
    min-height: 24px;
    min-width: 24px;
    border-radius: 4px;
}
QToolTip {
    background-color: #102918;
    color: #d9ffe3;
    border: 1px solid #2b7048;
}
"""
