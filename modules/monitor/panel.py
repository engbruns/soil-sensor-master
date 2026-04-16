import tkinter as tk
from tkinter import ttk

import matplotlib.ticker as ticker
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from utils.utils import log_error
from utils.value_transform import convert_parameter_value


class MonitorPanel(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.core_api = app.core_api
        self.tr = app.tr

        self.polling = False
        self.after_id = None
        self._poll_in_progress = False

        self.last_sensor_list = []
        self.row_to_param = {}
        self.history = {}
        self.last_good_data = {}

        self.tree = None

        self.create_widgets()
        self.start_polling()

    def create_widgets(self):
        for widget in self.winfo_children():
            widget.destroy()

        self.tree = ttk.Treeview(self, columns=[], show="headings")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)

        self.tree.bind("<Button-1>", self.on_tree_click)

    def start_polling(self):
        if not self.polling:
            self.polling = True
            self._schedule_next_poll(0)

    def stop_polling(self):
        self.polling = False
        if self.after_id:
            try:
                self.after_cancel(self.after_id)
            except Exception:
                pass
            self.after_id = None

    def _schedule_next_poll(self, delay_ms=2000):
        if self.after_id:
            try:
                self.after_cancel(self.after_id)
            except Exception:
                pass
        self.after_id = self.after(delay_ms, self.poll_data)

    def on_show(self):
        self.start_polling()

    def on_hide(self):
        self.stop_polling()

    def on_sensors_changed(self):
        # Force table rebuild and immediate refresh.
        self.last_sensor_list = []
        if self.polling:
            self._schedule_next_poll(0)

    def destroy(self):
        self.stop_polling()
        super().destroy()

    def poll_data(self):
        if not self.polling or self._poll_in_progress:
            return

        self._poll_in_progress = True
        try:
            sensors = self.core_api.list_sensors()
            if sensors != self.last_sensor_list:
                self.rebuild_table(sensors)

            for cached_name in list(self.last_good_data.keys()):
                if cached_name not in sensors:
                    del self.last_good_data[cached_name]

            all_data = {}
            fresh_data = {}
            for name in sensors:
                sensor = self.core_api.get_sensor(name)
                data = self._read_sensor_data(sensor, name)

                if data is not None and not any(v is not None for v in data.values()):
                    data = None

                if data and self._is_suspicious_snapshot(data):
                    log_error(f"Monitor: suspicious flat snapshot detected for '{name}', fallback to last good")
                    data = None

                if data is not None:
                    self.last_good_data[name] = data
                    all_data[name] = data
                    fresh_data[name] = True
                else:
                    all_data[name] = self.last_good_data.get(name)
                    fresh_data[name] = False

            if self.tree and self.row_to_param:
                for row_id, param_key in self.row_to_param.items():
                    row_values = [self.tr(self.get_param_name(param_key))]
                    for name in sensors:
                        sensor_data = all_data.get(name)
                        if sensor_data and param_key in sensor_data:
                            val = sensor_data[param_key]
                            if isinstance(val, float):
                                text = f"{val:.1f}"
                            else:
                                text = str(val)
                            if not fresh_data.get(name, False):
                                text = f"~{text}"
                            row_values.append(text)
                        else:
                            row_values.append("---")
                    self.tree.item(row_id, values=row_values)

                for name in sensors:
                    if not fresh_data.get(name, False):
                        continue
                    sensor_data = all_data.get(name)
                    if not sensor_data:
                        continue
                    for param_key, val in sensor_data.items():
                        if val is None:
                            continue
                        self.history.setdefault(param_key, {}).setdefault(name, []).append(val)
                        max_hist = self.core_api.settings.get("graph_settings", {}).get("max_history", 300)
                        if len(self.history[param_key][name]) > max_hist:
                            self.history[param_key][name].pop(0)
        finally:
            self._poll_in_progress = False
            if self.polling:
                self._schedule_next_poll(2000)

    def _read_sensor_data(self, sensor, sensor_name):
        if not sensor or not sensor.connected or not getattr(sensor, "profile_data", None):
            return None

        try:
            result = {}
            for p in sensor.profile_data.get("parameters", []):
                addr = p.get("address")
                if addr is None:
                    continue
                vals = sensor.read_registers(addr, 1)
                if vals and len(vals) == 1:
                    raw = vals[0]
                    result[p["key"]] = convert_parameter_value(raw, p, sensor.profile_data)
                else:
                    result[p["key"]] = None
            return result
        except Exception as exc:
            log_error(f"Monitor: failed to read sensor '{sensor_name}': {exc}")
            return None

    def _is_suspicious_snapshot(self, data):
        numeric = [float(v) for v in data.values() if isinstance(v, (int, float))]
        if len(numeric) < 4:
            return False
        rounded = {round(v, 3) for v in numeric}
        return len(rounded) == 1

    def rebuild_table(self, sensors):
        self.last_sensor_list = sensors[:]
        self.row_to_param.clear()
        self.tree.delete(*self.tree.get_children())

        for col in self.tree["columns"]:
            self.tree.heading(col, text="")
            self.tree.column(col, width=0, minwidth=0)
        self.tree["columns"] = []

        if not sensors:
            self.tree["columns"] = ["message"]
            self.tree.heading("message", text=self.tr("no_sensors"))
            self.tree.column("message", width=300, minwidth=100)
            self.tree.insert("", tk.END, values=[self.tr("no_sensors")])
            return

        all_params = set()
        for name in sensors:
            sensor = self.core_api.get_sensor(name)
            if sensor and sensor.profile_data:
                for p in sensor.profile_data.get("parameters", []):
                    all_params.add(p["key"])

        if not all_params:
            self.tree["columns"] = ["message"]
            self.tree.heading("message", text=self.tr("no_params"))
            self.tree.column("message", width=300, minwidth=100)
            self.tree.insert("", tk.END, values=[self.tr("no_params")])
            return

        columns = ["parameter"] + sensors
        self.tree["columns"] = columns
        self.tree.heading("parameter", text=self.tr("parameter"))
        self.tree.column("parameter", width=150, minwidth=100, anchor=tk.W)

        for i, name in enumerate(sensors):
            col = f"#{i + 2}"
            self.tree.heading(col, text=name)
            self.tree.column(col, width=100, minwidth=80, anchor=tk.E)

        for param_key in sorted(all_params):
            row_id = self.tree.insert(
                "",
                tk.END,
                values=[self.tr(self.get_param_name(param_key))] + ["---"] * len(sensors),
            )
            self.row_to_param[row_id] = param_key

    def get_param_name(self, param_key):
        for sensor_name in self.core_api.list_sensors():
            sensor_obj = self.core_api.get_sensor(sensor_name)
            if sensor_obj and sensor_obj.profile_data:
                for p in sensor_obj.profile_data.get("parameters", []):
                    if p["key"] == param_key:
                        return p.get("name_key", param_key)
        return param_key

    def get_param_unit(self, param_key):
        for sensor_name in self.core_api.list_sensors():
            sensor_obj = self.core_api.get_sensor(sensor_name)
            if sensor_obj and sensor_obj.profile_data:
                for p in sensor_obj.profile_data.get("parameters", []):
                    if p["key"] == param_key:
                        return p.get("unit", "")
        return ""

    def on_tree_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return

        col = self.tree.identify_column(event.x)
        if col in {"#0", "#1"}:
            return

        row_id = self.tree.identify_row(event.y)
        if not row_id or row_id not in self.row_to_param:
            return

        param_key = self.row_to_param[row_id]
        col_index = int(col[1:]) - 2
        sensors = self.last_sensor_list
        if col_index < 0 or col_index >= len(sensors):
            return

        sensor_name = sensors[col_index]
        param_history = self.history.get(param_key, {})
        if not param_history:
            return

        title = self.get_param_name(param_key)
        unit = self.get_param_unit(param_key)
        GraphWindowMulti(self, param_key, title, unit, param_history, self.core_api.settings, self.tr)


