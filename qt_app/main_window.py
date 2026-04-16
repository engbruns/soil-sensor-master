from __future__ import annotations

import os
from collections import deque
from typing import Dict, List

from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QAction, QActionGroup, QDesktopServices, QGuiApplication
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from config import LOGS_DIR, PROFILES_DIR, load_config, save_config
from qt_app.backend.sensor_registry import SensorRegistry
from qt_app.styles import THEME_LIGHT, build_stylesheet, list_themes
from qt_app.theme_utils import mark_styled_background
from qt_app.widgets import CalibrationTab, MonitorTab, ProfilesTab, ScannerTab, SensorManagerWidget
from utils.i18n import Translator
from utils.profile_manager import ProfileManager


LANG_TEXTS: Dict[str, Dict[str, str]] = {
    "ru": {
        "window_title": "SoilSens Master",
        "menu_file": "Файл",
        "menu_modules": "Модули",
        "menu_view": "Вид",
        "menu_theme": "Тема",
        "menu_language": "Язык",
        "menu_info": "Информация",
        "action_save": "Сохранить конфиг",
        "action_exit": "Выход",
        "action_about": "О программе",
        "tab_monitor": "Монитор",
        "tab_scanner": "Сканер",
        "tab_calibration": "Калибровка",
        "tab_profiles": "Профили",
        "module_monitor": "Монитор",
        "module_scanner": "Сканер",
        "module_calibration": "Калибровка",
        "module_profiles": "Профили",
        "status_ready": "Готово",
        "status_saved": "Конфигурация сохранена",
        "health_caption": "Здоровье",
        "health_none": "Датчики: нет",
        "health_total": "всего",
        "health_ok": "OK",
        "health_unstable": "нестаб.",
        "health_reconnecting": "переподкл.",
        "health_degraded": "деград.",
        "theme_light": "Светлая серо-белая",
        "theme_matrix": "Matrix (зелёная)",
        "theme_dark": "Тёмная",
        "about": "SoilSens Master\n\nРазработчик: EngBruns\nВерсия: PyQt6",
        "sensor_group": "Датчики",
        "sensor_add_tooltip": "Добавить датчик. Ctrl+Shift+клик: добавить симулятор",
        "sensor_btn_remove": "Удалить",
        "sensor_btn_refresh": "Обновить",
        "sensor_status_connect": "Подключить",
        "sensor_status_disconnect": "Отключить",
        "sensor_status_error": "Ошибка",
        "sensor_status_unstable": "Нестабильно",
        "sensor_status_reconnecting": "Переподключение",
        "col_name": "Имя",
        "col_port": "Порт",
        "col_addr": "Адрес",
        "col_baud": "Скорость",
        "col_profile": "Профиль",
        "col_status": "Статус",
        "monitor_group": "Мониторинг",
        "monitor_data_group": "Текущие данные",
        "monitor_graph_settings": "Настройки графика",
        "monitor_poll": "Интервал, мс:",
        "monitor_hint": "График открывается кликом по строке параметра",
        "monitor_state": "Состояние",
        "monitor_param": "Параметр",
        "monitor_no_sensors": "Нет подключенных датчиков",
        "chart_title": "График",
        "chart_no_data": "Нет данных для отображения",
        "chart_axis_time": "t",
        "chart_axis_value": "value",
        "graph_auto": "Авто",
        "x_from": "X от",
        "x_to": "X до",
        "x_step": "X шаг",
        "y_from": "Y от",
        "y_to": "Y до",
        "y_step": "Y шаг",
        "graph_max_points": "Макс. точек",
        "graph_min": "Мин",
        "graph_max": "Макс",
        "graph_step": "Шаг",
        "graph_empty_params": "Нет параметров для настройки",
    },
    "en": {
        "window_title": "SoilSens Master",
        "menu_file": "File",
        "menu_modules": "Modules",
        "menu_view": "View",
        "menu_theme": "Theme",
        "menu_language": "Language",
        "menu_info": "Info",
        "action_save": "Save config",
        "action_exit": "Exit",
        "action_about": "About",
        "tab_monitor": "Monitor",
        "tab_scanner": "Scanner",
        "tab_calibration": "Calibration",
        "tab_profiles": "Profiles",
        "module_monitor": "Monitor",
        "module_scanner": "Scanner",
        "module_calibration": "Calibration",
        "module_profiles": "Profiles",
        "status_ready": "Ready",
        "status_saved": "Configuration saved",
        "health_caption": "Health",
        "health_none": "Sensors: none",
        "health_total": "total",
        "health_ok": "ok",
        "health_unstable": "unstable",
        "health_reconnecting": "reconnecting",
        "health_degraded": "degraded",
        "theme_light": "Light gray",
        "theme_matrix": "Matrix",
        "theme_dark": "Dark",
        "about": "SoilSens Master\n\nDeveloper: EngBruns\nVersion: PyQt6",
        "sensor_group": "Sensors",
        "sensor_add_tooltip": "Add sensor. Ctrl+Shift+click: add simulator",
        "sensor_btn_remove": "Remove",
        "sensor_btn_refresh": "Refresh",
        "sensor_status_connect": "Connect",
        "sensor_status_disconnect": "Disconnect",
        "sensor_status_error": "Error",
        "sensor_status_unstable": "Unstable",
        "sensor_status_reconnecting": "Reconnecting",
        "col_name": "Name",
        "col_port": "Port",
        "col_addr": "Address",
        "col_baud": "Baud",
        "col_profile": "Profile",
        "col_status": "Status",
        "monitor_group": "Monitoring",
        "monitor_data_group": "Current data",
        "monitor_graph_settings": "Graph settings",
        "monitor_poll": "Interval, ms:",
        "monitor_hint": "Click a parameter row to open chart",
        "monitor_state": "State",
        "monitor_param": "Parameter",
        "monitor_no_sensors": "No connected sensors",
        "chart_title": "Chart",
        "chart_no_data": "No data to display",
        "chart_axis_time": "t",
        "chart_axis_value": "value",
        "graph_auto": "Auto",
        "x_from": "X from",
        "x_to": "X to",
        "x_step": "X step",
        "y_from": "Y from",
        "y_to": "Y to",
        "y_step": "Y step",
        "graph_max_points": "Max points",
        "graph_min": "Min",
        "graph_max": "Max",
        "graph_step": "Step",
        "graph_empty_params": "No parameters to configure",
    },
    "zh": {
        "window_title": "SoilSens Master",
        "menu_file": "文件",
        "menu_modules": "模块",
        "menu_view": "视图",
        "menu_theme": "主题",
        "menu_language": "语言",
        "menu_info": "信息",
        "action_save": "保存配置",
        "action_exit": "退出",
        "action_about": "关于",
        "tab_monitor": "监控",
        "tab_scanner": "扫描",
        "tab_calibration": "校准",
        "tab_profiles": "配置",
        "module_monitor": "监控",
        "module_scanner": "扫描",
        "module_calibration": "校准",
        "module_profiles": "配置",
        "status_ready": "就绪",
        "status_saved": "配置已保存",
        "health_caption": "健康",
        "health_none": "传感器: 无",
        "health_total": "总计",
        "health_ok": "正常",
        "health_unstable": "不稳定",
        "health_reconnecting": "重连中",
        "health_degraded": "降级",
        "theme_light": "浅色",
        "theme_matrix": "矩阵",
        "theme_dark": "深色",
        "about": "SoilSens Master\n\n开发者: EngBruns\n版本: PyQt6",
        "sensor_group": "传感器",
        "sensor_add_tooltip": "添加传感器。Ctrl+Shift+点击: 添加模拟器",
        "sensor_btn_remove": "删除",
        "sensor_btn_refresh": "刷新",
        "sensor_status_connect": "连接",
        "sensor_status_disconnect": "断开",
        "sensor_status_error": "错误",
        "sensor_status_unstable": "不稳定",
        "sensor_status_reconnecting": "重连中",
        "col_name": "名称",
        "col_port": "端口",
        "col_addr": "地址",
        "col_baud": "波特率",
        "col_profile": "配置",
        "col_status": "状态",
        "monitor_group": "监控",
        "monitor_data_group": "当前数据",
        "monitor_graph_settings": "图表设置",
        "monitor_poll": "间隔, 毫秒:",
        "monitor_hint": "点击参数行打开图表",
        "monitor_state": "状态",
        "monitor_param": "参数",
        "monitor_no_sensors": "没有已连接传感器",
        "chart_title": "图表",
        "chart_no_data": "没有可显示的数据",
        "chart_axis_time": "t",
        "chart_axis_value": "value",
        "graph_auto": "自动",
        "x_from": "X 从",
        "x_to": "X 到",
        "x_step": "X 步长",
        "y_from": "Y 从",
        "y_to": "Y 到",
        "y_step": "Y 步长",
        "graph_max_points": "最大点数",
        "graph_min": "最小",
        "graph_max": "最大",
        "graph_step": "步长",
        "graph_empty_params": "没有可配置参数",
    },
}

