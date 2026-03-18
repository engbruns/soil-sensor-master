# modules/scanner/assign_dialog.py
import tkinter as tk
from tkinter import ttk
from core.constants import STANDARD_PARAMS

class AssignParamDialog(tk.Toplevel):
    def __init__(self, parent, addr_hex, current_param, callback, tr):
        super().__init__(parent)
        self.parent = parent
        self.addr_hex = addr_hex
        self.callback = callback
        self.tr = tr
        self.title(f"Assign parameter for {addr_hex}")
        self.geometry("300x260")
        self.transient(parent)
        self.grab_set()

        ttk.Label(self, text=tr("parameter")).pack(pady=5)
        self.param_var = tk.StringVar(value=current_param if current_param else "")
        param_keys = list(STANDARD_PARAMS.keys())
        self.param_combo = ttk.Combobox(self, textvariable=self.param_var, values=param_keys, state="readonly")
        self.param_combo.pack(pady=5)
        self.param_combo.bind("<<ComboboxSelected>>", self.on_param_select)

        ttk.Label(self, text=tr("factor")).pack(pady=5)
        self.factor_var = tk.DoubleVar(value=1.0)
        ttk.Entry(self, textvariable=self.factor_var).pack(pady=5)

        ttk.Label(self, text=tr("offset")).pack(pady=5)
        self.offset_var = tk.DoubleVar(value=0.0)
        ttk.Entry(self, textvariable=self.offset_var).pack(pady=5)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text=tr("ok"), command=self.ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text=tr("cancel"), command=self.destroy).pack(side=tk.LEFT, padx=5)

    def on_param_select(self, event):
        param = self.param_var.get()
        if param in STANDARD_PARAMS:
            self.factor_var.set(STANDARD_PARAMS[param]["factor"])
            self.offset_var.set(STANDARD_PARAMS[param]["offset"])

    def ok(self):
        if self.callback:
            self.callback(self.addr_hex, {
                "param": self.param_var.get(),
                "factor": self.factor_var.get(),
                "offset": self.offset_var.get()
            })
        self.destroy()