class GraphWindowMulti(tk.Toplevel):
    def __init__(self, parent, param_key, title, unit, history_dict, settings, tr):
        super().__init__(parent)
        self.tr = tr
        self.param_key = param_key
        self.title(title or self.tr("graph.window.title"))
        self.geometry("600x500")

        self.history_dict = history_dict
        self.unit = unit
        self.settings = settings
        self._after_id = None

        self.create_widgets()
        self.update_graph()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        if self._after_id:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        self.destroy()

    def create_widgets(self):
        self.fig = Figure(figsize=(5, 4), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_xlabel(self.tr("graph.time_sec"))
        self.ax.set_ylabel(self.unit)
        self.ax.grid(True)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def update_graph(self):
        if not self.winfo_exists():
            return

        self.ax.clear()
        colors = ["blue", "red", "green", "orange", "purple", "brown", "pink", "gray", "olive", "cyan"]

        color_idx = 0
        for sensor_name, values in self.history_dict.items():
            if not values:
                continue
            x = list(range(len(values)))
            color = colors[color_idx % len(colors)]
            self.ax.plot(x, values, color=color, label=sensor_name, marker=".", markersize=3)
            color_idx += 1

        self.ax.set_xlabel(self.tr("graph.time_sec"))
        self.ax.set_ylabel(self.unit)
        self.ax.legend(loc="upper left", fontsize="small")
        self.ax.grid(True)

        y_limits = self.settings.get("graph_settings", {}).get("y_limits", {}).get(self.param_key, {})
        if not y_limits.get("auto", True):
            try:
                y_min = y_limits.get("min", 0)
                y_max = y_limits.get("max", 100)
                self.ax.set_ylim(y_min, y_max)
                step = y_limits.get("step")
                if step:
                    self.ax.yaxis.set_major_locator(ticker.MultipleLocator(step))
            except Exception:
                pass

        self.canvas.draw()
        self._after_id = self.after(2000, self.update_graph)
