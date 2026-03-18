# ui/main_window.py
# Расположение: ui/main_window.py
# Описание: Главное окно приложения. Содержит меню, панель инструментов и контейнер для панелей модулей.
# Версия с вынесенным адресом устройства (slave ID) в главную панель.

import tkinter as tk
from tkinter import ttk, messagebox
import serial.tools.list_ports
import sys
import os
from config import load_config, save_config, MODBUS_BAUDRATES
from core.core_api import CoreAPI
from core.module_manager import ModuleManager
from utils.sensor import SoilSensor
from utils.profile_manager import ProfileManager
from utils.logger import SessionLogger
from utils.i18n import Translator

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
        self.sensor = None
        self.logger = None

        self.port_var = tk.StringVar(value=self.config_data.get("last_port", ""))
        self.baudrate_var = tk.IntVar(value=self.config_data.get("last_baudrate", 4800))
        self.address_var = tk.IntVar(value=self.config_data.get("last_address", 1))  # новый атрибут
        self.profile_var = tk.StringVar()

        # API ядра (передаём переводчик, чтобы модули могли его использовать)
        self.core_api = CoreAPI(
            app=self,
            settings=self.config_data,
            profile_manager=self.profile_manager,
            logger=self.logger,
            sensor=self.sensor,
            tr=self.tr
        )

        # Менеджер модулей
        self.module_manager = ModuleManager(self.core_api, modules_path="modules")
        self.module_manager.discover_modules()

        self.create_menu()           # создаёт пустую строку меню
        self.create_toolbar()
        self.panel_container = ttk.Frame(self)
        self.panel_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.current_panel = None
        self.current_module_name = None
        self.load_modules()           # загружает модули и перестраивает меню
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_modules(self):
        print("Loading modules...")
        enabled = self.config_data["modules"]["enabled"]
        self.module_manager.load_enabled_modules(enabled)
        if enabled:
            self.switch_module(enabled[0])
        self.rebuild_mode_menu()

    def rebuild_mode_menu(self):
        print("Rebuilding mode menu")
        self.menubar.delete(0, 'end')
        mode_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label=self.tr("menu_mode"), menu=mode_menu)
        panels = self.module_manager.get_active_panels()
        print(f"Active panels: {list(panels.keys())}")
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
        self.update()

    def switch_module(self, module_name):
        print(f"switch_module called with {module_name}, current_module_name={self.current_module_name}")
        if self.current_panel:
            print("Destroying current panel")
            self.current_panel.destroy()
        self.current_module_name = module_name
        panels = self.module_manager.get_active_panels()
        if module_name in panels:
            panel_factory = panels[module_name]
            self.current_panel = panel_factory(self.panel_container)
            self.current_panel.pack(fill=tk.BOTH, expand=True)
            print(f"New panel created for {module_name}")
        else:
            ttk.Label(self.panel_container, text=self.tr("module_not_active")).pack()

    def create_menu(self):
        """Создаёт пустую строку меню. Фактическое наполнение произойдёт позже."""
        self.menubar = tk.Menu(self)
        self.config(menu=self.menubar)

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
        # Запускаем новый процесс с теми же аргументами
        import subprocess
        subprocess.Popen([sys.executable] + sys.argv)
        self.quit()
        sys.exit()

    def create_toolbar(self):
        toolbar = ttk.Frame(self, padding=5)
        toolbar.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(toolbar, text=self.tr("toolbar_port")).grid(row=0, column=0, padx=5)
        self.port_combo = ttk.Combobox(toolbar, textvariable=self.port_var, width=10)
        self.port_combo.grid(row=0, column=1, padx=5)
        ttk.Button(toolbar, text=self.tr("toolbar_refresh"), command=self.refresh_ports).grid(row=0, column=2, padx=5)

        ttk.Label(toolbar, text=self.tr("toolbar_baudrate")).grid(row=0, column=3, padx=5)
        baud_combo = ttk.Combobox(toolbar, textvariable=self.baudrate_var, values=MODBUS_BAUDRATES, width=8)
        baud_combo.grid(row=0, column=4, padx=5)

        # Новое поле: адрес устройства
        ttk.Label(toolbar, text=self.tr("device_address")).grid(row=0, column=5, padx=5)
        addr_spin = ttk.Spinbox(toolbar, from_=1, to=247, textvariable=self.address_var, width=5)
        addr_spin.grid(row=0, column=6, padx=5)

        ttk.Label(toolbar, text=self.tr("toolbar_profile")).grid(row=0, column=7, padx=5)
        self.profile_combo = ttk.Combobox(toolbar, textvariable=self.profile_var,
                                          values=self.profile_manager.list_profiles(), width=20)
        self.profile_combo.grid(row=0, column=8, padx=5)
        self.profile_combo.bind('<<ComboboxSelected>>', self.on_profile_selected)

        self.connect_btn = ttk.Button(toolbar, text=self.tr("toolbar_connect"), command=self.toggle_connection)
        self.connect_btn.grid(row=0, column=9, padx=10)

        self.status_label = ttk.Label(toolbar, text=self.tr("status_disconnected"), foreground="red")
        self.status_label.grid(row=0, column=10, padx=10)

        # Устанавливаем начальное значение профиля из конфига
        last_profile = self.config_data.get("last_profile", "")
        if last_profile:
            self.profile_var.set(last_profile)

        self.refresh_ports()

    def refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_combo['values'] = ports
        if ports and not self.port_var.get():
            self.port_var.set(ports[0])

    def on_profile_selected(self, event):
        fname = self.profile_var.get()
        data = self.profile_manager.get_profile(fname)
        if data:
            self.config_data["last_profile"] = fname
            self.current_profile_data = data
            # При желании можно подставить адрес из профиля, если он там есть, но мы не используем
            # if 'device' in data and 'default_address' in data['device']:
            #     self.address_var.set(data['device']['default_address'])
            if hasattr(self, 'current_module_name') and self.current_module_name:
                print(f"Profile changed to {fname}, reloading module {self.current_module_name}")
                self.switch_module(self.current_module_name)
            else:
                print("Profile selected before modules loaded, ignoring.")
        else:
            messagebox.showerror(self.tr("error"), self.tr("profile_not_found").format(fname))

    def toggle_connection(self):
        if not self.sensor or not self.sensor.connected:
            port = self.port_var.get()
            if not port:
                messagebox.showerror(self.tr("error"), self.tr("port_required"))
                return
            baud = self.baudrate_var.get()
            slave_id = self.address_var.get()   # используем выбранный адрес
            self.sensor = SoilSensor(port, baud, slave_id=slave_id)
            if self.sensor.connect():
                self.connect_btn.config(text=self.tr("toolbar_disconnect"))
                self.status_label.config(text=self.tr("status_connected"), foreground="green")
                self.logger = SessionLogger()
                self.core_api.sensor = self.sensor
                self.core_api.logger = self.logger
            else:
                messagebox.showerror(self.tr("error"), self.tr("connect_failed").format(port))
                self.sensor = None
        else:
            if self.sensor:
                self.sensor.disconnect()
                self.sensor = None
            if self.logger:
                self.logger.close()
                self.logger = None
            self.core_api.sensor = None
            self.core_api.logger = None
            self.connect_btn.config(text=self.tr("toolbar_connect"))
            self.status_label.config(text=self.tr("status_disconnected"), foreground="red")

    def on_closing(self):
        self.module_manager.deactivate_all()
        if self.sensor and self.sensor.connected:
            self.sensor.disconnect()
        if self.logger:
            self.logger.close()
        save_config(self.config_data)
        self.destroy()