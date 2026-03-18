# ui/dialogs/graph_settings_dialog.py
import tkinter as tk
from tkinter import ttk, messagebox

class GraphSettingsDialog(tk.Toplevel):
    def __init__(self, parent, core_api, tr):
        super().__init__(parent)
        self.parent = parent
        self.core_api = core_api
        self.tr = tr
        self.title(tr("dialog.graph_settings"))
        self.geometry("550x450")
        self.transient(parent)
        self.grab_set()

        # Копируем текущие настройки графиков
        self.graph_settings = core_api.settings.get("graph_settings", {}).copy()
        self.result = False

        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.cancel)

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Максимальное количество точек
        ttk.Label(main_frame, text=self.tr("settings.max_points")).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.max_history_var = tk.IntVar(value=self.graph_settings.get("max_history", 300))
        ttk.Spinbox(main_frame, from_=10, to=10000, textvariable=self.max_history_var, width=10).grid(row=0, column=1, sticky=tk.W, padx=5)

        # Рамка с вкладками для параметров
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=1, column=0, columnspan=2, pady=10, sticky=tk.NSEW)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)

        # Список параметров (как в старом коде)
        params = [
            (self.tr("Температура"), "temperature"),
            (self.tr("Влажность"), "humidity"),
            (self.tr("pH"), "ph"),
            (self.tr("EC"), "ec"),
            (self.tr("Азот (N)"), "nitrogen"),
            (self.tr("Фосфор (P)"), "phosphorus"),
            (self.tr("Калий (K)"), "potassium"),
            (self.tr("Солёность"), "salinity"),
            (self.tr("TDS"), "tds"),
        ]

        self.limit_vars = {}
        y_limits = self.graph_settings.get("y_limits", {})

        for display_name, key in params:
            frame = ttk.Frame(notebook, padding=5)
            notebook.add(frame, text=display_name)

            limits = y_limits.get(key, {})
            auto_val = limits.get("auto", True)
            min_val = limits.get("min", 0)
            max_val = limits.get("max", 100)
            step_val = limits.get("step", 10)

            auto_var = tk.BooleanVar(value=auto_val)
            min_var = tk.DoubleVar(value=min_val)
            max_var = tk.DoubleVar(value=max_val)
            step_var = tk.DoubleVar(value=step_val)

            self.limit_vars[key] = (auto_var, min_var, max_var, step_var)

            ttk.Checkbutton(frame, text=self.tr("settings.auto"), variable=auto_var).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=5)

            ttk.Label(frame, text=self.tr("settings.min")).grid(row=1, column=0, sticky=tk.W, pady=2)
            ttk.Entry(frame, textvariable=min_var, width=10).grid(row=1, column=1, sticky=tk.W, padx=5)

            ttk.Label(frame, text=self.tr("settings.max")).grid(row=2, column=0, sticky=tk.W, pady=2)
            ttk.Entry(frame, textvariable=max_var, width=10).grid(row=2, column=1, sticky=tk.W, padx=5)

            ttk.Label(frame, text=self.tr("settings.step")).grid(row=3, column=0, sticky=tk.W, pady=2)
            ttk.Entry(frame, textvariable=step_var, width=10).grid(row=3, column=1, sticky=tk.W, padx=5)

        # Кнопки
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text=self.tr("settings.save"), command=self.save).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text=self.tr("settings.cancel"), command=self.cancel).pack(side=tk.LEFT, padx=5)

    def save(self):
        # Обновляем локальную копию
        self.graph_settings["max_history"] = self.max_history_var.get()
        y_limits = {}
        for key, (auto_var, min_var, max_var, step_var) in self.limit_vars.items():
            y_limits[key] = {
                "auto": auto_var.get(),
                "min": min_var.get(),
                "max": max_var.get(),
                "step": step_var.get()
            }
        self.graph_settings["y_limits"] = y_limits

        # Применяем к основным настройкам
        self.core_api.settings["graph_settings"] = self.graph_settings
        self.result = True
        self.destroy()

    def cancel(self):
        self.result = False
        self.destroy()