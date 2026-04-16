# ui/sensor_manager.py
# Расположение: ui/sensor_manager.py
# Описание: Панель управления несколькими датчиками с динамическим растяжением колонок.
#           Одна кнопка "+" добавляет реальный датчик, Ctrl+Shift+клик добавляет симулятор.

import tkinter as tk
from tkinter import ttk, messagebox
import serial.tools.list_ports
from config import MODBUS_BAUDRATES
from utils.sensor import SoilSensor, SimulatedSoilSensor

class SensorManagerPanel(ttk.Frame):
    def __init__(self, parent, core_api, tr):
        super().__init__(parent)
        self.core_api = core_api
        self.tr = tr
        self.rows = []          # список словарей с виджетами для каждой строки
        self.column_count = 8   # количество колонок
        self.create_widgets()
        self.refresh_ports()

    def create_widgets(self):
        # Внешняя рамка
        self.frame = ttk.LabelFrame(self, text=self.tr("sensor_manager"), padding=5)
        self.frame.pack(fill=tk.X, expand=False, padx=5, pady=5)

        # Контейнер для таблицы с прокруткой
        self.table_canvas = tk.Canvas(self.frame, highlightthickness=0)
        self.table_canvas.configure(height=120)   # высота для ~3 строк
        self.scrollbar = ttk.Scrollbar(self.frame, orient="vertical", command=self.table_canvas.yview)
        self.table_canvas.configure(yscrollcommand=self.scrollbar.set)

        self.table_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Внутренний фрейм, где будут заголовки и строки
        self.table_frame = ttk.Frame(self.table_canvas)
        self.canvas_window = self.table_canvas.create_window((0,0), window=self.table_frame, anchor="nw")

        self.table_frame.bind("<Configure>", self._on_frame_configure)
        self.table_canvas.bind("<Configure>", self._on_canvas_configure)

        # Создаём заголовки и настраиваем колонки
        headers = [
            ("sensor_name", 12),
            ("port", 10),
            ("address", 6),
            ("baudrate", 8),
            ("profile", 20),
            ("status", 10),
            ("connect", 8),
            ("delete", 4)
        ]
        for col, (text_key, width) in enumerate(headers):
            label = ttk.Label(self.table_frame, text=self.tr(text_key), anchor=tk.CENTER)
            label.grid(row=0, column=col, padx=2, pady=2, sticky="ew")
            self.table_frame.columnconfigure(col, weight=1, minsize=width*8)

        # Кнопка добавления (одна) с tooltip
        btn_frame = ttk.Frame(self.frame)
        btn_frame.pack(fill=tk.X, pady=(5,0))

        self.add_btn = ttk.Button(btn_frame, text="+")
        self.add_btn.pack(side=tk.LEFT, padx=2)
        # Tooltip
        self._create_tooltip(self.add_btn, self.tr("add_sensor_tooltip"))
        # Привязываем обработчик нажатия с проверкой модификаторов
        self.add_btn.bind("<Button-1>", self.on_add_button_click)

    def _create_tooltip(self, widget, text):
        """Простой всплывающий tooltip."""
        def enter(event):
            self.tooltip = tk.Toplevel(widget)
            self.tooltip.wm_overrideredirect(True)
            self.tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            label = ttk.Label(self.tooltip, text=text, background="#ffffe0", relief=tk.SOLID, borderwidth=1)
            label.pack()
        def leave(event):
            if hasattr(self, 'tooltip'):
                self.tooltip.destroy()
                del self.tooltip
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)

    def on_add_button_click(self, event):
        """Обработчик клика по кнопке +. Если зажат Ctrl+Shift, добавляем симулятор, иначе реальный."""
        is_simulated = False
        # event.state & 0x0001 – Shift, 0x0004 – Ctrl (на Windows/Linux)
        if (event.state & 0x0001) and (event.state & 0x0004):
            is_simulated = True
        self.add_sensor_row(is_simulated=is_simulated)

    def _on_frame_configure(self, event):
        self.table_canvas.configure(scrollregion=self.table_canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.table_canvas.itemconfig(self.canvas_window, width=event.width)

    def add_sensor_row(self, is_simulated=False, sensor_name=None, port=None, address=1, baudrate=4800, profile=None):
        """Добавляет новую строку для датчика."""
        if sensor_name is None:
            existing_names = [row['name_var'].get() for row in self.rows]
            num = 1
            while f"Датчик {num}" in existing_names:
                num += 1
            sensor_name = f"Датчик {num}"

        row_num = len(self.rows) + 1
        row_frame = ttk.Frame(self.table_frame)
        row_frame.grid(row=row_num, column=0, columnspan=self.column_count, sticky="ew", pady=1)
        # Настраиваем колонки строки так же, как и в заголовке
        for col in range(self.column_count):
            row_frame.columnconfigure(col, weight=1)

        # Имя датчика (с возможностью редактирования двойным кликом)
        name_var = tk.StringVar(value=sensor_name)
        name_label = ttk.Label(row_frame, textvariable=name_var, anchor=tk.CENTER, relief=tk.SUNKEN)
        name_label.grid(row=0, column=0, padx=2, sticky="ew")
        # Двойной клик для редактирования
        def edit_name(event):
            entry = ttk.Entry(row_frame, textvariable=name_var, justify=tk.CENTER)
            entry.grid(row=0, column=0, padx=2, sticky="ew")
            entry.focus()
            def save_edit(e):
                name_var.set(entry.get())
                entry.destroy()
                name_label.grid(row=0, column=0, padx=2, sticky="ew")
            entry.bind("<Return>", save_edit)
            entry.bind("<FocusOut>", save_edit)
        name_label.bind("<Double-Button-1>", edit_name)

        # COM-порт
        if not is_simulated:
            port_combo = ttk.Combobox(row_frame, state="readonly")
            port_combo.grid(row=0, column=1, padx=2, sticky="ew")
        else:
            port_combo = ttk.Entry(row_frame, state="disabled")
            port_combo.insert(0, "sim")
            port_combo.grid(row=0, column=1, padx=2, sticky="ew")

        # Адрес
        addr_var = tk.IntVar(value=address)
        addr_spin = ttk.Spinbox(row_frame, from_=1, to=247, textvariable=addr_var, width=6)
        addr_spin.grid(row=0, column=2, padx=2, sticky="ew")

        # Скорость
        baud_var = tk.IntVar(value=baudrate)
        baud_combo = ttk.Combobox(row_frame, textvariable=baud_var, values=MODBUS_BAUDRATES)
        baud_combo.grid(row=0, column=3, padx=2, sticky="ew")

        # Профиль
        profile_combo = ttk.Combobox(row_frame, state="readonly")
        profile_combo.grid(row=0, column=4, padx=2, sticky="ew")
        self._refresh_profiles(profile_combo)
        if profile:
            profile_combo.set(profile)

        # Статус
        status_label = ttk.Label(row_frame, text=self.tr("disconnected"), foreground="red", anchor=tk.CENTER)
        status_label.grid(row=0, column=5, padx=2, sticky="ew")

        # Кнопка подключения
        connect_btn = ttk.Button(row_frame, text=self.tr("connect"))
        connect_btn.grid(row=0, column=6, padx=2, sticky="ew")

        # Кнопка удаления
        del_btn = ttk.Button(row_frame, text="✕")
        del_btn.grid(row=0, column=7, padx=2, sticky="ew")

        row_data = {
            'frame': row_frame,
            'name_var': name_var,
            'port_combo': port_combo,
            'addr_var': addr_var,
            'baud_var': baud_var,
            'profile_combo': profile_combo,
            'status_label': status_label,
            'connect_btn': connect_btn,
            'del_btn': del_btn,
            'is_simulated': is_simulated,
            'connected_sensor_name': None
        }
        self.rows.append(row_data)

        connect_btn.config(command=lambda: self._toggle_connection(row_data))
        del_btn.config(command=lambda: self._delete_row(row_data))

        if not is_simulated:
            self._refresh_ports_for_row(row_data)
        if port and not is_simulated:
            port_combo.set(port)

    def _refresh_ports_for_row(self, row_data):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        row_data['port_combo']['values'] = ports
        if not row_data['port_combo'].get() and ports:
            row_data['port_combo'].set(ports[0])

    def refresh_ports(self):
        for row in self.rows:
            if not row['is_simulated']:
                self._refresh_ports_for_row(row)

    def _refresh_profiles(self, profile_combo):
        profiles = self.core_api.profile_manager.list_profiles()
        profile_combo['values'] = profiles
        if not profile_combo.get() and profiles:
            profile_combo.set(profiles[0])

    def refresh_profiles_all(self):
        for row in self.rows:
            self._refresh_profiles(row['profile_combo'])

    def _toggle_connection(self, row_data):
        sensor_name = row_data['name_var'].get()
        is_simulated = row_data['is_simulated']

        connected_name = row_data.get('connected_sensor_name')
        lookup_name = connected_name or sensor_name

        existing = self.core_api.get_sensor(lookup_name)
        if existing and existing.connected:
            existing.disconnect()
            self.core_api.remove_sensor(lookup_name)
            row_data['connected_sensor_name'] = None
            row_data['status_label'].config(text=self.tr("disconnected"), foreground="red")
            row_data['connect_btn'].config(text=self.tr("connect"))
            self.core_api.app.refresh_modules_on_sensor_change()
            return

        if sensor_name in self.core_api.list_sensors():
            messagebox.showerror(self.tr("error"), f"{self.tr('sensor_name')}: {sensor_name} already exists")
            return

        if is_simulated:
            profile_fname = row_data['profile_combo'].get()
            profile_data = self.core_api.profile_manager.get_profile(profile_fname)
            if not profile_data:
                messagebox.showerror(self.tr("error"), self.tr("profile_not_found").format(profile_fname))
                return
            sensor = SimulatedSoilSensor(sensor_name, profile_data)
            sensor.profile_data = profile_data
            sensor.connected = True
            self.core_api.add_sensor(sensor_name, sensor)
            self.core_api.set_active_sensor(sensor_name)
            row_data['connected_sensor_name'] = sensor_name
            row_data['status_label'].config(text=self.tr("connected"), foreground="green")
            row_data['connect_btn'].config(text=self.tr("disconnect"))
            self.core_api.app.refresh_modules_on_sensor_change()
            return

        # Реальный датчик
        port = row_data['port_combo'].get()
        if not port:
            messagebox.showerror(self.tr("error"), self.tr("port_required"))
            return
        addr = row_data['addr_var'].get()
        baud = row_data['baud_var'].get()
        profile_fname = row_data['profile_combo'].get()
        if not profile_fname:
            messagebox.showerror(self.tr("error"), self.tr("profile_required"))
            return

        same_name, _ = self.core_api.get_sensor_by_port_and_address(port, addr)
        if same_name:
            messagebox.showerror(
                self.tr("error"),
                f"{self.tr('sensor')} {same_name} already uses {port} / addr {addr}"
            )
            return

        # Current architecture keeps one Serial handle per sensor object.
        # Avoid opaque failures when trying to connect several logical sensors to the same COM port.
        for existing_name in self.core_api.list_sensors():
            existing_sensor = self.core_api.get_sensor(existing_name)
            if (
                existing_sensor
                and getattr(existing_sensor, "connected", False)
                and getattr(existing_sensor, "port", None) == port
                and existing_name != row_data.get('connected_sensor_name')
            ):
                messagebox.showerror(
                    self.tr("error"),
                    f"{self.tr('port')}: {port} is already in use by {existing_name}"
                )
                return

        profile_data = self.core_api.profile_manager.get_profile(profile_fname)
        if not profile_data:
            messagebox.showerror(self.tr("error"), self.tr("profile_not_found").format(profile_fname))
            return

        sensor = SoilSensor(port, baud, slave_id=addr)
        if sensor.connect():
            if sensor.ping(retries=2):
                sensor.profile_data = profile_data
                self.core_api.add_sensor(sensor_name, sensor)
                self.core_api.set_active_sensor(sensor_name)
                row_data['connected_sensor_name'] = sensor_name
                row_data['status_label'].config(text=self.tr("connected"), foreground="green")
                row_data['connect_btn'].config(text=self.tr("disconnect"))
                self.core_api.app.refresh_modules_on_sensor_change()
            else:
                sensor.disconnect()
                messagebox.showerror(self.tr("error"),
                                     self.tr("connect_no_response").format(port, baud, addr))
        else:
            messagebox.showerror(self.tr("error"), self.tr("connect_failed").format(port))

    def _delete_row(self, row_data):
        sensor_name = row_data.get('connected_sensor_name') or row_data['name_var'].get()
        if sensor_name in self.core_api.list_sensors():
            self.core_api.remove_sensor(sensor_name)
        row_data['connected_sensor_name'] = None
        row_data['frame'].destroy()
        self.rows.remove(row_data)
        self.core_api.app.refresh_modules_on_sensor_change()

    def load_from_config(self):
        saved = self.core_api.settings.get("sensors", [])
        for item in saved:
            self.add_sensor_row(
                is_simulated=item.get("simulated", False),
                sensor_name=item.get("name"),
                port=item.get("port"),
                address=item.get("address", 1),
                baudrate=item.get("baudrate", 4800),
                profile=item.get("profile")
            )

    def save_to_config(self):
        sensors_list = []
        for row in self.rows:
            sensors_list.append({
                "name": row['name_var'].get(),
                "port": row['port_combo'].get() if not row['is_simulated'] else "sim",
                "address": row['addr_var'].get(),
                "baudrate": row['baud_var'].get(),
                "profile": row['profile_combo'].get(),
                "simulated": row['is_simulated']
            })
        self.core_api.settings["sensors"] = sensors_list
