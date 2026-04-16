# modules/calibration/presenter.py
import tkinter as tk
import datetime
import threading
import queue
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from .panel import CalibrationPanel
from .engine import CalibrationEngine
from .ref_value_dialog import RefValueDialog
from .save_dialog import SaveCalibrationDialog
from .export_dialog import ExportCsvDialog
from .graph_dialog import GraphDialog
from .result_dialog import RegressionResultDialog
from utils.value_transform import convert_parameter_value

class CalibrationPresenter:
    def __init__(self, engine, parent, core_api):
        self.engine = engine
        self.core_api = core_api
        self.tr = core_api.tr
        self.view = CalibrationPanel(parent, self, self.tr)
        self.points = []
        self.calibration_results = {}
        self.current_mode = 'lab'
        self.calib_sensor = None
        self.ref_sensor = None
        self.calib_sensor_name = None
        self.ref_sensor_name = None
        self.calib_profile_data = None
        self.ref_profile_data = None
        self.param_info = {}
        self.ref_param_info = {}
        self.current_graph_type = "points"
        self.current_graph_param = None
        self._collecting = False
        self._updating = True
        self._data_queue = queue.Queue()
        self._worker_thread = None
        self._worker_wakeup = threading.Event()
        self._after_id = None

        self.fig, self.ax = plt.subplots(figsize=(5,4))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.view.graph_canvas)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.view.after(0, self._initial_sensor_selection)
        self._start_worker()

    def get_view(self):
        return self.view

    def _initial_sensor_selection(self):
        if self.view.calib_sensor_combo.get():
            self.on_calib_sensor_selected(self.view.calib_sensor_combo.get())
        if self.view.ref_sensor_combo.get():
            self.on_ref_sensor_selected(self.view.ref_sensor_combo.get())

    def on_mode_changed(self, mode):
        self.current_mode = mode

    def on_calib_sensor_selected(self, name):
        self.calib_sensor_name = name
        self.calib_sensor = self.core_api.get_sensor(name)
        if self.calib_sensor and self.calib_sensor.profile_data:
            self.calib_profile_data = self.calib_sensor.profile_data
            self.param_info = {p['key']: p for p in self.calib_profile_data.get('parameters', [])}
            self.view.update_params_list(self.calib_profile_data.get('parameters', []))
        else:
            self.param_info = {}
            self.view.update_params_list([])

    def on_ref_sensor_selected(self, name):
        self.ref_sensor_name = name
        if name:
            self.ref_sensor = self.core_api.get_sensor(name)
            if self.ref_sensor and self.ref_sensor.profile_data:
                self.ref_profile_data = self.ref_sensor.profile_data
                self.ref_param_info = {p['key']: p for p in self.ref_profile_data.get('parameters', [])}
            else:
                self.ref_profile_data = None
                self.ref_param_info = {}
        else:
            self.ref_sensor = None
            self.ref_profile_data = None
            self.ref_param_info = {}

    # -------- Фоновый сбор текущих данных --------
    def _start_worker(self):
        if self._worker_thread and self._worker_thread.is_alive():
            return
        self._updating = True
        self._worker_wakeup.clear()
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()
        self._schedule_queue_check()

    def _stop_worker(self):
        self._updating = False
        self._worker_wakeup.set()
        if self._after_id:
            try:
                self.view.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=1)
            self._worker_thread = None

    def _worker_loop(self):
        while self._updating:
            data = self._collect_current_data()
            self._data_queue.put(data)
            self._worker_wakeup.wait(5)
            self._worker_wakeup.clear()

    def _collect_current_data(self):
        result = {}
        if self.calib_sensor and self.calib_sensor.connected and self.calib_profile_data:
            d = {}
            for p in self.calib_profile_data.get("parameters", []):
                addr = p.get("address")
                if addr is None:
                    continue
                try:
                    vals = self.calib_sensor.read_registers(addr, 1)
                    if vals and len(vals) == 1:
                        raw = vals[0]
                        # Calibration workflow should show engineering conversion without saved calibration model.
                        val = convert_parameter_value(raw, p, None)
                        d[p["key"]] = val
                    else:
                        d[p["key"]] = None
                except Exception as e:
                    d[p["key"]] = None
                    self._log_error(f"Read error for {p['key']}: {e}")
            result[self.calib_sensor_name or "Калибруемый"] = d
        if self.ref_sensor and self.ref_sensor.connected and self.ref_profile_data:
            d = {}
            for p in self.ref_profile_data.get("parameters", []):
                addr = p.get("address")
                if addr is None:
                    continue
                try:
                    vals = self.ref_sensor.read_registers(addr, 1)
                    if vals and len(vals) == 1:
                        raw = vals[0]
                        val = convert_parameter_value(raw, p, None)
                        d[p["key"]] = val
                    else:
                        d[p["key"]] = None
                except Exception as e:
                    d[p["key"]] = None
                    self._log_error(f"Read error for ref {p['key']}: {e}")
            result[self.ref_sensor_name or "Эталон"] = d
        return result

    def _schedule_queue_check(self):
        if not self._updating:
            return
        try:
            data = None
            while not self._data_queue.empty():
                data = self._data_queue.get_nowait()
            if data is not None:
                self.view.update_current_sensors_table(data)
        except queue.Empty:
            pass
        self._after_id = self.view.after(1000, self._schedule_queue_check)

    def _log_error(self, msg):
        from utils.utils import log_error
        log_error(f"Calibration: {msg}")

    def _param_def(self, param_key, ref=False):
        param_map = self.ref_param_info if ref else self.param_info
        return param_map.get(param_key, {"key": param_key})

    def _convert_raw_value(self, raw_value, param_key, ref=False):
        if raw_value is None:
            return None
        return convert_parameter_value(raw_value, self._param_def(param_key, ref=ref), None)

    # -------- Сбор точки --------
    def on_add_point(self, mode, calib_name, ref_name, selected_params, num_samples):
        if self._collecting:
            self.view.show_error(self.tr("collect_in_progress"))
            self.view.on_add_point_finished()
            return
        if not self.calib_sensor or not self.calib_sensor.connected:
            self.view.show_error(self.tr("calib_sensor_not_connected"))
            self.view.on_add_point_finished()
            return
        if mode == 'ref' and (not self.ref_sensor or not self.ref_sensor.connected):
            self.view.show_error(self.tr("ref_sensor_not_connected"))
            self.view.on_add_point_finished()
            return

        self._collecting = True
        timestamp = datetime.datetime.now().strftime("%H:%M")
        if mode == 'lab':
            self.engine.collect_point(
                self.calib_sensor, selected_params, num_samples,
                callback=lambda raw_stats, ref_stats: self._on_lab_collected(raw_stats, timestamp, selected_params)
            )
        else:
            self.engine.collect_point(
                self.calib_sensor, selected_params, num_samples,
                ref_sensor=self.ref_sensor,
                ref_profile_data=self.ref_profile_data,
                callback=lambda raw_stats, ref_stats: self._on_ref_collected(raw_stats, ref_stats, timestamp, selected_params)
            )

    def _on_lab_collected(self, raw_stats, timestamp, selected_params):
        self._collecting = False
        if raw_stats is None:
            self.view.show_error(self.tr("collect_failed"))
            self.view.on_add_point_finished()
            return
        RefValueDialog(self.view, selected_params, raw_stats,
                       lambda rstats, ref_vals: self._save_lab_point(rstats, ref_vals, timestamp, selected_params),
                       self.tr)

    def _save_lab_point(self, raw_stats, ref_values, timestamp, selected_params):
        point = {
            'timestamp': timestamp,
            'selected_params': selected_params,
            'raw_stats': raw_stats,
            'ref_values': ref_values
        }
        self.points.append(point)
        self.view.update_points_table(self.points, self.param_info, self.ref_param_info)
        self.view.enable_export(True)
        self.view.enable_calc_save(True)
        self.view.on_add_point_finished()
        self._update_graph()

    def _on_ref_collected(self, raw_stats, ref_stats, timestamp, selected_params):
        self._collecting = False
        if raw_stats is None or ref_stats is None:
            self.view.show_error(self.tr("collect_failed"))
            self.view.on_add_point_finished()
            return
        point = {
            'timestamp': timestamp,
            'selected_params': selected_params,
            'raw_stats': raw_stats,
            'ref_stats': ref_stats
        }
        self.points.append(point)
        self.view.update_points_table(self.points, self.param_info, self.ref_param_info)
        self.view.enable_export(True)
        self.view.enable_calc_save(True)
        self.view.on_add_point_finished()
        self._update_graph()

    def on_remove_point(self, idx):
        if 0 <= idx < len(self.points):
            del self.points[idx]
            self.view.update_points_table(self.points, self.param_info, self.ref_param_info)
            if not self.points:
                self.view.enable_calc_save(False)
                self.view.enable_export(False)
            else:
                self.view.enable_calc_save(True)
                self.view.enable_export(True)
            self._update_graph()

    # -------- Регрессия и графики --------
    def on_calculate_regression(self, param, model_type):
        if not self.points:
            self.view.show_error(self.tr("no_data"))
            return
        X, y = self._get_regression_data(param)
        if len(X) < 2:
            self.view.show_warning(self.tr("not_enough_points").format(self.tr(param)))
            return
        result = self.engine.calculate_regression(X, y, model_type)
        if result is None:
            self.view.show_warning(self.tr("regression_failed"))
            return
        self.calibration_results[param] = result
        RegressionResultDialog(self.view, param, result, self.tr)
        self._update_graph()

    def _get_regression_data(self, param):
        X = []
        y = []
        for p in self.points:
            raw_median = p['raw_stats'].get(param, {}).get('median')
            if raw_median is not None:
                conv_median = self._convert_raw_value(raw_median, param, ref=False)
                if self.current_mode == 'lab':
                    ref_val = p.get('ref_values', {}).get(param)
                    if ref_val is not None:
                        X.append(conv_median)
                        y.append(ref_val)
                else:
                    ref_median = p.get('ref_stats', {}).get(param, {}).get('median')
                    if ref_median is not None:
                        conv_ref = self._convert_raw_value(ref_median, param, ref=True)
                        X.append(conv_median)
                        y.append(conv_ref)
        return X, y

    def on_graph_type_changed(self, graph_type):
        self.current_graph_type = graph_type
        self._update_graph()

    def on_graph_param_selected(self, param_key):
        self.current_graph_param = param_key
        self._update_graph()

    def _update_graph(self):
        if not self.current_graph_param:
            return
        if self.current_graph_type == 'points':
            self._draw_points_graph(self.current_graph_param)
        else:
            if self.calibration_results.get(self.current_graph_param):
                X, y = self._get_regression_data(self.current_graph_param)
                if X and y:
                    self._update_graph_with_regression(self.current_graph_param, X, y, self.calibration_results[self.current_graph_param])
                else:
                    self.ax.clear()
                    self.ax.text(0.5, 0.5, self.tr("no_regression_data"), ha='center', va='center')
                    self.canvas.draw()
            else:
                self.ax.clear()
                self.ax.text(0.5, 0.5, self.tr("calculate_regression_first"), ha='center', va='center')
                self.canvas.draw()

    def _draw_points_graph(self, param_key):
        if not self.points:
            self.ax.clear()
            self.ax.text(0.5, 0.5, self.tr("no_points"), ha='center', va='center')
            self.canvas.draw()
            return

        calib_vals = []
        ref_vals = []
        for i, point in enumerate(self.points):
            raw_median = point['raw_stats'].get(param_key, {}).get('median')
            if raw_median is not None:
                calib_vals.append(self._convert_raw_value(raw_median, param_key, ref=False))
            else:
                calib_vals.append(None)

            if self.current_mode == 'lab':
                ref_val = point.get('ref_values', {}).get(param_key)
                if ref_val is not None:
                    ref_vals.append(ref_val)
                else:
                    ref_vals.append(None)
            else:
                ref_median = point.get('ref_stats', {}).get(param_key, {}).get('median')
                if ref_median is not None:
                    ref_vals.append(self._convert_raw_value(ref_median, param_key, ref=True))
                else:
                    ref_vals.append(None)

        x = list(range(1, len(self.points)+1))
        self.ax.clear()
        self.ax.plot(x, calib_vals, marker='o', linestyle='-', color='blue', label=self.tr("calib_median"))
        self.ax.plot(x, ref_vals, marker='s', linestyle='--', color='green', label=self.tr("ref_value"))
        self.ax.set_xlabel(self.tr("point_num"))
        self.ax.set_ylabel(self.tr("value"))
        self.ax.set_title(self.tr(param_key))
        self.ax.grid(True)
        self.ax.legend()
        self.canvas.draw()

    def _update_graph_with_regression(self, param_key, X, y, result):
        self.ax.clear()
        self.ax.scatter(X, y, color='blue', label=self.tr("points"))
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
        self.ax.plot(X_line, y_line, color='red', label=label)
        self.ax.set_xlabel(self.tr("calib_value"))
        self.ax.set_ylabel(self.tr("ref_value"))
        self.ax.set_title(self.tr(param_key))
        self.ax.legend()
        self.ax.grid(True)
        self.canvas.draw()

    def on_show_raw_graph(self, point_idx, param, sensor_type):
        if point_idx < 0 or point_idx >= len(self.points):
            return
        point = self.points[point_idx]
        if sensor_type == 'calib':
            raw_stats = point['raw_stats'].get(param)
            is_ref = False
        else:
            raw_stats = point.get('ref_stats', {}).get(param)
            is_ref = True
        if raw_stats and raw_stats.get('raw'):
            raw_vals = [self._convert_raw_value(v, param, ref=is_ref) if v is not None else None for v in raw_stats['raw']]
            median = self._convert_raw_value(raw_stats.get('median'), param, ref=is_ref)
            GraphDialog(self.view, f"{self.tr(param)} - {self.tr('raw_data')} ({self.tr(sensor_type)})", raw_vals, median, self.tr)

    def open_system_registers(self):
        if not self.calib_sensor:
            self.view.show_message(self.tr("select_sensor_first"))
            return
        profile = self.calib_sensor.profile_data
        if not profile:
            self.view.show_message(self.tr("no_profile"))
            return
        from .system_registers_dialog import SystemRegistersDialog
        SystemRegistersDialog(self.view, self.core_api, profile, self.tr, self.calib_sensor)

    def on_save_calibration(self):
        if not self.calibration_results:
            self.view.show_error(self.tr("no_regression"))
            return
        SaveCalibrationDialog(self.view, self.core_api, self.calibration_results, self.tr)

    def on_export_csv(self):
        if not self.points:
            self.view.show_error(self.tr("no_data"))
            return
        ExportCsvDialog(self.view, self.points, self.param_info, self.ref_param_info, self.current_mode, self.tr)

    def destroy(self):
        self._stop_worker()
        self.engine.stop()
        if self.view and self.view.winfo_exists():
            self.view.destroy()

    def on_sensors_changed(self):
        sensors = self.core_api.list_sensors()
        self.view.update_sensor_lists(sensors)

        calib_name = self.view.calib_sensor_combo.get()
        if calib_name:
            self.on_calib_sensor_selected(calib_name)
        else:
            self.calib_sensor_name = None
            self.calib_sensor = None
            self.calib_profile_data = None
            self.param_info = {}
            self.view.update_params_list([])

        ref_name = self.view.ref_sensor_combo.get()
        if ref_name:
            self.on_ref_sensor_selected(ref_name)
        else:
            self.ref_sensor_name = None
            self.ref_sensor = None
            self.ref_profile_data = None
            self.ref_param_info = {}

    def on_show(self):
        self._start_worker()

    def on_hide(self):
        self._stop_worker()
