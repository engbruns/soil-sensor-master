# modules/scanner/panel.py
# Расположение: modules/scanner/panel.py
# Описание: Панель сканера – выбор датчика, настройка параметров сканирования,
#           результаты в таблице. Добавлена вертикальная прокрутка.

import tkinter as tk
from tkinter import ttk, messagebox

class ScannerPanel(ttk.Frame):
    def __init__(self, parent, presenter, tr):
        super().__init__(parent)
        self.presenter = presenter
        self.tr = tr
        self.collecting = False
        self.create_widgets()

    def create_widgets(self):
        # Создаём внешний canvas с прокруткой
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        # При изменении размеров scrollable_frame обновляем область прокрутки
        self.scrollable_frame.bind("<Configure>", self._on_frame_configure)
        # При изменении размера canvas обновляем ширину окна
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Все виджеты размещаем внутри scrollable_frame
        self._create_widgets_inside()

    def _on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _create_widgets_inside(self):
        """Все внутренние элементы создаются здесь."""
        # Панель выбора датчика
        sensor_frame = ttk.LabelFrame(self.scrollable_frame, text=self.tr("select_sensor"), padding=5)
        sensor_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(sensor_frame, text=self.tr("sensor")).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.sensor_combo = ttk.Combobox(sensor_frame, state="readonly", width=20)
        self.sensor_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        self.sensor_combo.bind("<<ComboboxSelected>>", self.on_sensor_selected)

        # Панель настроек сканирования
        scan_frame = ttk.LabelFrame(self.scrollable_frame, text=self.tr("scan_settings"), padding=5)
        scan_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(scan_frame, text=self.tr("address_mode")).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.address_mode = tk.StringVar(value="range")
        ttk.Radiobutton(scan_frame, text=self.tr("range"), variable=self.address_mode, value="range",
                        command=self.toggle_mode).grid(row=0, column=1, padx=5, pady=5)
        ttk.Radiobutton(scan_frame, text=self.tr("list"), variable=self.address_mode, value="list",
                        command=self.toggle_mode).grid(row=0, column=2, padx=5, pady=5)

        self.range_frame = ttk.Frame(scan_frame)
        self.range_frame.grid(row=1, column=0, columnspan=3, pady=5)
        ttk.Label(self.range_frame, text=self.tr("start_addr")).pack(side=tk.LEFT)
        self.start_addr = tk.StringVar(value="0x00")
        ttk.Entry(self.range_frame, textvariable=self.start_addr, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Label(self.range_frame, text=self.tr("end_addr")).pack(side=tk.LEFT)
        self.end_addr = tk.StringVar(value="0x30")
        ttk.Entry(self.range_frame, textvariable=self.end_addr, width=8).pack(side=tk.LEFT, padx=2)

        self.list_frame = ttk.Frame(scan_frame)
        self.list_frame.grid(row=1, column=0, columnspan=3, pady=5)
        ttk.Label(self.list_frame, text=self.tr("address_list")).pack(side=tk.LEFT)
        self.address_list = tk.StringVar(value="0x00-0x08, 0x22-0x24, 0x50-0x53, 0x4E8-0x4FE, 0x7D0-0x7D1")
        ttk.Entry(self.list_frame, textvariable=self.address_list, width=40).pack(side=tk.LEFT, padx=2)

        self.toggle_mode()

        ttk.Label(scan_frame, text=self.tr("num_cycles")).grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.cycles_var = tk.IntVar(value=10)
        ttk.Spinbox(scan_frame, from_=1, to=100, textvariable=self.cycles_var, width=8).grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)

        self.collect_btn = ttk.Button(scan_frame, text=self.tr("start_scan"), command=self.toggle_collect)
        self.collect_btn.grid(row=2, column=2, padx=10, pady=5)

        self.progress_var = tk.IntVar(value=0)
        self.progress = ttk.Progressbar(scan_frame, orient=tk.HORIZONTAL, length=200, mode='determinate', variable=self.progress_var)
        self.progress.grid(row=3, column=0, columnspan=3, padx=5, pady=5, sticky=tk.EW)

        # Панель ориентиров
        ref_frame = ttk.LabelFrame(self.scrollable_frame, text=self.tr("references"), padding=5)
        ref_frame.pack(fill=tk.X, padx=10, pady=5)

        self.ref_tree = ttk.Treeview(ref_frame, columns=("param", "value", "tolerance"), show="headings", height=3)
        self.ref_tree.heading("param", text=self.tr("param"))
        self.ref_tree.heading("value", text=self.tr("value"))
        self.ref_tree.heading("tolerance", text=self.tr("tolerance"))
        self.ref_tree.pack(fill=tk.X, padx=5, pady=5)

        ref_controls = ttk.Frame(ref_frame)
        ref_controls.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(ref_controls, text=self.tr("param")).pack(side=tk.LEFT)
        self.ref_param = ttk.Combobox(ref_controls, values=["temperature", "humidity", "ph", "ec", "nitrogen", "phosphorus", "potassium", "salinity", "tds"], width=12)
        self.ref_param.pack(side=tk.LEFT, padx=2)
        ttk.Label(ref_controls, text=self.tr("value")).pack(side=tk.LEFT)
        self.ref_value = tk.StringVar(value="25.0")
        ttk.Entry(ref_controls, textvariable=self.ref_value, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Label(ref_controls, text=self.tr("tolerance")).pack(side=tk.LEFT)
        self.ref_tol = tk.StringVar(value="1.0")
        ttk.Entry(ref_controls, textvariable=self.ref_tol, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Button(ref_controls, text=self.tr("add"), command=self.add_reference).pack(side=tk.LEFT, padx=2)
        ttk.Button(ref_controls, text=self.tr("remove"), command=self.remove_reference).pack(side=tk.LEFT, padx=2)

        # Кнопки управления
        btn_frame = ttk.Frame(self.scrollable_frame)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

        self.search_addr_btn = ttk.Button(btn_frame, text=self.tr("search_address"), command=self.presenter.open_address_search)
        self.search_addr_btn.pack(side=tk.LEFT, padx=5)

        self.analyze_btn = ttk.Button(btn_frame, text=self.tr("analyze"), command=self.presenter.on_analyze_clicked, state=tk.DISABLED)
        self.analyze_btn.pack(side=tk.LEFT, padx=5)

        self.save_btn = ttk.Button(btn_frame, text=self.tr("save_profile"), command=self.presenter.on_save_profile, state=tk.DISABLED)
        self.save_btn.pack(side=tk.LEFT, padx=5)

        # Таблица результатов (занимает оставшееся место)
        result_frame = ttk.LabelFrame(self.scrollable_frame, text=self.tr("results"), padding=5)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ("addr_hex", "addr_dec", "value_dec", "value_hex", "graph", "assign", "prob")
        self.tree = ttk.Treeview(result_frame, columns=columns, show="headings", height=8)
        self.tree.heading("addr_hex", text=self.tr("addr_hex"))
        self.tree.heading("addr_dec", text=self.tr("addr_dec"))
        self.tree.heading("value_dec", text=self.tr("value_dec"))
        self.tree.heading("value_hex", text=self.tr("value_hex"))
        self.tree.heading("graph", text=self.tr("graph"))
        self.tree.heading("assign", text=self.tr("assign"))
        self.tree.heading("prob", text=self.tr("prob"))

        self.tree.column("addr_hex", width=80)
        self.tree.column("addr_dec", width=80)
        self.tree.column("value_dec", width=100)
        self.tree.column("value_hex", width=100)
        self.tree.column("graph", width=60)
        self.tree.column("assign", width=150)
        self.tree.column("prob", width=200)

        vsb = ttk.Scrollbar(result_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(result_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        result_frame.grid_rowconfigure(0, weight=1)
        result_frame.grid_columnconfigure(0, weight=1)

        self.tree.bind("<Button-1>", self.on_tree_click)

        # Заполняем список датчиков
        self.update_sensor_list()

    # Все остальные методы остаются без изменений
    def update_sensor_list(self):
        sensors = self.presenter.core_api.list_sensors()
        current = self.sensor_combo.get()
        self.sensor_combo['values'] = sensors
        if current in sensors:
            self.sensor_combo.set(current)
        elif sensors:
            self.sensor_combo.set(sensors[0])
        else:
            self.sensor_combo.set("")

    def on_sensor_selected(self, event):
        name = self.sensor_combo.get()
        if name:
            self.presenter.on_sensor_selected(name)

    def toggle_mode(self):
        if self.address_mode.get() == "range":
            self.list_frame.grid_remove()
            self.range_frame.grid()
        else:
            self.range_frame.grid_remove()
            self.list_frame.grid()

    def toggle_collect(self):
        if self.collecting:
            self.presenter.on_stop_collect()
        else:
            try:
                if self.address_mode.get() == "range":
                    start = int(self.start_addr.get(), 16)
                    end = int(self.end_addr.get(), 16)
                    addresses = list(range(start, end + 1))
                else:
                    addresses = self.parse_address_string(self.address_list.get())
            except Exception as e:
                messagebox.showerror(self.tr("error"), str(e))
                return
            cycles = self.cycles_var.get()
            self.presenter.on_start_collect(addresses, cycles)

    def parse_address_string(self, s):
        result = []
        parts = s.split(',')
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if '-' in part:
                low_high = part.split('-')
                if len(low_high) != 2:
                    raise ValueError(f"Invalid range: {part}")
                low = self._parse_addr(low_high[0].strip())
                high = self._parse_addr(low_high[1].strip())
                if low > high:
                    raise ValueError(f"Start > end: {part}")
                result.extend(range(low, high + 1))
            else:
                addr = self._parse_addr(part)
                result.append(addr)
        return sorted(set(result))

    def _parse_addr(self, s):
        s = s.strip()
        if s.startswith(('0x', '0X')):
            return int(s, 16)
        try:
            return int(s, 10)
        except ValueError:
            try:
                return int(s, 16)
            except ValueError:
                raise ValueError(f"Invalid address format: {s}")

    def set_collecting(self, collecting):
        self.collecting = collecting
        self.collect_btn.config(text=self.tr("stop_scan") if collecting else self.tr("start_scan"))

    def update_progress(self, percent):
        self.progress_var.set(percent)

    def update_table(self, snapshot, manual_mapping):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for item in snapshot:
            addr_hex = item['addr_hex']
            addr_dec = item['addr_dec']
            val_dec = f"{item['value_dec']:.1f}" if item['value_dec'] is not None else "---"
            val_hex = item['value_hex']
            mapping = manual_mapping.get(addr_dec, {})
            assign = mapping.get('param', self.tr("click_to_assign"))
            self.tree.insert('', tk.END, values=(addr_hex, addr_dec, val_dec, val_hex, self.tr("graph"), assign, ""))

    def update_table_with_probs(self, snapshot, manual_mapping, probs, tr):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for item in snapshot:
            addr_hex = item['addr_hex']
            addr_dec = item['addr_dec']
            val_dec = f"{item['value_dec']:.1f}" if item['value_dec'] is not None else "---"
            val_hex = item['value_hex']
            mapping = manual_mapping.get(addr_dec, {})
            assign = mapping.get('param', self.tr("click_to_assign"))
            prob_text = ""
            if addr_dec in probs and probs[addr_dec]:
                sorted_params = sorted(probs[addr_dec].items(), key=lambda x: x[1], reverse=True)
                parts = [f"{tr(p)}: {int(prob*100)}%" for p, prob in sorted_params[:2]]
                prob_text = " ".join(parts)
            self.tree.insert('', tk.END, values=(addr_hex, addr_dec, val_dec, val_hex, self.tr("graph"), assign, prob_text))

    def enable_analyze(self, enabled):
        self.analyze_btn.config(state=tk.NORMAL if enabled else tk.DISABLED)

    def enable_save(self, enabled):
        self.save_btn.config(state=tk.NORMAL if enabled else tk.DISABLED)

    def show_message(self, msg):
        messagebox.showinfo(self.tr("info"), msg)

    def on_tree_click(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        col = self.tree.identify_column(event.x)
        values = self.tree.item(item, "values")
        if col == "#5":  # graph
            addr_hex = values[0]
            for s in self.presenter.current_snapshot:
                if s['addr_hex'] == addr_hex:
                    raw = s.get('raw_values', [])
                    median = s.get('value_dec')
                    self.presenter.on_graph_clicked(addr_hex, raw, median)
                    break
        elif col == "#6":  # assign
            addr_hex = values[0]
            current = self.presenter.manual_mapping.get(int(addr_hex, 16), {}).get("param")
            self.presenter.on_assign_clicked(addr_hex, current)

    def add_reference(self):
        param = self.ref_param.get()
        try:
            val = float(self.ref_value.get())
            tol = float(self.ref_tol.get())
        except ValueError:
            messagebox.showerror(self.tr("error"), self.tr("number_required"))
            return
        self.presenter.on_add_reference(param, val, tol)
        self.ref_tree.insert('', tk.END, values=(param, f"{val:.2f}", f"{tol:.2f}"))

    def remove_reference(self):
        sel = self.ref_tree.selection()
        if sel:
            idx = self.ref_tree.index(sel[0])
            self.ref_tree.delete(sel[0])
            self.presenter.on_remove_reference(idx)

    def on_sensors_changed(self):
        self.presenter.on_sensors_changed()

    def on_show(self):
        pass

    def on_hide(self):
        if self.collecting:
            self.presenter.on_stop_collect()
