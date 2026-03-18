# modules/monitor/engine.py
# Расположение: modules/monitor/engine.py
# Описание: Логика мониторинга – чтение данных с датчика.

import threading
import time
from utils.utils import log_error

class MonitorEngine:
    def __init__(self, core_api):
        self.core_api = core_api
        self.running = False
        self.thread = None
        self.callback = None
        self.error_count = 0

    def start(self, callback):
        self.callback = callback
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)

    def _run(self):
        while self.running:
            sensor = self.core_api.sensor
            profile_data = self.core_api.get_current_profile_data()
            if sensor and sensor.connected and profile_data:
                # Пытаемся читать все параметры одним запросом, если адреса последовательны
                params = profile_data.get("parameters", [])
                if params and len(params) > 1:
                    # Проверяем, идут ли адреса подряд
                    addrs = [p["address"] for p in params]
                    if all(addrs[i] == addrs[0] + i for i in range(len(addrs))):
                        # Читаем группой
                        vals = sensor.read_registers(addrs[0], len(addrs))
                        if vals and len(vals) == len(addrs):
                            data = {}
                            for i, p in enumerate(params):
                                raw = vals[i]
                                val = raw * p.get("factor", 1) + p.get("offset", 0)
                                data[p["key"]] = val
                            if data and self.callback:
                                self.callback(data)
                            self.error_count = 0
                        else:
                            self.error_count += 1
                            if self.error_count == 1:
                                log_error("Monitor: group read failed")
                    else:
                        # Читаем по одному
                        data = {}
                        success = True
                        for p in params:
                            addr = p["address"]
                            vals = sensor.read_registers(addr, 1)
                            if vals and len(vals) == 1:
                                raw = vals[0]
                                val = raw * p.get("factor", 1) + p.get("offset", 0)
                                data[p["key"]] = val
                            else:
                                success = False
                                self.error_count += 1
                                if self.error_count == 1:
                                    log_error(f"Monitor: failed to read addr {addr}")
                        if success and data:
                            self.error_count = 0
                            if self.callback:
                                self.callback(data)
                else:
                    # Один параметр
                    p = params[0]
                    addr = p["address"]
                    vals = sensor.read_registers(addr, 1)
                    if vals and len(vals) == 1:
                        raw = vals[0]
                        val = raw * p.get("factor", 1) + p.get("offset", 0)
                        if self.callback:
                            self.callback({p["key"]: val})
                        self.error_count = 0
                    else:
                        self.error_count += 1
                        if self.error_count == 1:
                            log_error(f"Monitor: failed to read addr {addr}")
            else:
                if not sensor or not sensor.connected:
                    log_error("Monitor: sensor not connected")
                if not profile_data:
                    log_error("Monitor: no profile selected")
                if self.callback:
                    self.callback(None)  # сигнал о потере связи
            time.sleep(2)