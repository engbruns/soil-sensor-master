import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv

from utils.value_transform import convert_parameter_value


class ExportCsvDialog(tk.Toplevel):
    def __init__(self, parent, points, param_info, ref_param_info, mode, tr):
        super().__init__(parent)
        self.parent = parent
        self.points = points
        self.param_info = param_info
        self.ref_param_info = ref_param_info
        self.mode = mode
        self.tr = tr

        self.title(self.tr("export_csv_title"))
        self.geometry("300x100")
        self.transient(parent)
        self.grab_set()

        ttk.Label(self, text=self.tr("select_csv_path")).pack(pady=5)
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text=self.tr("choose_path"), command=self.choose).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text=self.tr("cancel"), command=self.destroy).pack(side=tk.LEFT, padx=5)

    def choose(self):
        filename = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if filename:
            self.export(filename)
            messagebox.showinfo(self.tr("success"), self.tr("export_success"))
            self.destroy()

    def _param_def(self, param_key, ref=False):
        info = self.ref_param_info if ref else self.param_info
        return info.get(param_key, {"key": param_key})

    def _convert_raw(self, raw, param_key, ref=False):
        if raw is None:
            return None
        # Export should reflect engineering conversion (signed/factor/offset) without saved model.
        return convert_parameter_value(raw, self._param_def(param_key, ref=ref), None)

    def export(self, filename):
        max_samples = 0
        for point in self.points:
            for _, raw_stat in point["raw_stats"].items():
                if raw_stat:
                    max_samples = max(max_samples, len(raw_stat.get("raw", [])))
            if self.mode == "ref" and point.get("ref_stats"):
                for _, ref_stat in point["ref_stats"].items():
                    if ref_stat:
                        max_samples = max(max_samples, len(ref_stat.get("raw", [])))

        header = ["Точка", "Время", "Параметр", "Тип", "Медиана", "Среднее", "Макс", "Мин"]
        for i in range(max_samples):
            header.append(f"Значение {i + 1}")

        with open(filename, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(header)

            for i, point in enumerate(self.points):
                point_num = i + 1
                timestamp = point.get("timestamp", "")
                selected_params = point["selected_params"]

                for param in selected_params:
                    raw_stat = point["raw_stats"].get(param)
                    if raw_stat:
                        median = self._convert_raw(raw_stat.get("median"), param, ref=False)
                        avg = self._convert_raw(raw_stat.get("avg"), param, ref=False)
                        max_val = self._convert_raw(raw_stat.get("max"), param, ref=False)
                        min_val = self._convert_raw(raw_stat.get("min"), param, ref=False)
                        raw_vals = [self._convert_raw(v, param, ref=False) if v is not None else None for v in raw_stat["raw"]]

                        row = [
                            point_num,
                            timestamp,
                            self.tr(param),
                            self.tr("calib"),
                            f"{median:.2f}" if median is not None else "",
                            f"{avg:.2f}" if avg is not None else "",
                            f"{max_val:.2f}" if max_val is not None else "",
                            f"{min_val:.2f}" if min_val is not None else "",
                        ]
                        for v in raw_vals:
                            row.append(f"{v:.2f}" if v is not None else "")
                        for _ in range(max_samples - len(raw_vals)):
                            row.append("")
                        writer.writerow(row)

                    if self.mode == "lab":
                        ref_val = point.get("ref_values", {}).get(param)
                        if ref_val is not None:
                            row = [
                                point_num,
                                timestamp,
                                self.tr(param),
                                self.tr("ref"),
                                f"{ref_val:.2f}",
                                f"{ref_val:.2f}",
                                f"{ref_val:.2f}",
                                f"{ref_val:.2f}",
                            ]
                            for _ in range(max_samples):
                                row.append("")
                            writer.writerow(row)
                    else:
                        ref_stat = point.get("ref_stats", {}).get(param)
                        if ref_stat and self.ref_param_info:
                            median_r = self._convert_raw(ref_stat.get("median"), param, ref=True)
                            avg_r = self._convert_raw(ref_stat.get("avg"), param, ref=True)
                            max_r = self._convert_raw(ref_stat.get("max"), param, ref=True)
                            min_r = self._convert_raw(ref_stat.get("min"), param, ref=True)
                            ref_raw_vals = [
                                self._convert_raw(v, param, ref=True) if v is not None else None
                                for v in ref_stat["raw"]
                            ]

                            row = [
                                point_num,
                                timestamp,
                                self.tr(param),
                                self.tr("ref"),
                                f"{median_r:.2f}" if median_r is not None else "",
                                f"{avg_r:.2f}" if avg_r is not None else "",
                                f"{max_r:.2f}" if max_r is not None else "",
                                f"{min_r:.2f}" if min_r is not None else "",
                            ]
                            for v in ref_raw_vals:
                                row.append(f"{v:.2f}" if v is not None else "")
                            for _ in range(max_samples - len(ref_raw_vals)):
                                row.append("")
                            writer.writerow(row)
