# modules/calibration/panel.py
import tkinter as tk
from tkinter import ttk, messagebox
import serial.tools.list_ports

class CalibrationPanel(ttk.Frame):
    def __init__(self, parent, presenter, tr):
        super().__init__(parent)
        self.presenter = presenter
        self.tr = tr
        self.mode = tk.StringVar(value="lab")
        self.param_vars = {}
        self.param_keys = []
        self.create_widgets()

    def create_widgets(self):
        # Основной контейнер с прокруткой
        main_canvas = tk.Canvas(self, highlightthickness=0)
        main_scrollbar = ttk.Scrollbar(self, orient="vertical", command=main_canvas.yview)
        self.scrollable_frame = ttk.Frame(main_canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        )
        main_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        main_canvas.configure(yscrollcommand=main_scrollbar.set)

        main_canvas.pack(side="left", fill="both", expand=True)
        main_scrollbar.pack(side="right", fill="y")

        # Настройка сетки
        self.scrollable_frame.columnconfigure(0, weight=1)
        self.scrollable_frame.columnconfigure(1, weight=1)

        # Режим
        mode_frame = ttk.LabelFrame(self.scrollable_frame, text=self.tr("mode"), padding=5)
        mode_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        ttk.Radiobutton(mode_frame, text=self.tr("lab_mode"), variable=self.mode, value="lab",
                        command=self.on_mode_change).pack(anchor=tk.W, padx=5)
        ttk.Radiobutton(mode_frame, text=self.tr("ref_mode"), variable=self.mode, value="ref",
                        command=self.on_mode_change).pack(anchor=tk.W, padx=5)

        # Список параметров
        self.params_frame = ttk.LabelFrame(self.scrollable_frame, text=self.tr("select_params"), padding=5)
        self.params_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.params_frame.columnconfigure(0, weight=1)

        # Количество считываний и кнопка
        left_row2 = ttk.Frame(self.scrollable_frame)
        left_row2.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        ttk.Label(left_row2, text=self.tr("num_samples")).pack(side=tk.LEFT, padx=5)
        self.samples_var = tk.IntVar(value=10)
        ttk.Spinbox(left_row2, from_=1, to=100, textvariable=self.samples_var, width=8).pack(side=tk.LEFT, padx=5)
        self.add_btn = ttk.Button(left_row2, text=self.tr("add_point"), command=self.add_point)
        self.add_btn.pack(side=tk.LEFT, padx=10)

        # Блок эталонного датчика
        self.ref_block = ttk.LabelFrame(self.scrollable_frame, text=self.tr("ref_sensor"), padding=5)
        self.ref_block.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        self.ref_block.columnconfigure(1, weight=1)

        ttk.Label(self.ref_block, text=self.tr("ref_profile")).grid(row=0, column=0, padx=2, sticky="w")
        self.ref_profile_combo = ttk.Combobox(self.ref_block, state="readonly", width=20)
        self.ref_profile_combo.grid(row=0, column=1, padx=2, sticky="ew")

        ttk.Label(self.ref_block, text=self.tr("ref_port")).grid(row=1, column=0, padx=2, sticky="w")
        self.ref_port_combo = ttk.Combobox(self.ref_block, values=[], state="readonly", width=10)
        self.ref_port_combo.grid(row=1, column=1, padx=2, sticky="w")

        btn_ref_frame = ttk.Frame(self.ref_block)
        btn_ref_frame.grid(row=2, column=0, columnspan=2, pady=5)
        self.ref_connect_btn = ttk.Button(btn_ref_frame, text=self.tr("connect_ref"), command=self.connect_ref)
        self.ref_connect_btn.pack(side=tk.LEFT, padx=2)
        self.ref_status = ttk.Label(btn_ref_frame, text=self.tr("disconnected"), foreground="red")
        self.ref_status.pack(side=tk.LEFT, padx=10)
        self.ref_disconnect_btn = ttk.Button(btn_ref_frame, text="✕", width=2, command=self.disconnect_ref)
        self.ref_disconnect_btn.pack(side=tk.LEFT, padx=2)

        self.ref_block.grid_remove()

        # Таблица точек
        points_frame = ttk.LabelFrame(self.scrollable_frame, text=self.tr("points"), padding=5)
        points_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        self.scrollable_frame.rowconfigure(2, weight=1)
        points_frame.columnconfigure(0, weight=1)
        points_frame.rowconfigure(0, weight=1)

        # Колонки: №, Параметр, Тип, Медиана, Среднее, Макс, Мин, График
        columns = ("№", "Параметр", "Тип", "Медиана", "Среднее", "Макс", "Мин", "График")
        self.tree = ttk.Treeview(points_frame, columns=columns, show="headings", height=10)
        vsb = ttk.Scrollbar(points_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=80)
        self.tree.column("№", width=40)
        self.tree.column("Параметр", width=120)
        self.tree.column("Тип", width=60)
        self.tree.column("График", width=60)

        self.tree.bind("<Button-1>", self.on_tree_click)

        # Кнопки под таблицей
        btn_frame = ttk.Frame(self.scrollable_frame)
        btn_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=5, pady=5)

        self.save_btn = ttk.Button(btn_frame, text=self.tr("save_calib"), command=self.save_calib, state=tk.DISABLED)
        self.save_btn.pack(side=tk.LEFT, padx=5)

        self.export_btn = ttk.Button(btn_frame, text=self.tr("export_csv"), command=self.export_csv, state=tk.DISABLED)
        self.export_btn.pack(side=tk.LEFT, padx=5)

        self.remove_btn = ttk.Button(btn_frame, text=self.tr("remove_point"), command=self.remove_point)
        self.remove_btn.pack(side=tk.LEFT, padx=5)

        # Панель управления графиком
        graph_control_frame = ttk.Frame(self.scrollable_frame)
        graph_control_frame.grid(row=4, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        graph_control_frame.columnconfigure(1, weight=1)

        ttk.Label(graph_control_frame, text=self.tr("graph_param")).grid(row=0, column=0, padx=5, sticky="w")
        self.graph_param_combo = ttk.Combobox(graph_control_frame, state="readonly", width=20)
        self.graph_param_combo.grid(row=0, column=1, padx=5, sticky="ew")
        self.graph_param_combo.bind("<<ComboboxSelected>>", self.on_graph_param_selected)

        self.calc_reg_btn = ttk.Button(graph_control_frame, text=self.tr("calc_regression"), command=self.calc_regression)
        self.calc_reg_btn.grid(row=0, column=2, padx=5)

        ttk.Label(graph_control_frame, text=self.tr("model")).grid(row=1, column=0, padx=5, sticky="w")
        self.model_combo = ttk.Combobox(graph_control_frame, values=["linear", "poly2", "poly3"], state="readonly", width=10)
        self.model_combo.set("linear")
        self.model_combo.grid(row=1, column=1, padx=5, sticky="w")

        # График
        self.graph_frame = ttk.LabelFrame(self.scrollable_frame, text=self.tr("graph"), padding=5)
        self.graph_frame.grid(row=5, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        self.scrollable_frame.rowconfigure(5, weight=1)
        self.graph_frame.columnconfigure(0, weight=1)
        self.graph_frame.rowconfigure(0, weight=1)

        self.refresh_ports()
        self.refresh_profiles()

    def refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.ref_port_combo['values'] = ports
        if ports and not self.ref_port_combo.get():
            self.ref_port_combo.set(ports[0])

    def refresh_profiles(self):
        profiles = self.presenter.core_api.profile_manager.list_profiles()
        self.ref_profile_combo['values'] = profiles
        if profiles and not self.ref_profile_combo.get():
            self.ref_profile_combo.set(profiles[0])

    def update_param_list(self, params):
        for widget in self.params_frame.winfo_children():
            widget.destroy()
        self.param_vars.clear()
        self.param_keys = []
        for p in params:
            var = tk.BooleanVar()
            cb = ttk.Checkbutton(self.params_frame, text=self.tr(p.get('name_key', p['key'])), variable=var)
            cb.pack(anchor=tk.W, padx=5)
            self.param_vars[p['key']] = var
            self.param_keys.append(p['key'])
        self.graph_param_combo['values'] = [self.tr(k) for k in self.param_keys]

    def on_mode_change(self):
        mode = self.mode.get()
        if mode == 'lab':
            self.ref_block.grid_remove()
        else:
            self.ref_block.grid()

    def connect_ref(self):
        port = self.ref_port_combo.get()
        profile = self.ref_profile_combo.get()
        if not port or not profile:
            self.show_error(self.tr("fill_ref_fields"))
            return
        self.presenter.on_connect_ref(port, profile)

    def disconnect_ref(self):
        self.presenter.on_disconnect_ref()

    def update_ref_status(self, connected):
        if connected:
            self.ref_status.config(text=self.tr("connected"), foreground="green")
            self.ref_connect_btn.config(state=tk.DISABLED)
        else:
            self.ref_status.config(text=self.tr("disconnected"), foreground="red")
            self.ref_connect_btn.config(state=tk.NORMAL)

    def add_point(self):
        mode = self.mode.get()
        selected = [key for key, var in self.param_vars.items() if var.get()]
        if not selected:
            self.show_error(self.tr("select_params_first"))
            return
        num_samples = self.samples_var.get()
        self.presenter.on_add_point(mode, num_samples, selected)

    def remove_point(self):
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0], "values")
        if values:
            point_num = int(values[0]) - 1
            self.presenter.on_remove_point(point_num)

    def calc_regression(self):
        idx = self.graph_param_combo.current()
        if idx < 0 or idx >= len(self.param_keys):
            self.show_error(self.tr("select_param_first"))
            return
        param = self.param_keys[idx]
        model = self.model_combo.get()
        self.presenter.on_calculate_regression(param, model)

    def save_calib(self):
        self.presenter.on_save_calibration()

    def export_csv(self):
        self.presenter.on_export_csv()

    def on_tree_click(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        col = self.tree.identify_column(event.x)
        values = self.tree.item(item, "values")
        if not values:
            return
        col_index = int(col[1:]) - 1
        if col_index >= len(values):
            return
        # Проверяем, что клик по колонке "График" (последняя)
        if col_index == 7:
            point_num = int(values[0]) - 1
            tags = self.tree.item(item, "tags")
            if len(tags) >= 2:
                param = tags[0]
                sensor_type = tags[1]  # 'calib' или 'ref'
                self.presenter.on_show_raw_graph(point_num, param, sensor_type)

    def on_graph_param_selected(self, event):
        idx = self.graph_param_combo.current()
        if idx >= 0 and idx < len(self.param_keys):
            param = self.param_keys[idx]
            self.presenter.on_show_graph_for_param(param)

    def update_points_table(self, points, selected_params, mode, param_info, ref_param_info=None):
        for row in self.tree.get_children():
            self.tree.delete(row)

        if not points:
            return

        for i, point in enumerate(points):
            point_num = i + 1
            for param in selected_params:
                # Строка калибруемого датчика
                raw_stat = point['raw_stats'].get(param)
                if raw_stat:
                    factor = param_info.get(param, {}).get('factor', 1)
                    offset = param_info.get(param, {}).get('offset', 0)
                    median = raw_stat['median'] * factor + offset if raw_stat['median'] is not None else None
                    avg = raw_stat['avg'] * factor + offset if raw_stat['avg'] is not None else None
                    max_val = raw_stat['max'] * factor + offset if raw_stat['max'] is not None else None
                    min_val = raw_stat['min'] * factor + offset if raw_stat['min'] is not None else None

                    row = [
                        point_num,
                        self.tr(param),
                        "Кал",
                        f"{median:.2f}" if median is not None else '---',
                        f"{avg:.2f}" if avg is not None else '---',
                        f"{max_val:.2f}" if max_val is not None else '---',
                        f"{min_val:.2f}" if min_val is not None else '---',
                        self.tr("graph")
                    ]
                    self.tree.insert('', tk.END, values=row, tags=(param, 'calib'))

                # Строка эталонного датчика (или введённые эталоны)
                if mode == 'lab':
                    ref_val = point.get('ref_values', {}).get(param)
                    if ref_val is not None:
                        row = [
                            point_num,
                            self.tr(param),
                            "Эт",
                            f"{ref_val:.2f}",
                            f"{ref_val:.2f}",
                            f"{ref_val:.2f}",
                            f"{ref_val:.2f}",
                            self.tr("graph")
                        ]
                        self.tree.insert('', tk.END, values=row, tags=(param, 'ref'))
                else:
                    ref_stat = point.get('ref_stats', {}).get(param)
                    if ref_stat:
                        ref_factor = ref_param_info.get(param, {}).get('factor', 1)
                        ref_offset = ref_param_info.get(param, {}).get('offset', 0)
                        median_r = ref_stat['median'] * ref_factor + ref_offset if ref_stat['median'] is not None else None
                        avg_r = ref_stat['avg'] * ref_factor + ref_offset if ref_stat['avg'] is not None else None
                        max_r = ref_stat['max'] * ref_factor + ref_offset if ref_stat['max'] is not None else None
                        min_r = ref_stat['min'] * ref_factor + ref_offset if ref_stat['min'] is not None else None
                        row = [
                            point_num,
                            self.tr(param),
                            "Эт",
                            f"{median_r:.2f}" if median_r is not None else '---',
                            f"{avg_r:.2f}" if avg_r is not None else '---',
                            f"{max_r:.2f}" if max_r is not None else '---',
                            f"{min_r:.2f}" if min_r is not None else '---',
                            self.tr("graph")
                        ]
                        self.tree.insert('', tk.END, values=row, tags=(param, 'ref'))

    def enable_save_export(self, enabled):
        state = tk.NORMAL if enabled else tk.DISABLED
        self.save_btn.config(state=state)
        self.export_btn.config(state=state)

    def show_error(self, msg):
        messagebox.showerror(self.tr("error"), msg)

    def show_message(self, msg):
        messagebox.showinfo(self.tr("info"), msg)

    def show_warning(self, msg):
        messagebox.showwarning(self.tr("warning"), msg)