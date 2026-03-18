# modules/calibration/save_dialog.py
import tkinter as tk
from tkinter import ttk, messagebox

class SaveCalibrationDialog(tk.Toplevel):
    def __init__(self, parent, core_api, selected_params, calibration_results, tr):
        super().__init__(parent)
        self.parent = parent
        self.core_api = core_api
        self.selected_params = selected_params
        self.calibration_results = calibration_results
        self.tr = tr
        self.title(self.tr("save_calib_title"))
        self.geometry("300x200")
        self.transient(parent)
        self.grab_set()

        ttk.Label(self, text=self.tr("profile_name")).pack(pady=5)
        self.name_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.name_var, width=30).pack(pady=5)

        ttk.Label(self, text=self.tr("description")).pack(pady=5)
        self.desc_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.desc_var, width=30).pack(pady=5)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text=self.tr("save"), command=self.save).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text=self.tr("cancel"), command=self.destroy).pack(side=tk.LEFT, padx=5)

    def save(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror(self.tr("error"), self.tr("enter_name"))
            return
        # Здесь будет логика сохранения
        messagebox.showinfo(self.tr("success"), self.tr("save_not_implemented"))
        self.destroy()