class ErrorLogConsoleDialog(QDialog):
    def __init__(self, log_file: str, text_map: Dict[str, str], parent=None):
        super().__init__(parent)
        self.log_file = log_file
        self._texts = dict(text_map)

        self.hint_label = QLabel("")
        self.text_view = QPlainTextEdit()
        self.text_view.setReadOnly(True)
        self.refresh_button = QPushButton("")
        self.refresh_button.clicked.connect(self._refresh)

        controls = QHBoxLayout()
        controls.addStretch(1)
        controls.addWidget(self.refresh_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.hint_label)
        layout.addWidget(self.text_view, 1)
        layout.addLayout(controls)

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._refresh)
        self._timer.start()

        self.resize(860, 430)
        self._last_text = ""
        self.set_texts(self._texts)
        self._refresh()

    def set_texts(self, text_map: Dict[str, str]):
        self._texts.update(text_map)
        self.setWindowTitle(self._texts.get("debug_console_title", "Error Console"))
        self.hint_label.setText(self._texts.get("debug_console_hint", ""))
        self.refresh_button.setText(self._texts.get("debug_console_refresh", "Refresh"))
        self._refresh(force=True)

    def _read_tail(self, max_lines: int = 500) -> str:
        if not os.path.exists(self.log_file):
            return ""
        try:
            with open(self.log_file, "r", encoding="utf-8", errors="replace") as f:
                lines = deque(f, maxlen=max_lines)
            return "".join(lines).strip()
        except Exception as exc:
            return f"Failed to read log: {exc}"

    def _refresh(self, force: bool = False):
        text = self._read_tail()
        if not text:
            text = self._texts.get("debug_console_empty", "error.log is empty")
        if force or text != self._last_text:
            self.text_view.setPlainText(text)
            bar = self.text_view.verticalScrollBar()
            if bar:
                bar.setValue(bar.maximum())
            self._last_text = text

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)


