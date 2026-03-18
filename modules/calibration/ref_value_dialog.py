# modules/calibration/ref_value_dialog.py
import tkinter as tk
from tkinter import ttk

class RefValueDialog(tk.Toplevel):
    def __init__(self, parent, selected_params, raw_stats, callback, tr):
        super().__init__(parent)
        self.parent = parent
        self.selected_params = selected_params
        self.raw_stats = raw_stats
        self.callback = callback
        self.tr = tr
        self.title(self.tr("enter_ref_values"))
        self.geometry("300x{}".format(100 + 30*len(selected_params)))
        self.transient(parent)
        self.grab_set()

        self.entries = {}
        row = 0
        for param in selected_params:
            ttk.Label(self, text=f"{tr(param)}:").grid(row=row, column=0, padx=5, pady=2, sticky=tk.W)
            var = tk.DoubleVar()
            entry = ttk.Entry(self, textvariable=var, width=10)
            entry.grid(row=row, column=1, padx=5, pady=2)
            self.entries[param] = var
            raw_val = raw_stats.get(param, {}).get('median', 0)
            ttk.Label(self, text=f"(сырое: {raw_val:.2f})").grid(row=row, column=2, padx=5, pady=2)
            row += 1

        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=row, column=0, columnspan=3, pady=10)
        ttk.Button(btn_frame, text=self.tr("ok"), command=self.ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text=self.tr("cancel"), command=self.destroy).pack(side=tk.LEFT, padx=5)

    def ok(self):
        ref_values = {}
        for param, var in self.entries.items():
            try:
                ref_values[param] = var.get()
            except:
                self.show_error(self.tr("invalid_number"))
                return
        self.callback(self.raw_stats, ref_values)
        self.destroy()