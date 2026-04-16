# modules/calibration/panel.py
# Расположение: modules/calibration/panel.py
# Описание: Панель калибровки с чекбоксами параметров, адаптивным интерфейсом,
#           переключением типов графиков (точки / регрессия) и прокруткой.

# modules/calibration/panel.py
import tkinter as tk
from tkinter import ttk, messagebox
from utils.value_transform import convert_parameter_value

class CalibrationPanel(ttk.Frame):
    def __init__(self, parent, presenter, tr):
        super().__init__(parent)
        self.presenter = presenter
        self.tr = tr
        self.param_keys = []
        self.create_widgets()

    def create_widgets(self):
        # Контейнер с прокруткой
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.scrollable_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self._create_widgets_inside()

    def _on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _create_widgets_inside(self):
        # --- Таблица текущих показаний ---
        sensors_frame = ttk.LabelFrame(self.scrollable_frame, text=self.tr("current_sensors"), padding=5)
        sensors_frame.pack(fill=tk.X, padx=10, pady=5)

        self.sensors_tree = ttk.Treeview(sensors_frame, columns=[], show="headings", height=3)
        vsb = ttk.Scrollbar(sensors_frame, orient="vertical", command=self.sensors_tree.yview)
        hsb = ttk.Scrollbar(sensors_frame, orient="horizontal", command=self.sensors_tree.xview)
        self.sensors_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.sensors_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        sensors_frame.grid_rowconfigure(0, weight=1)
        sensors_frame.grid_columnconfigure(0, weight=1)

        # --- Верхняя строка: режим/датчики и параметры ---
        top_row = ttk.Frame(self.scrollable_frame)
        top_row.pack(fill=tk.X, padx=10, pady=5)

        # Левая часть: режим и датчики
        mode_sensor_frame = ttk.LabelFrame(top_row, text=self.tr("mode_and_sensors"), padding=5)
        mode_sensor_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0,10))

        ttk.Label(mode_sensor_frame, text=self.tr("mode")).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.mode = tk.StringVar(value="lab")
        ttk.Radiobutton(mode_sensor_frame, text=self.tr("lab_mode"), variable=self.mode, value="lab",
                        command=self.on_mode_change).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        ttk.Radiobutton(mode_sensor_frame, text=self.tr("ref_mode"), variable=self.mode, value="ref",
                        command=self.on_mode_change).grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)

        ttk.Label(mode_sensor_frame, text=self.tr("calib_sensor")).grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.calib_sensor_combo = ttk.Combobox(mode_sensor_frame, state="readonly", width=25)
        self.calib_sensor_combo.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky=tk.W)
        self.calib_sensor_combo.bind("<<ComboboxSelected>>", self.on_calib_sensor_selected)

        self.ref_sensor_frame = ttk.Frame(mode_sensor_frame)
        ttk.Label(self.ref_sensor_frame, text=self.tr("ref_sensor")).pack(side=tk.LEFT, padx=5)
        self.ref_sensor_combo = ttk.Combobox(self.ref_sensor_frame, state="readonly", width=25)
        self.ref_sensor_combo.pack(side=tk.LEFT, padx=5)
        self.ref_sensor_combo.bind("<<ComboboxSelected>>", self.on_ref_sensor_selected)
        self.ref_sensor_frame.grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky=tk.W)
        self.ref_sensor_frame.grid_remove()

        # Правая часть: параметры
        params_frame = ttk.LabelFrame(top_row, text=self.tr("select_params"), padding=5)
        params_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.params_container = ttk.Frame(params_frame)
        self.params_container.pack(fill=tk.X, padx=5, pady=5)
        self.param_vars = {}
        self.param_keys = []

        # --- Сбор точки ---
        collect_frame = ttk.LabelFrame(self.scrollable_frame, text=self.tr("collect_point"), padding=5)
        collect_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(collect_frame, text=self.tr("num_samples")).pack(side=tk.LEFT, padx=5)
        self.samples_var = tk.IntVar(value=10)
        ttk.Spinbox(collect_frame, from_=1, to=100, textvariable=self.samples_var, width=8).pack(side=tk.LEFT, padx=5)

        self.add_btn = ttk.Button(collect_frame, text=self.tr("add_point"), command=self.add_point)
        self.add_btn.pack(side=tk.LEFT, padx=10)

        self.progress = ttk.Progressbar(collect_frame, orient=tk.HORIZONTAL, length=150, mode='indeterminate')
        self.progress.pack(side=tk.LEFT, padx=10)

        # --- Таблица точек ---
        points_frame = ttk.LabelFrame(self.scrollable_frame, text=self.tr("points"), padding=5)
        points_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ("№", "Время", "Параметр", "Тип", "Медиана", "Среднее", "Макс", "Мин", "График")
        self.points_tree = ttk.Treeview(points_frame, columns=columns, show="headings", height=8)
        for col in columns:
            self.points_tree.heading(col, text=col)
            self.points_tree.column(col, width=80, anchor=tk.CENTER)
        self.points_tree.column("Параметр", width=120)
        self.points_tree.column("Тип", width=60)
        self.points_tree.column("График", width=60)

        vsb_points = ttk.Scrollbar(points_frame, orient="vertical", command=self.points_tree.yview)
        hsb_points = ttk.Scrollbar(points_frame, orient="horizontal", command=self.points_tree.xview)
        self.points_tree.configure(yscrollcommand=vsb_points.set, xscrollcommand=hsb_points.set)
        self.points_tree.grid(row=0, column=0, sticky="nsew")
        vsb_points.grid(row=0, column=1, sticky="ns")
        hsb_points.grid(row=1, column=0, sticky="ew")
        points_frame.grid_rowconfigure(0, weight=1)
        points_frame.grid_columnconfigure(0, weight=1)

        self.points_tree.bind("<Button-1>", self.on_points_tree_click)

        # --- Управление графиком ---
        graph_control_frame = ttk.Frame(self.scrollable_frame)
        graph_control_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(graph_control_frame, text=self.tr("graph_type")).pack(side=tk.LEFT, padx=5)
        self.graph_type = tk.StringVar(value="points")
        ttk.Radiobutton(graph_control_frame, text=self.tr("points_graph"), variable=self.graph_type, value="points",
                        command=self.on_graph_type_changed).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(graph_control_frame, text=self.tr("regression_graph"), variable=self.graph_type, value="regression",
                        command=self.on_graph_type_changed).pack(side=tk.LEFT, padx=5)

        self.refresh_graph_btn = ttk.Button(graph_control_frame, text=self.tr("refresh_graph"), command=self.refresh_graph)
        self.refresh_graph_btn.pack(side=tk.LEFT, padx=10)

        ttk.Label(graph_control_frame, text=self.tr("graph_param")).pack(side=tk.LEFT, padx=10)
        self.graph_param_combo = ttk.Combobox(graph_control_frame, state="readonly", width=12)
        self.graph_param_combo.pack(side=tk.LEFT, padx=5)
        self.graph_param_combo.bind("<<ComboboxSelected>>", self.on_graph_param_selected)

        # --- Кнопки действий ---
        control_frame = ttk.Frame(self.scrollable_frame)
        control_frame.pack(fill=tk.X, padx=10, pady=5)

        self.calc_btn = ttk.Button(control_frame, text=self.tr("calc_regression"), command=self.calc_regression, state=tk.DISABLED)
        self.calc_btn.pack(side=tk.LEFT, padx=5)

        self.save_btn = ttk.Button(control_frame, text=self.tr("save_calib"), command=self.save_calib, state=tk.DISABLED)
        self.save_btn.pack(side=tk.LEFT, padx=5)

        self.export_btn = ttk.Button(control_frame, text=self.tr("export_csv"), command=self.export_csv, state=tk.NORMAL)
        self.export_btn.pack(side=tk.LEFT, padx=5)

        self.remove_btn = ttk.Button(control_frame, text=self.tr("remove_point"), command=self.remove_point, state=tk.DISABLED)
        self.remove_btn.pack(side=tk.LEFT, padx=5)

        ttk.Label(control_frame, text=self.tr("model")).pack(side=tk.LEFT, padx=10)
        self.model_combo = ttk.Combobox(control_frame, values=["linear", "poly2", "poly3"], state="readonly", width=8)
        self.model_combo.set("linear")
        self.model_combo.pack(side=tk.LEFT, padx=5)

        # --- Системные регистры ---
        sys_btn_frame = ttk.Frame(self.scrollable_frame)
        sys_btn_frame.pack(fill=tk.X, padx=10, pady=5)
        self.sys_reg_btn = ttk.Button(sys_btn_frame, text=self.tr("system_registers"), command=self.presenter.open_system_registers)
        self.sys_reg_btn.pack(side=tk.LEFT, padx=5)

        # --- График ---
        graph_frame = ttk.LabelFrame(self.scrollable_frame, text=self.tr("graph"), padding=5)
        graph_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.graph_canvas = tk.Canvas(graph_frame, bg='white')
        self.graph_canvas.pack(fill=tk.BOTH, expand=True)

        # Загружаем список датчиков
        self.update_sensor_lists(self.presenter.core_api.list_sensors())

    # ---- Методы интерфейса ----
    def update_sensor_lists(self, sensors):
        prev_calib = self.calib_sensor_combo.get()
        prev_ref = self.ref_sensor_combo.get()

        self.calib_sensor_combo['values'] = sensors
        self.ref_sensor_combo['values'] = sensors

        if prev_calib in sensors:
            self.calib_sensor_combo.set(prev_calib)
        elif sensors:
            self.calib_sensor_combo.set(sensors[0])
        else:
            self.calib_sensor_combo.set("")

        if prev_ref in sensors:
            self.ref_sensor_combo.set(prev_ref)
        elif len(sensors) > 1:
            self.ref_sensor_combo.set(sensors[1] if sensors[0] == self.calib_sensor_combo.get() else sensors[0])
        else:
            self.ref_sensor_combo.set("")

    def update_params_list(self, params):
        for widget in self.params_container.winfo_children():
            widget.destroy()
        self.param_vars.clear()
        self.param_keys.clear()
        for p in params:
            key = p['key']
            display = self.tr(p.get('name_key', key))
            var = tk.BooleanVar()
            cb = ttk.Checkbutton(self.params_container, text=display, variable=var)
            cb.pack(anchor=tk.W, padx=5)
            self.param_vars[key] = var
            self.param_keys.append(key)

        self.graph_param_combo['values'] = [self.tr(k) for k in self.param_keys]
        if self.param_keys:
            self.graph_param_combo.set(self.tr(self.param_keys[0]))
            self.presenter.on_graph_param_selected(self.param_keys[0])

    def get_selected_params(self):
        return [key for key, var in self.param_vars.items() if var.get()]

    def on_mode_change(self):
        mode = self.mode.get()
        if mode == 'lab':
            self.ref_sensor_frame.grid_remove()
        else:
            self.ref_sensor_frame.grid()
        self.presenter.on_mode_changed(mode)

    def on_calib_sensor_selected(self, event):
        name = self.calib_sensor_combo.get()
        if name:
            self.presenter.on_calib_sensor_selected(name)

    def on_ref_sensor_selected(self, event):
        name = self.ref_sensor_combo.get()
        if name:
            self.presenter.on_ref_sensor_selected(name)

    def update_current_sensors_table(self, data):
        sensors = list(data.keys())
        if not sensors:
            self.sensors_tree.delete(*self.sensors_tree.get_children())
            return
        all_params = set()
        for d in data.values():
            all_params.update(d.keys())
        all_params = sorted(all_params)
        current_cols = self.sensors_tree["columns"]
        expected_cols = ["parameter"] + sensors
        if list(current_cols) != expected_cols:
            self._rebuild_sensors_table(sensors, all_params)
            return
        value_map = {}
        for param in all_params:
            value_map[param] = {}
            for sensor in sensors:
                val = data.get(sensor, {}).get(param)
                value_map[param][sensor] = val
        for row_id in self.sensors_tree.get_children():
            param_display = self.sensors_tree.item(row_id, "values")[0]
            tags = self.sensors_tree.item(row_id, "tags")
            if not tags:
                continue
            param_key = tags[0]
            row_values = [param_display]
            for sensor in sensors:
                val = value_map.get(param_key, {}).get(sensor)
                if val is not None:
                    row_values.append(f"{val:.1f}" if isinstance(val, float) else str(val))
                else:
                    row_values.append("---")
            self.sensors_tree.item(row_id, values=row_values)

    def _rebuild_sensors_table(self, sensors, all_params):
        for row in self.sensors_tree.get_children():
            self.sensors_tree.delete(row)
        columns = ["parameter"] + sensors
        self.sensors_tree["columns"] = columns
        for col in columns:
            self.sensors_tree.heading(col, text=col)
            self.sensors_tree.column(col, width=100, anchor=tk.CENTER)
        self.sensors_tree.heading("parameter", text=self.tr("parameter"))
        for param in all_params:
            param_display = self.tr(param)
            self.sensors_tree.insert("", tk.END, values=[param_display] + ["---"] * len(sensors), tags=(param,))

    def _get_param_def(self, param_key, ref=False):
        info = self.ref_param_info if ref else self.param_info
        return info.get(param_key, {"key": param_key})

    def _convert_raw(self, raw, param_key, ref=False):
        if raw is None:
            return None
        param_def = self._get_param_def(param_key, ref=ref)
        # Calibration panel should use engineering conversion without applying saved calibration model.
        return convert_parameter_value(raw, param_def, None)

    def update_points_table(self, points, param_info, ref_param_info):
        self.param_info = param_info or {}
        self.ref_param_info = ref_param_info or {}
        self.points_tree.delete(*self.points_tree.get_children())
        if not points:
            self.remove_btn.config(state=tk.DISABLED)
            return
        self.remove_btn.config(state=tk.NORMAL)
        for i, point in enumerate(points):
            point_num = i + 1
            timestamp = point.get('timestamp', '')
            selected_params = point.get('selected_params', [])
            for param in selected_params:
                raw_stat = point['raw_stats'].get(param)
                if raw_stat:
                    median = self._convert_raw(raw_stat.get('median'), param, ref=False)
                    avg = self._convert_raw(raw_stat.get('avg'), param, ref=False)
                    max_val = self._convert_raw(raw_stat.get('max'), param, ref=False)
                    min_val = self._convert_raw(raw_stat.get('min'), param, ref=False)
                    row = [
                        point_num,
                        timestamp,
                        self.tr(param),
                        self.tr("calib"),
                        f"{median:.2f}" if median is not None else '---',
                        f"{avg:.2f}" if avg is not None else '---',
                        f"{max_val:.2f}" if max_val is not None else '---',
                        f"{min_val:.2f}" if min_val is not None else '---',
                        self.tr("graph")
                    ]
                    self.points_tree.insert('', tk.END, values=row, tags=(param, 'calib', str(i)))
                if point.get('ref_values'):
                    ref_val = point['ref_values'].get(param)
                    if ref_val is not None:
                        row = [
                            point_num,
                            timestamp,
                            self.tr(param),
                            self.tr("ref"),
                            f"{ref_val:.2f}",
                            f"{ref_val:.2f}",
                            f"{ref_val:.2f}",
                            f"{ref_val:.2f}",
                            self.tr("graph")
                        ]
                        self.points_tree.insert('', tk.END, values=row, tags=(param, 'ref', str(i)))
                elif point.get('ref_stats'):
                    ref_stat = point['ref_stats'].get(param)
                    if ref_stat and ref_param_info:
                        median_r = self._convert_raw(ref_stat.get('median'), param, ref=True)
                        avg_r = self._convert_raw(ref_stat.get('avg'), param, ref=True)
                        max_r = self._convert_raw(ref_stat.get('max'), param, ref=True)
                        min_r = self._convert_raw(ref_stat.get('min'), param, ref=True)
                        row = [
                            point_num,
                            timestamp,
                            self.tr(param),
                            self.tr("ref"),
                            f"{median_r:.2f}" if median_r is not None else '---',
                            f"{avg_r:.2f}" if avg_r is not None else '---',
                            f"{max_r:.2f}" if max_r is not None else '---',
                            f"{min_r:.2f}" if min_r is not None else '---',
                            self.tr("graph")
                        ]
                        self.points_tree.insert('', tk.END, values=row, tags=(param, 'ref', str(i)))

    def start_progress(self):
        self.progress.start(10)

    def stop_progress(self):
        self.progress.stop()

    def enable_calc_save(self, enabled):
        state = tk.NORMAL if enabled else tk.DISABLED
        self.calc_btn.config(state=state)
        self.save_btn.config(state=state)

    def enable_export(self, enabled):
        state = tk.NORMAL if enabled else tk.DISABLED
        self.export_btn.config(state=state)

    def enable_remove(self, enabled):
        state = tk.NORMAL if enabled else tk.DISABLED
        self.remove_btn.config(state=state)

    def add_point(self):
        selected = self.get_selected_params()
        if not selected:
            self.show_error(self.tr("select_params_first"))
            return
        num_samples = self.samples_var.get()
        mode = self.mode.get()
        calib_sensor = self.calib_sensor_combo.get()
        ref_sensor = self.ref_sensor_combo.get() if mode == 'ref' else None
        if mode == 'ref' and not ref_sensor:
            self.show_error(self.tr("select_ref_sensor"))
            return
        self.add_btn.config(state=tk.DISABLED)
        self.start_progress()
        self.presenter.on_add_point(mode, calib_sensor, ref_sensor, selected, num_samples)

    def on_add_point_finished(self):
        self.stop_progress()
        self.enable_export(True)
        self.add_btn.config(state=tk.NORMAL)

    def calc_regression(self):
        selected = self.get_selected_params()
        if not selected:
            self.show_error(self.tr("select_param_first"))
            return
        param = selected[0]
        model = self.model_combo.get()
        self.presenter.on_calculate_regression(param, model)

    def save_calib(self):
        self.presenter.on_save_calibration()

    def export_csv(self):
        self.presenter.on_export_csv()

    def remove_point(self):
        selected = self.points_tree.selection()
        if selected:
            tags = self.points_tree.item(selected[0], "tags")
            if len(tags) >= 3:
                point_idx = int(tags[2])
                self.presenter.on_remove_point(point_idx)

    def on_graph_type_changed(self):
        self.presenter.on_graph_type_changed(self.graph_type.get())

    def on_graph_param_selected(self, event):
        idx = self.graph_param_combo.current()
        if idx >= 0:
            param_key = self.param_keys[idx]
            self.presenter.on_graph_param_selected(param_key)

    def refresh_graph(self):
        self.on_graph_param_selected(None)

    def on_points_tree_click(self, event):
        item = self.points_tree.identify_row(event.y)
        if not item:
            return
        col = self.points_tree.identify_column(event.x)
        if col == "#9":  # график
            tags = self.points_tree.item(item, "tags")
            if len(tags) >= 3:
                param = tags[0]
                sensor_type = tags[1]
                point_idx = int(tags[2])
                self.presenter.on_show_raw_graph(point_idx, param, sensor_type)

    def show_error(self, msg):
        messagebox.showerror(self.tr("error"), msg)

    def show_warning(self, msg):
        messagebox.showwarning(self.tr("warning"), msg)

    def show_message(self, msg):
        messagebox.showinfo(self.tr("info"), msg)

    def on_sensors_changed(self):
        self.presenter.on_sensors_changed()

    def on_show(self):
        self.presenter.on_show()

    def on_hide(self):
        self.presenter.on_hide()
