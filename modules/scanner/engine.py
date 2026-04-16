# modules/scanner/engine.py
# Расположение: modules/scanner/engine.py
# Описание: Движок сканера – сбор данных в фоновом потоке.

import threading
import time
from utils.utils import safe_median, log_error

class ScannerEngine:
    def __init__(self, core_api):
        self.core_api = core_api
        self.running = False
        self.thread = None
        self.progress_callback = None
        self.finished_callback = None

    def start_collect(self, sensor, addresses, num_cycles, progress_callback, finished_callback):
        """
        Запускает сбор данных.
        sensor: объект SoilSensor (уже подключён)
        addresses: список целых чисел (адресов)
        num_cycles: количество циклов
        progress_callback: функция(percent)
        finished_callback: функция(snapshot, success)
        """
        self.running = True
        self.progress_callback = progress_callback
        self.finished_callback = finished_callback
        self.thread = threading.Thread(target=self._collect_loop, args=(sensor, addresses, num_cycles), daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)

    def _collect_loop(self, sensor, addresses, num_cycles):
        if not sensor or not sensor.connected:
            log_error("Scanner: sensor not connected")
            if self.finished_callback:
                self.finished_callback([], False)
            return

        raw_data = {addr: [] for addr in addresses}
        total_cycles = num_cycles

        for cycle in range(total_cycles):
            if not self.running:
                break
            for addr in addresses:
                if not self.running:
                    break
                try:
                    vals = sensor.read_registers(addr, 1)
                    if vals and len(vals) == 1:
                        raw_data[addr].append(vals[0])
                    else:
                        raw_data[addr].append(None)
                except Exception as e:
                    log_error(f"Scanner: error reading addr {addr}: {e}")
                    raw_data[addr].append(None)
                time.sleep(0.05)

            if self.progress_callback:
                progress = int((cycle + 1) / total_cycles * 100)
                self.progress_callback(progress)

            if cycle < total_cycles - 1 and self.running:
                time.sleep(2)

        if not self.running:
            if self.finished_callback:
                self.finished_callback([], False)
            return

        snapshot = []
        for addr in addresses:
            values = [v for v in raw_data[addr] if v is not None]
            if values:
                median = safe_median(values)
                snapshot.append({
                    "addr_hex": f"0x{addr:02X}",
                    "addr_dec": addr,
                    "value_dec": median,
                    "value_hex": f"{int(median):04X}" if median is not None else "---",
                    "raw_values": raw_data[addr]
                })
            else:
                snapshot.append({
                    "addr_hex": f"0x{addr:02X}",
                    "addr_dec": addr,
                    "value_dec": None,
                    "value_hex": "---",
                    "raw_values": raw_data[addr]
                })

        if self.finished_callback:
            self.finished_callback(snapshot, True)
        self.running = False
