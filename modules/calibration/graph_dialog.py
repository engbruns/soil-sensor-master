# modules/calibration/graph_dialog.py
import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class GraphDialog(tk.Toplevel):
    def __init__(self, parent, title, raw_values, median, tr):
        super().__init__(parent)
        self.title(title)
        self.geometry("600x400")

        fig, ax = plt.subplots(figsize=(6,4))
        if raw_values:
            x = list(range(len(raw_values)))
            y = [v if v is not None else 0 for v in raw_values]
            ax.scatter(x, y, label='Raw', s=10)
            if median is not None:
                ax.axhline(y=median, color='r', linestyle='--', label=f'Median = {median:.2f}')
        else:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center')
        ax.set_xlabel(tr("measurement"))
        ax.set_ylabel(tr("value"))
        ax.legend()
        ax.grid(True)

        canvas = FigureCanvasTkAgg(fig, master=self)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)