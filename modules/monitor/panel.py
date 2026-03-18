# modules/monitor/panel.py
# Расположение: modules/monitor/panel.py
# Описание: Панель монитора – отображение карточек параметров.


# modules/monitor/panel.py
import tkinter as tk
from tkinter import ttk
import time
from .graph_window import GraphWindow

class MonitorPanel(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.core_api = app.core_api
        self.tr = app.tr
        self.polling = False
        self.after_id = None
        self.card_labels = {}
        self.history = {}          # история значений для графиков
        self.create_cards()

    def create_cards(self):
        for widget in self.winfo_children():
            widget.destroy()
        self.card_labels.clear()

        profile = self.core_api.get_current_profile_data()
        if not profile:
            ttk.Label(self, text=self.tr("monitor_no_profile")).pack(expand=True)
            return

        params = profile.get("parameters", [])
        if not params:
            ttk.Label(self, text=self.tr("monitor_no_params")).pack(expand=True)
            return

        max_cols = 3
        for i, p in enumerate(params):
            key = p["key"]
            display_name = self.tr(p.get("name_key", key))
            unit = p.get("unit", "")

            frame = ttk.LabelFrame(self, text=display_name, padding=5)
            frame.grid(row=i//max_cols, column=i%max_cols, padx=5, pady=5, sticky="nsew")
            val_label = ttk.Label(frame, text="---", font=('Arial', 16))
            val_label.pack()
            if unit:
                ttk.Label(frame, text=unit, font=('Arial', 8)).pack()
            self.card_labels[key] = val_label

            # Привязываем клик для открытия графика
            frame.bind("<Button-1>", lambda e, k=key, n=display_name, u=unit: self.open_graph(k, n, u))
            val_label.bind("<Button-1>", lambda e, k=key, n=display_name, u=unit: self.open_graph(k, n, u))

        for col in range(max_cols):
            self.columnconfigure(col, weight=1)

        if self.core_api.sensor and self.core_api.sensor.connected:
            self.start_polling()

    def start_polling(self):
        if not self.polling:
            self.polling = True
            self.poll_data()

    def stop_polling(self):
        self.polling = False
        if self.after_id:
            self.after_cancel(self.after_id)
            self.after_id = None

    def poll_data(self):
        if not self.polling or not self.core_api.sensor or not self.core_api.sensor.connected:
            return

        profile = self.core_api.get_current_profile_data()
        if not profile:
            self.stop_polling()
            return

        data = {}
        for p in profile.get("parameters", []):
            addr = p.get("address")
            if addr is None:
                continue
            vals = self.core_api.sensor.read_registers(addr, 1)
            if vals and len(vals) == 1:
                raw = vals[0]
                val = raw * p.get("factor", 1) + p.get("offset", 0)
                data[p["key"]] = val

        if data:
            for key, val in data.items():
                if key in self.card_labels:
                    self.card_labels[key].config(text=f"{val:.1f}" if isinstance(val, float) else str(val))
                if key not in self.history:
                    self.history[key] = []
                self.history[key].append(val)
                max_hist = self.core_api.settings.get("graph_settings", {}).get("max_history", 300)
                if len(self.history[key]) > max_hist:
                    self.history[key].pop(0)
            if self.core_api.logger:
                self.core_api.logger.log(data)
        else:
            for lbl in self.card_labels.values():
                lbl.config(text="---")

        if self.polling:
            self.after_id = self.after(2000, self.poll_data)

    def open_graph(self, key, title, unit):
        if key not in self.history:
            return
        colors = ['red', 'blue', 'green', 'purple', 'brown', 'orange', 'pink', 'cyan', 'magenta']
        color = colors[hash(key) % len(colors)]
        GraphWindow(self, title, unit, color, key, lambda: self.history.get(key, []), self.core_api.settings, self.tr)

    def show_disconnected(self):
        for lbl in self.card_labels.values():
            lbl.config(text="---")