class MainWindow(QMainWindow):
    TAB_ORDER = [
        ("monitor", "tab_monitor"),
        ("scanner", "tab_scanner"),
        ("calibration", "tab_calibration"),
        ("profiles", "tab_profiles"),
    ]

    def __init__(self):
        super().__init__()

        self.config_data = load_config()
        self.translator = Translator("ru")
        self.available_languages = self.translator.get_available_languages() or ["ru", "en", "zh"]

        self.current_theme = self._normalize_theme(self.config_data.get("app", {}).get("theme", THEME_LIGHT))
        self.current_language = self._normalize_language(self.config_data.get("app", {}).get("language", "ru"))
        self.translator.load_language(self.current_language)
        self.enabled_modules = self._normalize_modules(
            self.config_data.get("modules", {}).get("enabled", [k for k, _ in self.TAB_ORDER])
        )

        self.profile_manager = ProfileManager()
        self.profile_manager.create_default_profiles()
        self.registry = SensorRegistry(self.profile_manager)

        self.sensor_manager = SensorManagerWidget(
            registry=self.registry,
            profile_manager=self.profile_manager,
            settings=self.config_data,
        )

        self.tabs = QTabWidget()
        self.monitor_tab = MonitorTab(self.registry, self.config_data)
        monitor_interval = int(
            self.config_data.get("qt", {}).get("monitor_interval", self.monitor_tab.poll_interval.value())
        )
        self.monitor_tab.poll_interval.setValue(max(500, min(15000, monitor_interval)))

        self.scanner_tab = ScannerTab(self.registry, self.profile_manager)
        self.calibration_tab = CalibrationTab(self.registry, self.profile_manager)
        self.profiles_tab = ProfilesTab(self.profile_manager)

        self._tab_widget_by_key = {
            "monitor": self.monitor_tab,
            "scanner": self.scanner_tab,
            "calibration": self.calibration_tab,
            "profiles": self.profiles_tab,
        }
        self._tab_page_by_key = {k: self._wrap_scroll(v) for k, v in self._tab_widget_by_key.items()}

        self._tab_indices: Dict[str, int] = {}
        for key, _ in self.TAB_ORDER:
            idx = self.tabs.addTab(self._tab_page_by_key[key], key)
            self._tab_indices[key] = idx

        root = QWidget()
        mark_styled_background(root, "appRoot")
        layout = QVBoxLayout(root)
        self.main_splitter = QSplitter(Qt.Orientation.Vertical)
        self.main_splitter.setObjectName("mainVerticalSplitter")
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.setHandleWidth(8)
        self.main_splitter.addWidget(self.sensor_manager)
        self.main_splitter.addWidget(self.tabs)
        self.main_splitter.setStretchFactor(0, 2)
        self.main_splitter.setStretchFactor(1, 5)
        layout.addWidget(self.main_splitter, 1)
        self.setCentralWidget(root)

        self._fit_to_screen()
        self._restore_splitter_state()
        self._build_menu()
        self._wire_signals()
        self._init_health_indicator()
        self._debug_console_dialog: ErrorLogConsoleDialog | None = None

        self.apply_theme(self.current_theme, persist=False)
        self.apply_language(self.current_language, persist=False)
        self._apply_modules_visibility()

        self.monitor_tab.on_sensors_changed()
        self.scanner_tab.on_sensors_changed()
        self.calibration_tab.on_sensors_changed()

        self._on_tab_changed(self.tabs.currentIndex())
        self.statusBar().showMessage(self._t("status_ready"))

    def _wrap_scroll(self, widget: QWidget) -> QScrollArea:
        area = QScrollArea()
        area.setObjectName("moduleScrollArea")
        area.setWidgetResizable(True)
        area.setFrameShape(QFrame.Shape.NoFrame)
        area.setAlignment(Qt.AlignmentFlag.AlignTop)
        area.viewport().setObjectName("moduleScrollViewport")
        area.viewport().setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        container = QWidget()
        mark_styled_background(container, "moduleScrollContainer")
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(8, 8, 8, 8)
        c_layout.setSpacing(8)
        c_layout.addWidget(widget)

        area.setWidget(container)
        return area

    def _fit_to_screen(self):
        screen = QGuiApplication.primaryScreen()
        if not screen:
            self.resize(1100, 720)
            return

        rect = screen.availableGeometry()
        width = int(rect.width() * 0.84)
        height = int(rect.height() * 0.82)
        width = max(900, min(width, 1500))
        height = max(620, min(height, 920))
        width = min(width, max(640, rect.width() - 20))
        height = min(height, max(480, rect.height() - 20))
        self.resize(width, height)

    def _restore_splitter_state(self):
        qt_state = self.config_data.get("qt", {})
        sizes = qt_state.get("main_splitter_sizes")
        if isinstance(sizes, list) and len(sizes) == 2 and all(isinstance(v, int) and v > 0 for v in sizes):
            self.main_splitter.setSizes(sizes)
            return
        total = max(620, self.height())
        top = max(150, int(total * 0.28))
        bottom = max(320, total - top)
        self.main_splitter.setSizes([top, bottom])

    def _normalize_theme(self, theme: str) -> str:
        return theme if theme in list_themes() else THEME_LIGHT

    def _normalize_language(self, language: str) -> str:
        supported = self.available_languages or ["ru"]
        if language in supported:
            return language
        if "ru" in supported:
            return "ru"
        return supported[0]

    def _normalize_modules(self, modules: List[str]) -> List[str]:
        valid = [k for k, _ in self.TAB_ORDER]
        norm = [m for m in modules if m in valid]
        if not norm:
            return ["monitor"]
        return norm

    def _t(self, key: str) -> str:
        translated = self.translator.tr(key)
        if translated != key:
            return translated
        table = LANG_TEXTS.get(self.current_language, LANG_TEXTS["ru"])
        if key in table:
            return table[key]
        return LANG_TEXTS["ru"].get(key, key)

    def _build_menu(self):
        self.menuBar().setNativeMenuBar(False)

        self.menu_file = self.menuBar().addMenu("")
        self.act_save = QAction("", self)
        self.act_save.triggered.connect(self.save_state)
        self.menu_file.addAction(self.act_save)

        self.menu_file.addSeparator()

        self.act_open_profiles = QAction("", self)
        self.act_open_profiles.triggered.connect(self._open_profiles_folder)
        self.menu_file.addAction(self.act_open_profiles)

        self.act_open_logs = QAction("", self)
        self.act_open_logs.triggered.connect(self._open_logs_folder)
        self.menu_file.addAction(self.act_open_logs)

        self.act_debug_console = QAction("", self)
        self.act_debug_console.triggered.connect(self._open_debug_console)
        self.menu_file.addAction(self.act_debug_console)

        self.menu_file.addSeparator()

        self.act_exit = QAction("", self)
        self.act_exit.triggered.connect(self.close)
        self.menu_file.addAction(self.act_exit)

        self.menu_modules = self.menuBar().addMenu("")
        self._module_actions: Dict[str, QAction] = {}
        for key, _ in self.TAB_ORDER:
            act = QAction("", self)
            act.setCheckable(True)
            act.toggled.connect(lambda checked, k=key: self._on_module_toggled(k, checked))
            self.menu_modules.addAction(act)
            self._module_actions[key] = act

        self.menu_view = self.menuBar().addMenu("")
        self.menu_theme = self.menu_view.addMenu("")

        self._theme_group = QActionGroup(self)
        self._theme_group.setExclusive(True)
        self._theme_actions: Dict[str, QAction] = {}

        for theme in list_themes():
            act = QAction("", self)
            act.setCheckable(True)
            act.triggered.connect(lambda checked=False, t=theme: self.apply_theme(t, persist=True))
            self.menu_theme.addAction(act)
            self._theme_group.addAction(act)
            self._theme_actions[theme] = act

        self.menu_language = self.menuBar().addMenu("")
        self._lang_group = QActionGroup(self)
        self._lang_group.setExclusive(True)
        self._lang_actions: Dict[str, QAction] = {}
        for lang in self.available_languages:
            act = QAction(self.translator.get_language_display_name(lang), self)
            act.setCheckable(True)
            act.triggered.connect(lambda checked=False, l=lang: self.apply_language(l, persist=True))
            self.menu_language.addAction(act)
            self._lang_group.addAction(act)
            self._lang_actions[lang] = act

        self.menu_info = self.menuBar().addMenu("")
        self.act_about = QAction("", self)
        self.act_about.triggered.connect(self._show_about)
        self.menu_info.addAction(self.act_about)

    def _wire_signals(self):
        self.sensor_manager.sensors_changed.connect(self.monitor_tab.on_sensors_changed)
        self.sensor_manager.sensors_changed.connect(self.scanner_tab.on_sensors_changed)
        self.sensor_manager.sensors_changed.connect(self.calibration_tab.on_sensors_changed)
        self.sensor_manager.sensors_changed.connect(self._update_health_indicator)

        self.sensor_manager.sensor_rows_changed.connect(self.save_state)
        self.sensor_manager.sensor_rows_changed.connect(self._update_health_indicator)

        self.profiles_tab.profiles_changed.connect(self._on_profiles_changed)
        self.scanner_tab.profiles_changed.connect(self._on_profiles_changed)
        self.calibration_tab.profiles_changed.connect(self._on_profiles_changed)

        self.tabs.currentChanged.connect(self._on_tab_changed)

    def _init_health_indicator(self):
        self._health_label = QLabel("")
        self._health_label.setObjectName("statusHealthLabel")
        self._health_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._health_label.setMinimumWidth(320)
        self.statusBar().addPermanentWidget(self._health_label, 1)

        self._health_timer = QTimer(self)
        self._health_timer.setInterval(1200)
        self._health_timer.timeout.connect(self._update_health_indicator)
        self._health_timer.start()
        self._update_health_indicator()

    def _update_health_indicator(self):
        if not hasattr(self, "_health_label"):
            return

        health_items = self.registry.list_sensor_health()
        if not health_items:
            self._health_label.setText(self._t("health_none"))
            self._health_label.setToolTip("")
            self._health_label.setStyleSheet("")
            return

        total = len(health_items)
        ok_count = 0
        unstable_count = 0
        reconnecting_count = 0
        degraded_count = 0
        issue_lines: List[str] = []

        for item in health_items:
            status = str(item.get("status", "degraded"))
            name = str(item.get("name", "sensor"))
            last_error = str(item.get("last_error", "") or "")

            if status == "connected":
                ok_count += 1
            elif status == "unstable":
                unstable_count += 1
            elif status == "reconnecting":
                reconnecting_count += 1
            else:
                degraded_count += 1

            if status != "connected":
                suffix = f" ({last_error})" if last_error else ""
                issue_lines.append(f"{name}: {status}{suffix}")

        text = (
            f"{self._t('health_caption')}: "
            f"{self._t('health_total')} {total} | "
            f"{self._t('health_ok')} {ok_count} | "
            f"{self._t('health_unstable')} {unstable_count} | "
            f"{self._t('health_reconnecting')} {reconnecting_count} | "
            f"{self._t('health_degraded')} {degraded_count}"
        )
        self._health_label.setText(text)
        self._health_label.setToolTip("\n".join(issue_lines[:10]))

        if degraded_count > 0:
            self._health_label.setStyleSheet("color: #b42318;")
        elif unstable_count > 0 or reconnecting_count > 0:
            self._health_label.setStyleSheet("color: #b54708;")
        else:
            self._health_label.setStyleSheet("color: #027a48;")

    def _on_profiles_changed(self):
        self.sensor_manager.refresh_profiles()
        self.profiles_tab.refresh_profiles()

    def _on_tab_changed(self, _index: int):
        self._sync_tab_activity()

    def _sync_tab_activity(self):
        current_index = self.tabs.currentIndex()
        for key, widget in self._tab_widget_by_key.items():
            if not hasattr(widget, "set_active"):
                continue
            idx = self._tab_indices[key]
            visible = True
            if hasattr(self.tabs, "isTabVisible"):
                visible = bool(self.tabs.isTabVisible(idx))
            widget.set_active(visible and idx == current_index)

    def _on_module_toggled(self, key: str, checked: bool):
        enabled = set(self.enabled_modules)
        if checked:
            enabled.add(key)
        else:
            enabled.discard(key)

        if not enabled:
            enabled.add("monitor")
            self._module_actions["monitor"].blockSignals(True)
            self._module_actions["monitor"].setChecked(True)
            self._module_actions["monitor"].blockSignals(False)

        self.enabled_modules = [k for k, _ in self.TAB_ORDER if k in enabled]
        self._apply_modules_visibility()
        self.save_state()

    def _apply_modules_visibility(self):
        for key, _ in self.TAB_ORDER:
            action = self._module_actions.get(key)
            if action:
                action.blockSignals(True)
                action.setChecked(key in self.enabled_modules)
                action.blockSignals(False)

        if hasattr(self.tabs, "setTabVisible"):
            for key, idx in self._tab_indices.items():
                self.tabs.setTabVisible(idx, key in self.enabled_modules)

            current = self.tabs.currentIndex()
            current_visible = True
            if hasattr(self.tabs, "isTabVisible"):
                current_visible = bool(self.tabs.isTabVisible(current))

            if not current_visible:
                for key, idx in self._tab_indices.items():
                    if key in self.enabled_modules:
                        self.tabs.setCurrentIndex(idx)
                        break

        self._sync_tab_activity()

    def _theme_display_name(self, theme: str) -> str:
        key = f"theme_{theme}"
        return self._t(key)

    def _retranslate_ui(self):
        self.setWindowTitle(self._t("window_title"))

        self.menu_file.setTitle(self._t("menu_file"))
        self.menu_modules.setTitle(self._t("menu_modules"))
        self.menu_view.setTitle(self._t("menu_view"))
        self.menu_theme.setTitle(self._t("menu_theme"))
        self.menu_language.setTitle(self._t("menu_language"))
        self.menu_info.setTitle(self._t("menu_info"))

        self.act_save.setText(self._t("action_save"))
        self.act_open_profiles.setText(self._t("action_open_profiles"))
        self.act_open_logs.setText(self._t("action_open_logs"))
        self.act_debug_console.setText(self._t("action_debug_console"))
        self.act_exit.setText(self._t("action_exit"))
        self.act_about.setText(self._t("action_about"))

        for key, title_key in self.TAB_ORDER:
            self.tabs.setTabText(self._tab_indices[key], self._t(title_key))

        module_key_map = {
            "monitor": "module_monitor",
            "scanner": "module_scanner",
            "calibration": "module_calibration",
            "profiles": "module_profiles",
        }
        for key, act in self._module_actions.items():
            act.setText(self._t(module_key_map[key]))

        for theme, act in self._theme_actions.items():
            act.setText(self._theme_display_name(theme))

        lang_act = self._lang_actions.get(self.current_language)
        if lang_act:
            lang_act.setChecked(True)

        self.sensor_manager.set_texts(
            {
                "group_title": self._t("sensor_group"),
                "btn_add": "+",
                "btn_remove": self._t("sensor_btn_remove"),
                "btn_refresh_ports": self._t("sensor_btn_refresh"),
                "btn_add_tooltip": self._t("sensor_add_tooltip"),
                "status_connect": self._t("sensor_status_connect"),
                "status_disconnect": self._t("sensor_status_disconnect"),
                "status_error": self._t("sensor_status_error"),
                "status_unstable": self._t("sensor_status_unstable"),
                "status_reconnecting": self._t("sensor_status_reconnecting"),
                "col_name": self._t("col_name"),
                "col_port": self._t("col_port"),
                "col_addr": self._t("col_addr"),
                "col_baud": self._t("col_baud"),
                "col_profile": self._t("col_profile"),
                "col_status": self._t("col_status"),
            }
        )

        self.monitor_tab.set_texts(
            {
                "group_monitor": self._t("monitor_group"),
                "group_data": self._t("monitor_data_group"),
                "poll_interval": self._t("monitor_poll"),
                "click_hint": self._t("monitor_hint"),
                "btn_graph_settings": self._t("monitor_graph_settings"),
                "settings_dialog_title": self._t("monitor_graph_settings"),
                "header_state": self._t("monitor_state"),
                "header_param": self._t("monitor_param"),
                "no_sensors": self._t("monitor_no_sensors"),
                "chart_title": self._t("chart_title"),
                "chart_no_data": self._t("chart_no_data"),
                "axis_time": self._t("chart_axis_time"),
                "axis_value": self._t("chart_axis_value"),
                "graph_auto": self._t("graph_auto"),
                "x_from": self._t("x_from"),
                "x_to": self._t("x_to"),
                "x_step": self._t("x_step"),
                "y_from": self._t("y_from"),
                "y_to": self._t("y_to"),
                "y_step": self._t("y_step"),
                "graph_max_points": self._t("graph_max_points"),
                "graph_min": self._t("graph_min"),
                "graph_max": self._t("graph_max"),
                "graph_step": self._t("graph_step"),
                "graph_empty_params": self._t("graph_empty_params"),
            }
        )
        if self._debug_console_dialog is not None:
            self._debug_console_dialog.set_texts(
                {
                    "debug_console_title": self._t("debug_console_title"),
                    "debug_console_hint": self._t("debug_console_hint"),
                    "debug_console_empty": self._t("debug_console_empty"),
                    "debug_console_refresh": self._t("debug_console_refresh"),
                }
            )
        self._update_health_indicator()

    def apply_theme(self, theme: str, persist: bool):
        theme = self._normalize_theme(theme)
        self.current_theme = theme

        app = QApplication.instance()
        if app:
            app.setStyleSheet(build_stylesheet(theme))

        act = self._theme_actions.get(theme)
        if act:
            act.setChecked(True)

        if persist:
            self.config_data.setdefault("app", {})
            self.config_data["app"]["theme"] = theme
            save_config(self.config_data)

    def apply_language(self, language: str, persist: bool):
        self.current_language = self._normalize_language(language)
        self.translator.load_language(self.current_language)
        self._retranslate_ui()
        if hasattr(self.monitor_tab, "set_language"):
            self.monitor_tab.set_language(self.current_language)
        if hasattr(self.scanner_tab, "set_language"):
            self.scanner_tab.set_language(self.current_language)
        if hasattr(self.calibration_tab, "set_language"):
            self.calibration_tab.set_language(self.current_language)

        if persist:
            self.config_data.setdefault("app", {})
            self.config_data["app"]["language"] = self.current_language
            save_config(self.config_data)

    def _open_local_folder(self, path: str, error_key: str):
        try:
            os.makedirs(path, exist_ok=True)
            if QDesktopServices.openUrl(QUrl.fromLocalFile(path)):
                return
        except Exception:
            pass
        QMessageBox.warning(self, self._t("menu_file"), f"{self._t(error_key)}:\n{path}")

    def _open_profiles_folder(self):
        self._open_local_folder(PROFILES_DIR, "profiles_open_failed")

    def _open_logs_folder(self):
        self._open_local_folder(LOGS_DIR, "logs_open_failed")

    def _open_debug_console(self):
        text_map = {
            "debug_console_title": self._t("debug_console_title"),
            "debug_console_hint": self._t("debug_console_hint"),
            "debug_console_empty": self._t("debug_console_empty"),
            "debug_console_refresh": self._t("debug_console_refresh"),
        }
        log_file = os.path.join(LOGS_DIR, "error.log")
        if self._debug_console_dialog is None:
            self._debug_console_dialog = ErrorLogConsoleDialog(log_file, text_map, self)
        else:
            self._debug_console_dialog.set_texts(text_map)
        self._debug_console_dialog.show()
        self._debug_console_dialog.raise_()
        self._debug_console_dialog.activateWindow()

    def _show_about(self):
        QMessageBox.information(self, self._t("action_about"), self._t("about"))

    def save_state(self):
        self.sensor_manager.save_rows_to_settings()

        self.config_data.setdefault("qt", {})
        self.config_data.setdefault("app", {})
        self.config_data.setdefault("modules", {})

        self.config_data["qt"]["monitor_interval"] = int(self.monitor_tab.poll_interval.value())
        self.config_data["qt"]["main_splitter_sizes"] = [int(v) for v in self.main_splitter.sizes()]
        self.config_data["app"]["theme"] = self.current_theme
        self.config_data["app"]["language"] = self.current_language
        self.config_data["modules"]["enabled"] = list(self.enabled_modules)
        self.config_data["graph_settings"] = self.monitor_tab._graph_settings()
        self.config_data["graph_window"] = self.monitor_tab._graph_window()

        save_config(self.config_data)
        self.statusBar().showMessage(self._t("status_saved"), 2500)

    def _stop_workers(self):
        if hasattr(self.monitor_tab, "shutdown"):
            self.monitor_tab.shutdown()

        if self.scanner_tab.worker and self.scanner_tab.worker.isRunning():
            self.scanner_tab.worker.stop()
            self.scanner_tab.worker.wait(1500)

        if self.calibration_tab.collect_thread and self.calibration_tab.collect_thread.isRunning():
            self.calibration_tab.collect_thread.stop()
            self.calibration_tab.collect_thread.wait(1500)

    def closeEvent(self, event):
        try:
            if hasattr(self, "_health_timer"):
                self._health_timer.stop()
            self.save_state()
            self._stop_workers()
            self.registry.disconnect_all()
        except Exception as exc:
            QMessageBox.critical(self, "Close error", str(exc))
        event.accept()
