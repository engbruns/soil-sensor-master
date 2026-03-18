# modules/calibration/result_dialog.py
import tkinter as tk
from tkinter import ttk

class RegressionResultDialog(tk.Toplevel):
    def __init__(self, parent, param, result, tr):
        super().__init__(parent)
        self.parent = parent
        self.tr = tr
        self.title(f"{tr('regression')} - {tr(param)}")
        self.geometry("300x150")
        self.transient(parent)
        self.grab_set()

        text = f"{tr('model')}: {result['model']}\n"
        if result['model'] == 'linear':
            a, b = result['coefficients']
            text += f"y = {a:.4f} x + {b:.4f}\n"
        elif result['model'] == 'poly2':
            c, b, a = result['coefficients']
            text += f"y = {a:.4f} x² + {b:.4f} x + {c:.4f}\n"
        elif result['model'] == 'poly3':
            d, c, b, a = result['coefficients']
            text += f"y = {a:.4f} x³ + {b:.4f} x² + {c:.4f} x + {d:.4f}\n"
        text += f"R² = {result['r2']:.4f}"

        ttk.Label(self, text=text, justify=tk.LEFT).pack(pady=10)
        ttk.Button(self, text=self.tr("ok"), command=self.destroy).pack(pady=5)