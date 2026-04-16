# modules/profiles/edit_dialog.py
# Расположение: modules/profiles/edit_dialog.py
# Описание: Диалог для создания/редактирования профиля датчика.

import tkinter as tk
from tkinter import ttk, messagebox
import copy

class ProfileEditDialog(tk.Toplevel):
    def __init__(self, parent, profile_manager, profile_data=None, tr=None):
        super().__init__(parent)
        self.parent = parent
        self.profile_manager = profile_manager
        self.tr = tr or (lambda x: x)  # если нет перевода, возвращаем как есть
        self.profile_data = profile_data if profile_data else self._create_empty_profile()
        self.result = None  # будет содержать сохранённые данные после OK

        self.title(self.tr("edit_profile") if profile_data else self.tr("new_profile"))
        self.geometry("800x600")
        self.transient(parent)
        self.grab_set()

        self.create_widgets()
        self.load_data()

    def _create_empty_profile(self):
        return {
            "name": "",
            "description": "",
            "device": {
                "default_address": 1,
                "default_baudrate": 4800,
                "available_baudrates": [2400, 4800, 9600]
            },
            "parameters": [],
            "system_registers": [],
            "calibration": {}
        }

    def create_widgets(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Вкладка "Общие"
        general_frame = ttk.Frame(notebook, padding=10)
        notebook.add(general_frame, text=self.tr("general"))

        ttk.Label(general_frame, text=self.tr("profile_name")).grid(row=0, column=0, sticky=tk.W, pady=2)
        self.name_var = tk.StringVar()
        ttk.Entry(general_frame, textvariable=self.name_var, width=40).grid(row=0, column=1, padx=5, sticky=tk.W)

        ttk.Label(general_frame, text=self.tr("description")).grid(row=1, column=0, sticky=tk.W, pady=2)
        self.desc_var = tk.StringVar()
        ttk.Entry(general_frame, textvariable=self.desc_var, width=40).grid(row=1, column=1, padx=5, sticky=tk.W)

        ttk.Label(general_frame, text=self.tr("default_address")).grid(row=2, column=0, sticky=tk.W, pady=2)
        self.addr_var = tk.IntVar(value=1)
        ttk.Spinbox(general_frame, from_=1, to=247, textvariable=self.addr_var, width=8).grid(row=2, column=1, padx=5, sticky=tk.W)

        ttk.Label(general_frame, text=self.tr("default_baudrate")).grid(row=3, column=0, sticky=tk.W, pady=2)
        self.baud_var = tk.IntVar(value=4800)
        ttk.Combobox(general_frame, textvariable=self.baud_var, values=[2400, 4800, 9600], state="readonly", width=10).grid(row=3, column=1, padx=5, sticky=tk.W)

        # Вкладка "Параметры"
        params_frame = ttk.Frame(notebook, padding=10)
        notebook.add(params_frame, text=self.tr("parameters"))

        # Таблица параметров
        columns = ("key", "name_key", "unit", "address", "factor", "offset")
        self.params_tree = ttk.Treeview(params_frame, columns=columns, show="headings", height=10)
        for col in columns:
            self.params_tree.heading(col, text=self.tr(col))
            self.params_tree.column(col, width=100)
        self.params_tree.pack(fill=tk.BOTH, expand=True)

        # Кнопки управления параметрами
        param_btn_frame = ttk.Frame(params_frame)
        param_btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(param_btn_frame, text=self.tr("add_parameter"), command=self.add_parameter).pack(side=tk.LEFT, padx=2)
        ttk.Button(param_btn_frame, text=self.tr("edit_parameter"), command=self.edit_parameter).pack(side=tk.LEFT, padx=2)
        ttk.Button(param_btn_frame, text=self.tr("delete_parameter"), command=self.delete_parameter).pack(side=tk.LEFT, padx=2)

        # Вкладка "Системные регистры"
        sysreg_frame = ttk.Frame(notebook, padding=10)
        notebook.add(sysreg_frame, text=self.tr("system_registers"))

        # Таблица системных регистров
        sys_columns = ("key", "name_key", "address", "factor", "offset", "unit", "writable")
        self.sys_tree = ttk.Treeview(sysreg_frame, columns=sys_columns, show="headings", height=10)
        for col in sys_columns:
            self.sys_tree.heading(col, text=self.tr(col))
            self.sys_tree.column(col, width=100)
        self.sys_tree.pack(fill=tk.BOTH, expand=True)

        sys_btn_frame = ttk.Frame(sysreg_frame)
        sys_btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(sys_btn_frame, text=self.tr("add_sysreg"), command=self.add_sysreg).pack(side=tk.LEFT, padx=2)
        ttk.Button(sys_btn_frame, text=self.tr("edit_sysreg"), command=self.edit_sysreg).pack(side=tk.LEFT, padx=2)
        ttk.Button(sys_btn_frame, text=self.tr("delete_sysreg"), command=self.delete_sysreg).pack(side=tk.LEFT, padx=2)

        # Вкладка "Калибровка"
        calib_frame = ttk.Frame(notebook, padding=10)
        notebook.add(calib_frame, text=self.tr("calibration"))

        # Таблица калибровок (параметр -> модель -> коэффициенты)
        calib_columns = ("parameter", "model", "coefficients")
        self.calib_tree = ttk.Treeview(calib_frame, columns=calib_columns, show="headings", height=10)
        for col in calib_columns:
            self.calib_tree.heading(col, text=self.tr(col))
            self.calib_tree.column(col, width=150)
        self.calib_tree.pack(fill=tk.BOTH, expand=True)

        calib_btn_frame = ttk.Frame(calib_frame)
        calib_btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(calib_btn_frame, text=self.tr("add_calib"), command=self.add_calib).pack(side=tk.LEFT, padx=2)
        ttk.Button(calib_btn_frame, text=self.tr("edit_calib"), command=self.edit_calib).pack(side=tk.LEFT, padx=2)
        ttk.Button(calib_btn_frame, text=self.tr("delete_calib"), command=self.delete_calib).pack(side=tk.LEFT, padx=2)

        # Кнопки внизу
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(btn_frame, text=self.tr("ok"), command=self.ok).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text=self.tr("cancel"), command=self.destroy).pack(side=tk.RIGHT, padx=5)

    def load_data(self):
        """Загружает данные текущего профиля в интерфейс."""
        self.name_var.set(self.profile_data.get("name", ""))
        self.desc_var.set(self.profile_data.get("description", ""))
        device = self.profile_data.get("device", {})
        self.addr_var.set(device.get("default_address", 1))
        self.baud_var.set(device.get("default_baudrate", 4800))

        # Параметры
        for p in self.profile_data.get("parameters", []):
            self.params_tree.insert("", tk.END, values=(
                p.get("key", ""),
                p.get("name_key", ""),
                p.get("unit", ""),
                p.get("address", ""),
                p.get("factor", 1),
                p.get("offset", 0)
            ))

        # Системные регистры
        for r in self.profile_data.get("system_registers", []):
            self.sys_tree.insert("", tk.END, values=(
                r.get("key", ""),
                r.get("name_key", ""),
                r.get("address", ""),
                r.get("factor", 1),
                r.get("offset", 0),
                r.get("unit", ""),
                "Да" if r.get("writable") else "Нет"
            ))

        # Калибровка
        calib = self.profile_data.get("calibration", {})
        if calib is None:
            calib = {}
        for param, data in calib.items():
            model = data.get("model", "")
            coeffs = data.get("coefficients", [])
            coeff_str = ", ".join([f"{c:.4f}" for c in coeffs])
            self.calib_tree.insert("", tk.END, values=(param, model, coeff_str))

    def ok(self):
        """Собирает данные из интерфейса и сохраняет в self.profile_data, затем закрывает."""
        self.profile_data["name"] = self.name_var.get().strip()
        self.profile_data["description"] = self.desc_var.get().strip()
        self.profile_data["device"] = {
            "default_address": self.addr_var.get(),
            "default_baudrate": self.baud_var.get(),
            "available_baudrates": [2400, 4800, 9600]
        }

        # Собираем параметры
        params = []
        for child in self.params_tree.get_children():
            vals = self.params_tree.item(child, "values")
            params.append({
                "key": vals[0],
                "name_key": vals[1],
                "unit": vals[2],
                "address": int(vals[3]),
                "factor": float(vals[4]),
                "offset": float(vals[5])
            })
        self.profile_data["parameters"] = params

        # Собираем системные регистры
        sysregs = []
        for child in self.sys_tree.get_children():
            vals = self.sys_tree.item(child, "values")
            sysregs.append({
                "key": vals[0],
                "name_key": vals[1],
                "address": int(vals[2]),
                "factor": float(vals[3]),
                "offset": float(vals[4]),
                "unit": vals[5],
                "writable": vals[6] == "Да"
            })
        self.profile_data["system_registers"] = sysregs

        # Собираем калибровку
        calib = {}
        for child in self.calib_tree.get_children():
            vals = self.calib_tree.item(child, "values")
            param = vals[0]
            model = vals[1]
            coeff_str = vals[2]
            if coeff_str:
                coeffs = [float(c.strip()) for c in coeff_str.split(",")]
            else:
                coeffs = []
            calib[param] = {"model": model, "coefficients": coeffs}
        self.profile_data["calibration"] = calib

        self.result = self.profile_data
        self.destroy()

    def add_parameter(self):
        self._edit_parameter(None)

    def edit_parameter(self):
        selected = self.params_tree.selection()
        if not selected:
            return
        item = selected[0]
        values = self.params_tree.item(item, "values")
        self._edit_parameter(item, values)

    def _edit_parameter(self, item, values=None):
        dlg = tk.Toplevel(self)
        dlg.title(self.tr("edit_parameter"))
        dlg.geometry("400x300")
        dlg.transient(self)
        dlg.grab_set()

        fields = {}
        labels = ["key", "name_key", "unit", "address", "factor", "offset"]
        for i, label in enumerate(labels):
            ttk.Label(dlg, text=self.tr(label)).grid(row=i, column=0, padx=5, pady=2, sticky=tk.W)
            var = tk.StringVar(value=values[i] if values else "")
            entry = ttk.Entry(dlg, textvariable=var, width=30)
            entry.grid(row=i, column=1, padx=5, pady=2)
            fields[label] = var

        def save():
            new_values = [fields[l].get() for l in labels]
            if item:
                self.params_tree.item(item, values=new_values)
            else:
                self.params_tree.insert("", tk.END, values=new_values)
            dlg.destroy()

        ttk.Button(dlg, text=self.tr("ok"), command=save).grid(row=len(labels), column=0, columnspan=2, pady=10)

    def delete_parameter(self):
        selected = self.params_tree.selection()
        if selected:
            self.params_tree.delete(selected[0])

    def add_sysreg(self):
        self._edit_sysreg(None)

    def edit_sysreg(self):
        selected = self.sys_tree.selection()
        if not selected:
            return
        item = selected[0]
        values = self.sys_tree.item(item, "values")
        self._edit_sysreg(item, values)

    def _edit_sysreg(self, item, values=None):
        dlg = tk.Toplevel(self)
        dlg.title(self.tr("edit_sysreg"))
        dlg.geometry("450x350")
        dlg.transient(self)
        dlg.grab_set()

        fields = {}
        labels = ["key", "name_key", "address", "factor", "offset", "unit", "writable"]
        for i, label in enumerate(labels):
            ttk.Label(dlg, text=self.tr(label)).grid(row=i, column=0, padx=5, pady=2, sticky=tk.W)
            if label == "writable":
                var = tk.StringVar(value=values[i] if values else "Да")
                cb = ttk.Combobox(dlg, textvariable=var, values=["Да", "Нет"], state="readonly")
                cb.grid(row=i, column=1, padx=5, pady=2)
                fields[label] = var
            else:
                var = tk.StringVar(value=values[i] if values else "")
                entry = ttk.Entry(dlg, textvariable=var, width=30)
                entry.grid(row=i, column=1, padx=5, pady=2)
                fields[label] = var

        def save():
            new_values = [fields[l].get() for l in labels]
            if item:
                self.sys_tree.item(item, values=new_values)
            else:
                self.sys_tree.insert("", tk.END, values=new_values)
            dlg.destroy()

        ttk.Button(dlg, text=self.tr("ok"), command=save).grid(row=len(labels), column=0, columnspan=2, pady=10)

    def delete_sysreg(self):
        selected = self.sys_tree.selection()
        if selected:
            self.sys_tree.delete(selected[0])

    def add_calib(self):
        self._edit_calib(None)

    def edit_calib(self):
        selected = self.calib_tree.selection()
        if not selected:
            return
        item = selected[0]
        values = self.calib_tree.item(item, "values")
        self._edit_calib(item, values)

    def _edit_calib(self, item, values=None):
        dlg = tk.Toplevel(self)
        dlg.title(self.tr("edit_calibration"))
        dlg.geometry("400x300")
        dlg.transient(self)
        dlg.grab_set()

        ttk.Label(dlg, text=self.tr("parameter")).grid(row=0, column=0, padx=5, pady=2, sticky=tk.W)
        param_var = tk.StringVar(value=values[0] if values else "")
        param_entry = ttk.Entry(dlg, textvariable=param_var, width=30)
        param_entry.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(dlg, text=self.tr("model")).grid(row=1, column=0, padx=5, pady=2, sticky=tk.W)
        model_var = tk.StringVar(value=values[1] if values else "linear")
        model_combo = ttk.Combobox(dlg, textvariable=model_var, values=["linear", "poly2", "poly3"], state="readonly")
        model_combo.grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(dlg, text=self.tr("coefficients")).grid(row=2, column=0, padx=5, pady=2, sticky=tk.W)
        coeff_var = tk.StringVar(value=values[2] if values else "")
        coeff_entry = ttk.Entry(dlg, textvariable=coeff_var, width=30)
        coeff_entry.grid(row=2, column=1, padx=5, pady=2)

        def save():
            new_values = (param_var.get(), model_var.get(), coeff_var.get())
            if item:
                self.calib_tree.item(item, values=new_values)
            else:
                self.calib_tree.insert("", tk.END, values=new_values)
            dlg.destroy()

        ttk.Button(dlg, text=self.tr("ok"), command=save).grid(row=3, column=0, columnspan=2, pady=10)

    def delete_calib(self):
        selected = self.calib_tree.selection()
        if selected:
            self.calib_tree.delete(selected[0])