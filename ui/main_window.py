# ui/main_window.py
# Main application window.

import os
import sys
import tkinter as tk
from tkinter import messagebox, ttk

from config import load_config, save_config
from core.core_api import CoreAPI
from core.module_manager import ModuleManager
from ui.sensor_manager import SensorManagerPanel
from utils.i18n import Translator
from utils.profile_manager import ProfileManager


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.geometry("900x700")
        self.resizable(True, True)

        self.config_data = load_config()
        self.translator = Translator(self.config_data["app"]["language"])
        self.tr = self.translator.tr
        self.title(self.tr("window_title"))

        self.current_profile = None
        self.current_profile_data = None

        self.profile_manager = ProfileManager()
        self.profile_manager.create_default_profiles()

        self.core_api = CoreAPI(
            app=self,
            settings=self.config_data,
            profile_manager=self.profile_manager,
            logger=None,
            tr=self.tr,
        )

        self.module_manager = ModuleManager(self.core_api, modules_path="modules")
        self.module_manager.discover_modules()

        self.create_menu()
        self.create_sensor_manager()

        self.panel_container = ttk.Frame(self)
        self.panel_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.current_panel = None
        self.current_module_name = None
        self.module_panel_cache = {}
        self.placeholder_label = None

        self.load_modules()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Load saved sensor rows from user config.
        self.sensor_manager.load_from_config()

    def create_sensor_manager(self):
        self.sensor_manager = SensorManagerPanel(self, self.core_api, self.tr)
        self.sensor_manager.pack(fill=tk.X, padx=10, pady=5)

    def create_menu(self):
        self.menubar = tk.Menu(self)
        self.config(menu=self.menubar)

    def load_modules(self):
        enabled = self.config_data["modules"]["enabled"]
        self.module_manager.load_enabled_modules(enabled)
        if enabled:
            self.switch_module(enabled[0])
        self.rebuild_mode_menu()

    def rebuild_mode_menu(self):
        self.menubar.delete(0, "end")

        mode_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label=self.tr("menu_mode"), menu=mode_menu)
        panels = self.module_manager.get_active_panels()
        for name in panels.keys():
            mode_menu.add_command(label=name.capitalize(), command=lambda n=name: self.switch_module(n))

        settings_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label=self.tr("menu_settings"), menu=settings_menu)
        settings_menu.add_command(label=self.tr("menu_modules"), command=self.open_modules_settings)
        settings_menu.add_command(label=self.tr("menu.graphs"), command=self.open_graph_settings)

        lang_menu = tk.Menu(settings_menu, tearoff=0)
        settings_menu.add_cascade(label=self.tr("menu.language"), menu=lang_menu)
        available_langs = self.translator.get_available_languages()
        for lang_code in available_langs:
            display_name = self.translator.get_language_display_name(lang_code)
            lang_menu.add_command(label=display_name, command=lambda l=lang_code: self.change_language(l))

        about_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label=self.tr("menu_about"), menu=about_menu)
        about_menu.add_command(label=self.tr("about_text"), command=self.show_about)

    def switch_module(self, module_name):
        if self.current_panel:
            if hasattr(self.current_panel, "on_hide"):
                self.current_panel.on_hide()
            self.current_panel.pack_forget()

        if self.placeholder_label and self.placeholder_label.winfo_exists():
            self.placeholder_label.pack_forget()

        self.current_module_name = module_name
        panels = self.module_manager.get_active_panels()

        if module_name not in panels:
            if not self.placeholder_label or not self.placeholder_label.winfo_exists():
                self.placeholder_label = ttk.Label(self.panel_container, text=self.tr("module_not_active"))
            self.placeholder_label.pack(fill=tk.BOTH, expand=True)
            self.current_panel = None
            return

        panel = self.module_panel_cache.get(module_name)
        if panel is None or not panel.winfo_exists():
            panel_factory = panels[module_name]
            panel = panel_factory(self.panel_container)
            self.module_panel_cache[module_name] = panel

        self.current_panel = panel
        self.current_panel.pack(fill=tk.BOTH, expand=True)
        if hasattr(self.current_panel, "on_show"):
            self.current_panel.on_show()

    def refresh_modules_on_sensor_change(self):
        """Notifies active module panels about sensor list changes without resetting state."""
        for panel in list(self.module_panel_cache.values()):
            if panel and panel.winfo_exists() and hasattr(panel, "on_sensors_changed"):
                panel.on_sensors_changed()

    def refresh_profiles(self):
        if hasattr(self, "sensor_manager"):
            self.sensor_manager.refresh_profiles_all()

    def open_modules_settings(self):
        from .dialogs.modules_settings_dialog import ModulesSettingsDialog

        ModulesSettingsDialog(self, self.module_manager, self.config_data, self.tr)

    def open_graph_settings(self):
        from .dialogs.graph_settings_dialog import GraphSettingsDialog

        dlg = GraphSettingsDialog(self, self.core_api, self.tr)
        self.wait_window(dlg)
        if dlg.result:
            save_config(self.core_api.settings)

    def show_about(self):
        messagebox.showinfo(self.tr("menu_about"), self.tr("about_full_text"))

    def change_language(self, lang):
        self.config_data["app"]["language"] = lang
        save_config(self.config_data)
        os.execv(sys.executable, [sys.executable] + sys.argv)

    def load_profile(self, fname):
        data = self.profile_manager.get_profile(fname)
        if not data:
            return

        self.current_profile = fname
        self.current_profile_data = data
        self.config_data["last_profile"] = fname

        # Refresh profile selectors in sensor rows.
        self.refresh_profiles()

        # Notify currently created module panels if they need to refresh their view state.
        for panel in list(self.module_panel_cache.values()):
            if panel and panel.winfo_exists() and hasattr(panel, "on_profile_changed"):
                panel.on_profile_changed(fname, data)

    def on_closing(self):
        if hasattr(self, "sensor_manager"):
            self.sensor_manager.save_to_config()

        for panel in list(self.module_panel_cache.values()):
            if panel and panel.winfo_exists() and hasattr(panel, "on_hide"):
                panel.on_hide()

        self.module_manager.deactivate_all()
        self.core_api.disconnect_all()
        save_config(self.config_data)
        self.destroy()
