# modules/calibration/engine.py
# Расположение: modules/calibration/engine.py
# Описание: Движок сбора данных для калибровки.

import threading
import time
from sklearn.pipeline import make_pipeline
from utils.utils import safe_median, log_error

class CalibrationEngine:
    def __init__(self, core_api):
        self.core_api = core_api
        self._stop_flag = False
        self.thread = None

    def collect_point(self, sensor, selected_params, num_samples, ref_sensor=None, ref_profile_data=None, callback=None):
        """
        Запускает сбор данных в отдельном потоке.
        sensor: объект SoilSensor калибруемого датчика
        selected_params: список ключей параметров
        num_samples: количество считываний
        ref_sensor: эталонный датчик (опционально)
        ref_profile_data: профиль эталонного датчика (опционально)
        callback: функция(raw_stats, ref_stats)
        """
        if not sensor or not sensor.connected:
            log_error("Calibration: main sensor not connected")
            if callback:
                callback(None, None)
            return

        # New collection session starts with a cleared stop flag.
        self._stop_flag = False

        def _collect():
            raw_data = {param: [] for param in selected_params}
            ref_data = {param: [] for param in selected_params} if ref_sensor else None

            for _ in range(num_samples):
                if self._stop_flag:
                    break
                for param in selected_params:
                    if self._stop_flag:
                        break
                    addr = self._get_address(param, sensor.profile_data)
                    if addr is not None:
                        vals = sensor.read_registers(addr, 1)
                        if vals and len(vals) == 1:
                            raw_data[param].append(vals[0])
                        else:
                            raw_data[param].append(None)
                if ref_sensor and ref_sensor.connected and not self._stop_flag and ref_profile_data:
                    for param in selected_params:
                        if self._stop_flag:
                            break
                        addr = self._get_address(param, ref_profile_data)
                        if addr is not None:
                            vals = ref_sensor.read_registers(addr, 1)
                            if vals and len(vals) == 1:
                                ref_data[param].append(vals[0])
                            else:
                                ref_data[param].append(None)
                time.sleep(0.5)

            if self._stop_flag:
                if callback:
                    callback(None, None)
                return

            raw_stats = {}
            for param in selected_params:
                values = [v for v in raw_data[param] if v is not None]
                if values:
                    raw_stats[param] = {
                        'median': safe_median(values),
                        'min': min(values),
                        'max': max(values),
                        'avg': sum(values)/len(values),
                        'raw': raw_data[param]
                    }
                else:
                    raw_stats[param] = None

            ref_stats = None
            if ref_sensor and ref_profile_data:
                ref_stats = {}
                for param in selected_params:
                    values = [v for v in ref_data[param] if v is not None]
                    if values:
                        ref_stats[param] = {
                            'median': safe_median(values),
                            'min': min(values),
                            'max': max(values),
                            'avg': sum(values)/len(values),
                            'raw': ref_data[param]
                        }
                    else:
                        ref_stats[param] = None

            if callback:
                callback(raw_stats, ref_stats)

        self.thread = threading.Thread(target=_collect, daemon=True)
        self.thread.start()

    def _get_address(self, param_key, profile_data):
        if not profile_data:
            return None
        for p in profile_data.get('parameters', []):
            if p['key'] == param_key:
                return p['address']
        return None

    def stop(self):
        self._stop_flag = True
        if self.thread:
            self.thread.join(timeout=1)

    def calculate_regression(self, X, y, model_type='linear'):
        import numpy as np
        from sklearn.linear_model import LinearRegression
        from sklearn.preprocessing import PolynomialFeatures
               
        if len(X) < 2:
            return None
        Xnp = np.array(X).reshape(-1,1)
        ynp = np.array(y)
        if model_type == 'linear':
            model = LinearRegression()
            model.fit(Xnp, ynp)
            r2 = model.score(Xnp, ynp)
            return {
                'model': 'linear',
                'coefficients': [model.coef_[0], model.intercept_],
                'r2': r2
            }
        elif model_type == 'poly2':
            poly = PolynomialFeatures(degree=2)
            X_poly = poly.fit_transform(Xnp)
            model = LinearRegression()
            model.fit(X_poly, ynp)
            r2 = model.score(X_poly, ynp)
            return {
                'model': 'poly2',
                'coefficients': [model.intercept_] + model.coef_[1:].tolist(),
                'r2': r2
            }
        elif model_type == 'poly3':
            poly = PolynomialFeatures(degree=3)
            X_poly = poly.fit_transform(Xnp)
            model = LinearRegression()
            model.fit(X_poly, ynp)
            r2 = model.score(X_poly, ynp)
            return {
                'model': 'poly3',
                'coefficients': [model.intercept_] + model.coef_[1:].tolist(),
                'r2': r2
            }
        else:
            return None
