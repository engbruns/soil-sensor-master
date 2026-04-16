# utils/sensor.py
# Serial layer for real and simulated soil sensors.

from __future__ import annotations

import random
import threading

import serial

from .utils import calculate_crc, log_error


class SoilSensor:
    def __init__(self, port, baudrate, slave_id=1, timeout=2, name=""):
        self.port = port
        self.baudrate = baudrate
        self.slave_id = slave_id
        self.timeout = timeout
        self.ser = None
        self.connected = False
        self.profile_data = None
        self.name = name
        self._io_lock = threading.RLock()

    def connect(self):
        with self._io_lock:
            try:
                self.ser = serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    bytesize=8,
                    parity='N',
                    stopbits=1,
                    timeout=self.timeout,
                    write_timeout=self.timeout,
                )
                self.connected = True
                return True
            except Exception as e:
                log_error(f"Connect error: {e}")
                self.connected = False
                return False

    def disconnect(self):
        with self._io_lock:
            if self.ser and self.ser.is_open:
                try:
                    self.ser.close()
                except Exception as e:
                    log_error(f"Disconnect error: {e}")
            self.connected = False

    def ping(self, retries=1):
        """Fast connectivity check by reading register 0x0000."""
        with self._io_lock:
            if not self.connected or not self.ser:
                return False

            for _ in range(retries):
                try:
                    self.ser.reset_input_buffer()
                    req = bytearray([self.slave_id, 0x03, 0x00, 0x00, 0x00, 0x01])
                    crc = calculate_crc(req)
                    req.extend([crc & 0xFF, (crc >> 8) & 0xFF])
                    self.ser.write(req)

                    resp = self.ser.read(7)
                    if len(resp) < 7:
                        continue

                    recv_crc = (resp[-1] << 8) | resp[-2]
                    calc_crc = calculate_crc(resp[:-2])
                    if recv_crc != calc_crc:
                        continue

                    if resp[0] == self.slave_id and resp[1] == 0x03 and resp[2] == 0x02:
                        return True
                except Exception as e:
                    log_error(f"Ping error: {e}")
            return False

    def read_registers(self, start_addr, num_regs, function_code=0x03):
        with self._io_lock:
            if not self.connected or not self.ser:
                return None

            for attempt in range(3):
                try:
                    self.ser.reset_input_buffer()
                    req = bytearray(
                        [
                            self.slave_id,
                            function_code,
                            (start_addr >> 8) & 0xFF,
                            start_addr & 0xFF,
                            (num_regs >> 8) & 0xFF,
                            num_regs & 0xFF,
                        ]
                    )
                    crc = calculate_crc(req)
                    req.extend([crc & 0xFF, (crc >> 8) & 0xFF])
                    self.ser.write(req)

                    expected = 3 + 2 * num_regs + 2
                    resp = self.ser.read(expected)
                    if len(resp) < expected:
                        log_error(f"Short response: {len(resp)} < {expected}")
                        continue

                    if resp[0] != self.slave_id:
                        log_error(f"Unexpected slave id {resp[0]} (expected {self.slave_id})")
                        continue

                    if resp[1] == (function_code | 0x80):
                        log_error(f"Modbus exception response code={resp[2] if len(resp) > 2 else 'unknown'}")
                        continue

                    if resp[1] != function_code:
                        log_error(f"Unexpected function code {resp[1]} (expected {function_code})")
                        continue

                    expected_byte_count = 2 * num_regs
                    if resp[2] != expected_byte_count:
                        log_error(
                            f"Unexpected byte count {resp[2]} (expected {expected_byte_count}), attempt {attempt + 1}"
                        )
                        continue

                    recv_crc = (resp[-1] << 8) | resp[-2]
                    calc_crc = calculate_crc(resp[:-2])
                    if recv_crc != calc_crc:
                        log_error(f"CRC mismatch (attempt {attempt + 1})")
                        continue

                    data = resp[3 : 3 + expected_byte_count]
                    return [(data[i] << 8) | data[i + 1] for i in range(0, len(data), 2)]
                except Exception as e:
                    log_error(f"Read error: {e}")
            return None

    def write_register(self, reg_addr, value, function_code=0x06):
        with self._io_lock:
            if not self.connected or not self.ser:
                return False

            for attempt in range(2):
                try:
                    req = bytearray(
                        [
                            self.slave_id,
                            function_code,
                            (reg_addr >> 8) & 0xFF,
                            reg_addr & 0xFF,
                            (value >> 8) & 0xFF,
                            value & 0xFF,
                        ]
                    )
                    crc = calculate_crc(req)
                    req.extend([crc & 0xFF, (crc >> 8) & 0xFF])
                    self.ser.write(req)

                    resp = self.ser.read(8)
                    if len(resp) < 8:
                        log_error(f"Write short response (attempt {attempt + 1})")
                        continue

                    if resp[0] != self.slave_id or resp[1] != function_code:
                        log_error(f"Write unexpected header slave={resp[0]} fn={resp[1]} (attempt {attempt + 1})")
                        continue

                    if resp[:6] != req[:6]:
                        log_error(f"Write echo mismatch (attempt {attempt + 1})")
                        continue

                    recv_crc = (resp[-1] << 8) | resp[-2]
                    calc_crc = calculate_crc(resp[:-2])
                    if recv_crc != calc_crc:
                        log_error(f"Write CRC mismatch (attempt {attempt + 1})")
                        continue

                    return True
                except Exception as e:
                    log_error(f"Write error: {e}")
            return False


class SimulatedSoilSensor:
    """Simple random simulator for UI testing without hardware."""

    def __init__(self, name, profile_data):
        self.name = name
        self.profile_data = profile_data
        self.connected = True
        self.port = f"sim:{name}"
        self.baudrate = 9600
        self.slave_id = 1
        self._random = random

    def connect(self):
        return True

    def disconnect(self):
        self.connected = False

    def ping(self, retries=1):
        return True

    def read_registers(self, start_addr, num_regs, function_code=0x03):
        if not self.connected:
            return None
        return [self._random.randint(0, 1000) for _ in range(num_regs)]

    def write_register(self, reg_addr, value, function_code=0x06):
        return True
