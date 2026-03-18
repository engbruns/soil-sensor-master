# modules/calibration/export_dialog.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv
import os

class ExportCsvDialog(tk.Toplevel):
    def __init__(self, parent, points, selected_params, mode, param_info, ref_param_info, tr):
        super().__init__(parent)
        self.parent = parent
        self.points = points
        self.selected_params = selected_params
        self.mode = mode
        self.param_info = param_info
        self.ref_param_info = ref_param_info
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

    def export(self, filename):
        # Определяем максимальное количество сырых значений по всем точкам и параметрам
        max_samples = 0
        for point in self.points:
            for param in self.selected_params:
                raw_list = point['raw_stats'].get(param, {}).get('raw', [])
                max_samples = max(max_samples, len(raw_list))
                if self.mode == 'ref' and self.ref_param_info:
                    ref_list = point.get('ref_stats', {}).get(param, {}).get('raw', [])
                    max_samples = max(max_samples, len(ref_list))

        # Заголовки
        header = ["Точка", "Параметр", "Тип", "Медиана", "Среднее", "Макс", "Мин"]
        for i in range(max_samples):
            header.append(f"Значение {i+1}")

        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(header)

            for i, point in enumerate(self.points):
                point_num = i + 1
                for param in self.selected_params:
                    # Калибруемый датчик
                    raw_stat = point['raw_stats'].get(param)
                    if raw_stat:
                        factor = self.param_info.get(param, {}).get('factor', 1)
                        offset = self.param_info.get(param, {}).get('offset', 0)
                        median = raw_stat['median'] * factor + offset if raw_stat['median'] is not None else None
                        avg = raw_stat['avg'] * factor + offset if raw_stat['avg'] is not None else None
                        max_val = raw_stat['max'] * factor + offset if raw_stat['max'] is not None else None
                        min_val = raw_stat['min'] * factor + offset if raw_stat['min'] is not None else None
                        raw_vals = [(v * factor + offset) if v is not None else None for v in raw_stat['raw']]

                        row = [point_num, self.tr(param), "Калибруемый",
                               f"{median:.2f}" if median is not None else '',
                               f"{avg:.2f}" if avg is not None else '',
                               f"{max_val:.2f}" if max_val is not None else '',
                               f"{min_val:.2f}" if min_val is not None else '']
                        for v in raw_vals:
                            row.append(f"{v:.2f}" if v is not None else '')
                        # Дополнить до max_samples пустыми
                        for _ in range(max_samples - len(raw_vals)):
                            row.append('')
                        writer.writerow(row)

                    # Эталонная строка
                    if self.mode == 'lab':
                        ref_val = point.get('ref_values', {}).get(param)
                        if ref_val is not None:
                            row = [point_num, self.tr(param), "Эталон",
                                   f"{ref_val:.2f}", f"{ref_val:.2f}", f"{ref_val:.2f}", f"{ref_val:.2f}"]
                            # Для эталона в лабораторном режиме сырых значений нет, заполняем пустыми
                            for _ in range(max_samples):
                                row.append('')
                            writer.writerow(row)
                    else:  # режим эталонного датчика
                        ref_stat = point.get('ref_stats', {}).get(param)
                        if ref_stat and self.ref_param_info:
                            ref_factor = self.ref_param_info.get(param, {}).get('factor', 1)
                            ref_offset = self.ref_param_info.get(param, {}).get('offset', 0)
                            median_r = ref_stat['median'] * ref_factor + ref_offset if ref_stat['median'] is not None else None
                            avg_r = ref_stat['avg'] * ref_factor + ref_offset if ref_stat['avg'] is not None else None
                            max_r = ref_stat['max'] * ref_factor + ref_offset if ref_stat['max'] is not None else None
                            min_r = ref_stat['min'] * ref_factor + ref_offset if ref_stat['min'] is not None else None
                            ref_raw_vals = [(v * ref_factor + ref_offset) if v is not None else None for v in ref_stat['raw']]

                            row = [point_num, self.tr(param), "Эталон",
                                   f"{median_r:.2f}" if median_r is not None else '',
                                   f"{avg_r:.2f}" if avg_r is not None else '',
                                   f"{max_r:.2f}" if max_r is not None else '',
                                   f"{min_r:.2f}" if min_r is not None else '']
                            for v in ref_raw_vals:
                                row.append(f"{v:.2f}" if v is not None else '')
                            for _ in range(max_samples - len(ref_raw_vals)):
                                row.append('')
                            writer.writerow(row)