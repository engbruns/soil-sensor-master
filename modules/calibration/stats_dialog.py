# modules/calibration/stats_dialog.py
import tkinter as tk
from tkinter import ttk

class RawStatsDialog(tk.Toplevel):
    def __init__(self, parent, param, raw_stats, tr):
        super().__init__(parent)
        self.parent = parent
        self.tr = tr
        self.title(f"{tr('raw_stats')} - {tr(param)}")
        self.geometry("300x200")
        self.transient(parent)
        self.grab_set()

        ttk.Label(self, text=f"{tr('median')}: {raw_stats.get('median', '---'):.2f}").pack(pady=2)
        ttk.Label(self, text=f"{tr('min')}: {raw_stats.get('min', '---'):.2f}").pack(pady=2)
        ttk.Label(self, text=f"{tr('max')}: {raw_stats.get('max', '---'):.2f}").pack(pady=2)
        ttk.Label(self, text=f"{tr('avg')}: {raw_stats.get('avg', '---'):.2f}").pack(pady=2)
        ttk.Label(self, text=f"{tr('raw_values')}: {raw_stats.get('raw', [])}").pack(pady=2)

        ttk.Button(self, text=self.tr("close"), command=self.destroy).pack(pady=10)
        