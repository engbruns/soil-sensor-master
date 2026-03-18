# modules/monitor/graph_window.py
import tkinter as tk
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.ticker as ticker

class GraphWindow(tk.Toplevel):
    def __init__(self, parent, title, unit, color, key, history_callback, settings, tr):
        super().__init__(parent)
        self.tr = tr
        self.title(title or self.tr("graph.window.title"))
        self.geometry("500x400")
        self.history_callback = history_callback
        self.unit = unit
        self.color = color
        self.key = key
        self.settings = settings

        self.fig = Figure(figsize=(5,4), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_xlabel(self.tr('graph.time_sec'))
        self.ax.set_ylabel(unit)
        self.ax.grid(True)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.update_graph()

    def update_graph(self):
        data = self.history_callback()
        if data and len(data) > 1:
            self.ax.clear()
            self.ax.plot(data, color=self.color)
            self.ax.set_xlabel(self.tr('graph.time_sec'))
            self.ax.set_ylabel(self.unit)
            self.ax.grid(True)

            limits = self.settings.get("graph_settings", {}).get("y_limits", {}).get(self.key, {})
            if not limits.get("auto", True):
                self.ax.set_ylim(limits.get("min", 0), limits.get("max", 100))
                step = limits.get("step")
                if step:
                    self.ax.yaxis.set_major_locator(ticker.MultipleLocator(step))

            last_val = data[-1]
            last_x = len(data)-1
            self.ax.annotate(f"{last_val:.1f}", (last_x, last_val),
                             xytext=(5,5), textcoords="offset points",
                             fontsize=9, color='red', weight='bold')
            self.ax.plot(last_x, last_val, 'ro', markersize=5)
            self.canvas.draw()
        self.after(2000, self.update_graph)