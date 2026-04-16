# modules/calibration/save_dialog.py
import tkinter as tk
from tkinter import ttk, messagebox
import json
import os

class SaveCalibrationDialog(tk.Toplevel):
    def __init__(self, parent, core_api, calibration_results, tr):
        super().__init__(parent)
        self.parent = parent
        self.core_api = core_api
        self.calibration_results = calibration_results
        self.tr = tr
        self.title(self.tr("save_calib_title"))
        self.geometry("300x150")
        self.transient(parent)
        self.grab_set()

        ttk.Label(self, text=self.tr("select_profile")).pack(pady=5)
        self.profile_combo = ttk.Combobox(self, state="readonly", width=30)
        self.profile_combo.pack(pady=5)
        self.profile_combo['values'] = self.core_api.profile_manager.list_profiles()
        if self.profile_combo['values']:
            self.profile_combo.set(self.profile_combo['values'][0])

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text=self.tr("save"), command=self.save).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text=self.tr("cancel"), command=self.destroy).pack(side=tk.LEFT, padx=5)

    def save(self):
        fname = self.profile_combo.get()
        if not fname:
            messagebox.showerror(self.tr("error"), self.tr("select_profile"))
            return
        profile_data = self.core_api.profile_manager.get_profile(fname)
        if not profile_data:
            messagebox.showerror(self.tr("error"), self.tr("profile_not_found"))
            return

        # Сохраняем калибровку в профиль
        profile_data['calibration'] = self.calibration_results
        if self.core_api.profile_manager.save_profile(fname, profile_data):
            messagebox.showinfo(self.tr("success"), self.tr("calib_saved"))
            self.destroy()
        else:
            messagebox.showerror(self.tr("error"), self.tr("save_failed"))