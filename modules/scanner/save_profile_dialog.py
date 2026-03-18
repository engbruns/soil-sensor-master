# modules/scanner/save_profile_dialog.py
import tkinter as tk
from tkinter import ttk, messagebox
from core.constants import STANDARD_PARAMS

class SaveProfileDialog(tk.Toplevel):
    def __init__(self, parent, core_api, snapshot, manual_mapping, last_probs, tr):
        super().__init__(parent)
        self.parent = parent
        self.core_api = core_api
        self.snapshot = snapshot
        self.manual_mapping = manual_mapping
        self.last_probs = last_probs
        self.tr = tr
        self.title(tr("save_profile"))
        self.geometry("300x200")
        self.transient(parent)
        self.grab_set()

        ttk.Label(self, text=tr("profile_name")).pack(pady=5)
        self.name_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.name_var, width=30).pack(pady=5)

        ttk.Label(self, text=tr("description")).pack(pady=5)
        self.desc_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.desc_var, width=30).pack(pady=5)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text=tr("save"), command=self.save).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text=tr("cancel"), command=self.destroy).pack(side=tk.LEFT, padx=5)

    def save(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror(self.tr("error"), self.tr("enter_name"))
            return
        parameters = []
        for addr, item in self.manual_mapping.items():
            param_key = item.get("param")
            if not param_key:
                continue
            params = {
                "key": param_key,
                "name": self.tr(param_key),
                "unit": STANDARD_PARAMS.get(param_key, {}).get("unit_key", ""),
                "address": addr,
                "function_code": 3,
                "factor": item.get("factor", 1),
                "offset": item.get("offset", 0)
            }
            parameters.append(params)
        if not parameters:
            messagebox.showerror(self.tr("error"), self.tr("no_params"))
            return
        fname = name.replace(" ", "_").lower() + ".json"
        profile_data = {
            "name": name,
            "description": self.desc_var.get().strip(),
            "device": {
                "default_address": 1,
                "default_baudrate": self.core_api.get_setting("last_baudrate", 4800),
                "available_baudrates": [2400, 4800, 9600]
            },
            "parameters": parameters,
            "system_registers": [],
            "calibration": None,
            "analysis": self.last_probs
        }
        if self.core_api.profile_manager.save_profile(fname, profile_data):
            messagebox.showinfo(self.tr("success"), self.tr("profile_saved"))
            self.destroy()
        else:
            messagebox.showerror(self.tr("error"), self.tr("save_failed"))