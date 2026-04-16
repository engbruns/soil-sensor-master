# modules/profiles/editor.py
# Расположение: modules/profiles/editor.py
# Описание: Диалог для создания и редактирования профиля датчика.

import tkinter as tk
from tkinter import ttk, messagebox
from core.constants import STANDARD_PARAMS

class ProfileEditor(tk.Toplevel):
    def __init__(self, parent, core_api, profile_data=None, callback=None):
        super().__init__(parent)
        self.parent = parent
        self.core_api = core_api
        self.tr = core_api.tr
        self.callback = callback
        self.profile_data = profile_data if profile_data else self._default_profile()
        self.modified = False

        self.title(self.tr("profile_editor"))
        self.geometry("800x600")
        self.transient(parent)
        self.grab_set()

        self.create_widgets()
        self.load_data()

    def _default_profile(self):
        return {
            "name": "",
            "description": "",
            "device": {
                "default_address": 1,
                "default_baudrate": 4800,
                "available_baudrates": [2400, 4800, 9600]
            },
            "parameters": [],
            "system_registers": [],  # пока не редактируем
            "calibration": None
        }

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Верхняя часть: имя, описание, адрес, скорость
        top_frame = ttk.LabelFrame(main_frame, text=self.tr("profile_info"), padding=5)
        top_frame.pack(fill=tk.X, pady=5)

        ttk.Label(top_frame, text=self.tr("profile_name")).grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.name_var = tk.StringVar()
        ttk.Entry(top_frame, textvariable=self.name_var, width=30).grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(top_frame, text=self.tr("description")).grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.desc_var = tk.StringVar()
        ttk.Entry(top_frame, textvariable=self.desc_var, width=50).grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(top_frame, text=self.tr("default_address")).grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.address_var = tk.IntVar(value=1)
        ttk.Spinbox(top_frame, from_=1, to=247, textvariable=self.address_var, width=8).grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)

        ttk.Label(top_frame, text=self.tr("default_baudrate")).grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        self.baud_var = tk.IntVar(value=4800)
        ttk.Combobox(top_frame, textvariable=self.baud_var, values=[2400, 4800, 9600], width=8).grid(row=3, column=1, sticky=tk.W, padx=5, pady=2)

        # Таблица параметров
        params_frame = ttk.LabelFrame(main_frame, text=self.tr("parameters"), padding=5)
        params_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        columns = ("key", "name", "address", "factor", "offset", "model", "coeffs", "edit")
        self.tree = ttk.Treeview(params_frame, columns=columns, show="headings", height=10)
        self.tree.heading("key", text=self.tr("key"))
        self.tree.heading("name", text=self.tr("name"))
        self.tree.heading("address", text=self.tr("address"))
        self.tree.heading("factor", text=self.tr("factor"))
        self.tree.heading("offset", text=self.tr("offset"))
        self.tree.heading("model", text=self.tr("model"))
        self.tree.heading("coeffs", text=self.tr("coeffs"))
        self.tree.heading("edit", text=self.tr("edit"))

        self.tree.column("key", width=80)
        self.tree.column("name", width=120)
        self.tree.column("address", width=60)
        self.tree.column("factor", width=60)
        self.tree.column("offset", width=60)
        self.tree.column("model", width=80)
        self.tree.column("coeffs", width=150)
        self.tree.column("edit", width=60)

        vsb = ttk.Scrollbar(params_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(params_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        params_frame.grid_rowconfigure(0, weight=1)
        params_frame.grid_columnconfigure(0, weight=1)

        self.tree.bind("<Button-1>", self.on_tree_click)

        # Кнопки
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text=self.tr("add_parameter"), command=self.add_parameter).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text=self.tr("save"), command=self.save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text=self.tr("cancel"), command=self.destroy).pack(side=tk.RIGHT, padx=5)

    def load_data(self):
        self.name_var.set(self.profile_data.get("name", ""))
        self.desc_var.set(self.profile_data.get("description", ""))
        dev = self.profile_data.get("device", {})
        self.address_var.set(dev.get("default_address", 1))
        self.baud_var.set(dev.get("default_baudrate", 4800))

        for p in self.profile_data.get("parameters", []):
            self._add_row(p)

    def _add_row(self, param):
        key = param.get("key", "")
        name = param.get("name_key", key)
        address = param.get("address", 0)
        factor = param.get("factor", 1)
        offset = param.get("offset", 0)
        calibration = self.profile_data.get("calibration", {}).get(key, {})
        model = calibration.get("model", "")
        coeffs = calibration.get("coefficients", [])
        coeffs_str = ", ".join(f"{c:.4f}" for c in coeffs) if coeffs else ""

        self.tree.insert("", tk.END, values=(
            key, name, address, factor, offset, model, coeffs_str, self.tr("edit")
        ), tags=(key,))

    def add_parameter(self):
        # Диалог добавления/редактирования параметра
        EditParamDialog(self, self.core_api, self.tr, self._on_param_edited)

    def _on_param_edited(self, param_data):
        # param_data: dict с ключами key, name, address, factor, offset, model, coeffs
        # Найти строку с таким key, если есть – обновить, иначе добавить
        key = param_data["key"]
        for item in self.tree.get_children():
            if self.tree.item(item, "tags")[0] == key:
                self.tree.item(item, values=(
                    key, param_data["name"], param_data["address"],
                    param_data["factor"], param_data["offset"],
                    param_data["model"], param_data["coeffs_str"],
                    self.tr("edit")
                ))
                self.modified = True
                return
        # Нет — добавляем
        self.tree.insert("", tk.END, values=(
            key, param_data["name"], param_data["address"],
            param_data["factor"], param_data["offset"],
            param_data["model"], param_data["coeffs_str"],
            self.tr("edit")
        ), tags=(key,))
        self.modified = True

    def on_tree_click(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        col = self.tree.identify_column(event.x)
        if col == "#8":  # колонка "edit"
            # Получаем данные строки
            values = self.tree.item(item, "values")
            key = values[0]
            # Ищем существующий параметр в self.profile_data (или создаём временный)
            param = None
            for p in self.profile_data.get("parameters", []):
                if p["key"] == key:
                    param = p
                    break
            if not param:
                param = {"key": key}
            calibration = self.profile_data.get("calibration", {}).get(key, {})
            EditParamDialog(self, self.core_api, self.tr, self._on_param_edited, param, calibration)

    def save(self):
        # Собираем данные из интерфейса
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror(self.tr("error"), self.tr("profile_name_required"))
            return

        # Собираем параметры из дерева
        parameters = []
        calibration = {}
        for item in self.tree.get_children():
            values = self.tree.item(item, "values")
            key = values[0]
            name_key = values[1]
            address = int(values[2])
            factor = float(values[3])
            offset = float(values[4])
            model = values[5] if values[5] else None
            coeffs_str = values[6]
            coeffs = [float(x.strip()) for x in coeffs_str.split(",")] if coeffs_str else None

            param = {
                "key": key,
                "name_key": name_key,
                "address": address,
                "function_code": 3,
                "factor": factor,
                "offset": offset
            }
            parameters.append(param)
            if model and coeffs:
                calibration[key] = {
                    "model": model,
                    "coefficients": coeffs,
                    "r2": None  # можно потом заполнить
                }

        profile_data = {
            "name": name,
            "description": self.desc_var.get(),
            "device": {
                "default_address": self.address_var.get(),
                "default_baudrate": self.baud_var.get(),
                "available_baudrates": [2400, 4800, 9600]
            },
            "parameters": parameters,
            "system_registers": self.profile_data.get("system_registers", []),
            "calibration": calibration
        }

        # Сохраняем через profile_manager
        fname = name.replace(" ", "_").lower() + ".json"
        if self.profile_manager.save_profile(fname, profile_data):
            messagebox.showinfo(self.tr("success"), self.tr("profile_saved"))
            if self.callback:
                self.callback()
            self.destroy()
        else:
            messagebox.showerror(self.tr("error"), self.tr("save_failed"))


class EditParamDialog(tk.Toplevel):
    def __init__(self, parent, core_api, tr, callback, param=None, calibration=None):
        super().__init__(parent)
        self.parent = parent
        self.core_api = core_api
        self.tr = tr
        self.callback = callback
        self.param = param if param else {}
        self.calibration = calibration if calibration else {}

        self.title(self.tr("edit_parameter"))
        self.geometry("400x400")
        self.transient(parent)
        self.grab_set()

        self.create_widgets()
        self.load_data()

    def create_widgets(self):
        main = ttk.Frame(self, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main, text=self.tr("parameter_key")).grid(row=0, column=0, sticky=tk.W, pady=2)
        self.key_var = tk.StringVar()
        key_combo = ttk.Combobox(main, textvariable=self.key_var, values=list(STANDARD_PARAMS.keys()), state="readonly")
        key_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        key_combo.bind("<<ComboboxSelected>>", self.on_key_selected)

        ttk.Label(main, text=self.tr("display_name")).grid(row=1, column=0, sticky=tk.W, pady=2)
        self.name_var = tk.StringVar()
        ttk.Entry(main, textvariable=self.name_var, width=30).grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(main, text=self.tr("address")).grid(row=2, column=0, sticky=tk.W, pady=2)
        self.address_var = tk.IntVar()
        ttk.Spinbox(main, from_=0, to=65535, textvariable=self.address_var, width=8).grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)

        ttk.Label(main, text=self.tr("factor")).grid(row=3, column=0, sticky=tk.W, pady=2)
        self.factor_var = tk.DoubleVar(value=1.0)
        ttk.Entry(main, textvariable=self.factor_var, width=10).grid(row=3, column=1, sticky=tk.W, padx=5, pady=2)

        ttk.Label(main, text=self.tr("offset")).grid(row=4, column=0, sticky=tk.W, pady=2)
        self.offset_var = tk.DoubleVar(value=0.0)
        ttk.Entry(main, textvariable=self.offset_var, width=10).grid(row=4, column=1, sticky=tk.W, padx=5, pady=2)

        # Калибровочная модель
        calib_frame = ttk.LabelFrame(main, text=self.tr("calibration_model"), padding=5)
        calib_frame.grid(row=5, column=0, columnspan=2, pady=10, sticky=tk.EW)

        ttk.Label(calib_frame, text=self.tr("model")).grid(row=0, column=0, sticky=tk.W)
        self.model_var = tk.StringVar(value="")
        model_combo = ttk.Combobox(calib_frame, textvariable=self.model_var, values=["linear", "poly2", "poly3"], state="readonly")
        model_combo.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(calib_frame, text=self.tr("coefficients")).grid(row=1, column=0, sticky=tk.W)
        self.coeffs_var = tk.StringVar()
        ttk.Entry(calib_frame, textvariable=self.coeffs_var, width=30).grid(row=1, column=1, padx=5, pady=2)
        ttk.Label(calib_frame, text=self.tr("coeffs_hint")).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=2)

        btn_frame = ttk.Frame(main)
        btn_frame.grid(row=6, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text=self.tr("ok"), command=self.save).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text=self.tr("cancel"), command=self.destroy).pack(side=tk.LEFT, padx=5)

    def load_data(self):
        self.key_var.set(self.param.get("key", ""))
        self.name_var.set(self.param.get("name_key", self.param.get("key", "")))
        self.address_var.set(self.param.get("address", 0))
        self.factor_var.set(self.param.get("factor", 1))
        self.offset_var.set(self.param.get("offset", 0))

        model = self.calibration.get("model", "")
        coeffs = self.calibration.get("coefficients", [])
        self.model_var.set(model)
        self.coeffs_var.set(", ".join(f"{c:.4f}" for c in coeffs))

    def on_key_selected(self, event):
        key = self.key_var.get()
        if key in STANDARD_PARAMS:
            self.factor_var.set(STANDARD_PARAMS[key]["factor"])
            self.offset_var.set(STANDARD_PARAMS[key]["offset"])
            self.name_var.set(self.tr(key + "_name") if hasattr(self, 'tr') else key)

    def save(self):
        key = self.key_var.get()
        if not key:
            messagebox.showerror(self.tr("error"), self.tr("select_parameter"))
            return
        try:
            address = self.address_var.get()
            factor = self.factor_var.get()
            offset = self.offset_var.get()
        except:
            messagebox.showerror(self.tr("error"), self.tr("invalid_number"))
            return
        model = self.model_var.get()
        coeffs_str = self.coeffs_var.get().strip()
        coeffs = [float(x.strip()) for x in coeffs_str.split(",")] if coeffs_str else []
        if model and not coeffs:
            messagebox.showerror(self.tr("error"), self.tr("coeffs_required"))
            return
        coeffs_display = ", ".join(f"{c:.4f}" for c in coeffs) if coeffs else ""

        param_data = {
            "key": key,
            "name": self.name_var.get(),
            "address": address,
            "factor": factor,
            "offset": offset,
            "model": model,
            "coeffs": coeffs,
            "coeffs_str": coeffs_display
        }
        self.callback(param_data)
        self.destroy()