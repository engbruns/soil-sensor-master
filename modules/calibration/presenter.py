# modules/calibration/presenter.py
import tkinter as tk
from .panel import CalibrationPanel
from .ref_value_dialog import RefValueDialog
from .save_dialog import SaveCalibrationDialog
from .export_dialog import ExportCsvDialog
from .graph_dialog import GraphDialog
from .result_dialog import RegressionResultDialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np

class CalibrationPresenter:
    def __init__(self, engine, parent, core_api):
        self.engine = engine
        self.core_api = core_api
        self.tr = core_api.tr
        self.view = CalibrationPanel(parent, self, self.tr)
        self.selected_params = []
        self.points = []
        self.ref_sensor = None
        self.ref_profile_data = None
        self.calibration_results = {}
        self.current_mode = 'lab'
        self.param_info = {}          # информация о параметрах калибруемого датчика
        self.ref_param_info = {}       # информация о параметрах эталонного датчика
        self._alive = True

        # Создаём область для графика
        self.fig, self.ax = plt.subplots(figsize=(5,4))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.view.graph_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.on_profile_changed()

    def get_view(self):
        return self.view

    def _load_param_info(self):
        profile = self.core_api.get_current_profile_data()
        if profile:
            self.param_info = {p['key']: p for p in profile.get('parameters', [])}
        else:
            self.param_info = {}

    def _load_ref_param_info(self):
        if self.ref_profile_data:
            self.ref_param_info = {p['key']: p for p in self.ref_profile_data.get('parameters', [])}
        else:
            self.ref_param_info = {}

    def on_profile_changed(self):
        profile = self.core_api.get_current_profile_data()
        if profile:
            params = profile.get('parameters', [])
            self.view.update_param_list(params)
            self._load_param_info()

    def on_add_point(self, mode, num_samples, selected_params):
        self.selected_params = selected_params
        self.current_mode = mode
        if mode == 'lab':
            self.engine.collect_point(
                selected_params, num_samples,
                callback=lambda raw_stats, ref_stats: self._on_lab_collected(raw_stats)
            )
        else:
            if not self.ref_sensor or not self.ref_sensor.connected:
                self.view.show_error(self.tr("ref_sensor_not_connected"))
                return
            ref_profile_fname = self.view.ref_profile_combo.get()
            self.ref_profile_data = self.core_api.profile_manager.get_profile(ref_profile_fname)
            if not self.ref_profile_data:
                self.view.show_error(self.tr("profile_not_found"))
                return
            self._load_ref_param_info()
            self.engine.collect_point(
                selected_params, num_samples,
                ref_sensor=self.ref_sensor,
                ref_profile_data=self.ref_profile_data,
                callback=lambda raw_stats, ref_stats: self._on_ref_collected(raw_stats, ref_stats)
            )

    def _on_lab_collected(self, raw_stats):
        if not self._alive:
            return
        if raw_stats is None:
            self.view.show_error(self.tr("collect_failed"))
            return
        RefValueDialog(self.view, self.selected_params, raw_stats, self._on_ref_values_entered, self.tr)

    def _on_ref_values_entered(self, raw_stats, ref_values):
        point = {
            'raw_stats': raw_stats,
            'ref_values': ref_values
        }
        self.points.append(point)
        self.view.update_points_table(self.points, self.selected_params, 'lab', self.param_info)
        self.view.enable_save_export(False)

    def _on_ref_collected(self, raw_stats, ref_stats):
        if not self._alive:
            return
        if raw_stats is None or ref_stats is None:
            self.view.show_error(self.tr("collect_failed"))
            return
        point = {
            'raw_stats': raw_stats,
            'ref_stats': ref_stats
        }
        self.points.append(point)
        self.view.update_points_table(self.points, self.selected_params, 'ref', self.param_info, self.ref_param_info)
        self.view.enable_save_export(False)

    def on_remove_point(self, index):
        if 0 <= index < len(self.points):
            del self.points[index]
            self.view.update_points_table(self.points, self.selected_params, self.current_mode,
                                          self.param_info, self.ref_param_info if self.current_mode=='ref' else None)
            self.view.enable_save_export(False)

    def on_show_graph_for_param(self, param):
        """Строит график: точки эталонов и линия медиан датчика."""
        self.ax.clear()
        X_ref = []
        y_ref = []
        X_med = []
        y_med = []
        factor = self.param_info.get(param, {}).get('factor', 1)
        offset = self.param_info.get(param, {}).get('offset', 0)
        for p in self.points:
            raw_median = p['raw_stats'].get(param, {}).get('median')
            if raw_median is not None:
                conv_median = raw_median * factor + offset
                X_med.append(len(X_med) + 1)
                y_med.append(conv_median)
            if self.current_mode == 'lab':
                ref_val = p.get('ref_values', {}).get(param)
                if ref_val is not None:
                    X_ref.append(len(X_ref) + 1)
                    y_ref.append(ref_val)
            else:
                ref_median = p.get('ref_stats', {}).get(param, {}).get('median')
                if ref_median is not None:
                    ref_factor = self.ref_param_info.get(param, {}).get('factor', 1)
                    ref_offset = self.ref_param_info.get(param, {}).get('offset', 0)
                    conv_ref = ref_median * ref_factor + ref_offset
                    X_ref.append(len(X_ref) + 1)
                    y_ref.append(conv_ref)

        if X_med:
            self.ax.plot(X_med, y_med, marker='o', linestyle='-', color='blue', label=self.tr("calib_median"))
        if X_ref:
            self.ax.plot(X_ref, y_ref, marker='s', linestyle='--', color='green', label=self.tr("ref_value"))
        self.ax.set_xlabel(self.tr("point_num"))
        self.ax.set_ylabel(self.tr("value"))
        self.ax.set_title(f"{self.tr(param)}")
        self.ax.grid(True)
        self.ax.legend()
        self.canvas.draw()

    def on_calculate_regression(self, param, model_type='linear'):
        if not self.points:
            self.view.show_error(self.tr("no_data"))
            return
        X = []
        y = []
        factor = self.param_info.get(param, {}).get('factor', 1)
        offset = self.param_info.get(param, {}).get('offset', 0)
        for p in self.points:
            raw_median = p['raw_stats'].get(param, {}).get('median')
            if raw_median is not None:
                conv_median = raw_median * factor + offset
                if self.current_mode == 'lab':
                    ref_val = p.get('ref_values', {}).get(param)
                    if ref_val is not None:
                        X.append(conv_median)
                        y.append(ref_val)
                else:
                    ref_median = p.get('ref_stats', {}).get(param, {}).get('median')
                    if ref_median is not None:
                        ref_factor = self.ref_param_info.get(param, {}).get('factor', 1)
                        ref_offset = self.ref_param_info.get(param, {}).get('offset', 0)
                        conv_ref = ref_median * ref_factor + ref_offset
                        X.append(conv_median)
                        y.append(conv_ref)
        if len(X) < 2:
            self.view.show_warning(self.tr("not_enough_points").format(self.tr(param)))
            return
        result = self.engine.calculate_regression(X, y, model_type)
        if result is None:
            self.view.show_warning(self.tr("regression_failed"))
            return
        self.calibration_results[param] = result
        RegressionResultDialog(self.view, param, result, self.tr)
        # Обновляем график с линией регрессии
        self.on_show_graph_for_param(param)
        # Добавим линию регрессии
        X_line = np.linspace(min(X), max(X), 100)
        if result['model'] == 'linear':
            a, b = result['coefficients']
            y_line = a * X_line + b
            label = f"{self.tr('regression')}: y = {a:.4f} x + {b:.4f}"
        elif result['model'] == 'poly2':
            c, b, a = result['coefficients']
            y_line = a * X_line**2 + b * X_line + c
            label = f"{self.tr('regression')}: y = {a:.4f} x² + {b:.4f} x + {c:.4f}"
        elif result['model'] == 'poly3':
            d, c, b, a = result['coefficients']
            y_line = a * X_line**3 + b * X_line**2 + c * X_line + d
            label = f"{self.tr('regression')}: y = {a:.4f} x³ + {b:.4f} x² + {c:.4f} x + {d:.4f}"
        else:
            return
        self.ax.plot(X_line, y_line, color='red', linestyle='-', label=label)
        self.ax.legend()
        self.canvas.draw()
        self.view.enable_save_export(True)

    def on_show_raw_graph(self, point_idx, param, sensor_type):
        if point_idx < 0 or point_idx >= len(self.points):
            return
        point = self.points[point_idx]
        if sensor_type == 'calib':
            raw_stats = point['raw_stats'].get(param)
            factor = self.param_info.get(param, {}).get('factor', 1)
            offset = self.param_info.get(param, {}).get('offset', 0)
        else:  # 'ref'
            raw_stats = point.get('ref_stats', {}).get(param)
            factor = self.ref_param_info.get(param, {}).get('factor', 1) if self.ref_param_info else 1
            offset = self.ref_param_info.get(param, {}).get('offset', 0) if self.ref_param_info else 0
        if raw_stats and raw_stats.get('raw'):
            raw_vals = [(v * factor + offset) if v is not None else None for v in raw_stats['raw']]
            median = raw_stats['median'] * factor + offset if raw_stats['median'] is not None else None
            from .graph_dialog import GraphDialog
            GraphDialog(self.view, f"{self.tr(param)} - {self.tr('raw_data')} ({self.tr(sensor_type)})", raw_vals, median, self.tr)

    def on_connect_ref(self, port, profile_fname):
        from utils.sensor import SoilSensor
        profile = self.core_api.profile_manager.get_profile(profile_fname)
        if not profile:
            self.view.show_error(self.tr("profile_not_found"))
            return
        baud = profile['device']['default_baudrate']
        self.ref_sensor = SoilSensor(port, baud)
        if self.ref_sensor.connect():
            self.view.update_ref_status(True)
            self.view.show_message(self.tr("ref_connected"))
        else:
            self.view.update_ref_status(False)
            self.view.show_error(self.tr("ref_connect_failed"))

    def on_disconnect_ref(self):
        if self.ref_sensor:
            self.ref_sensor.disconnect()
            self.ref_sensor = None
            self.ref_profile_data = None
            self.ref_param_info = {}
            self.view.update_ref_status(False)

    def on_save_calibration(self):
        if not self.calibration_results:
            self.view.show_error(self.tr("no_regression"))
            return
        SaveCalibrationDialog(self.view, self.core_api, self.selected_params, self.calibration_results, self.tr)

    def on_export_csv(self):
        if not self.points:
            self.view.show_error(self.tr("no_data"))
            return
        ExportCsvDialog(self.view, self.points, self.selected_params, self.current_mode,
                        self.param_info, self.ref_param_info if self.current_mode=='ref' else None, self.tr)

    def destroy(self):
        self._alive = False
        if self.ref_sensor:
            self.ref_sensor.disconnect()
        self.engine.stop()
        if self.view and self.view.winfo_exists():
            self.view.destroy()