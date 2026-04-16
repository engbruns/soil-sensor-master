from __future__ import annotations

import threading
from typing import List, Optional

import serial

from utils.utils import calculate_crc, log_error


class ModbusBus:
    """Shared serial bus for multiple Modbus devices on the same COM/baudrate."""

    def __init__(self, port: str, baudrate: int, timeout: float = 1.5):
        self.port = port
        self.baudrate = int(baudrate)
        self.timeout = float(timeout)
        self._ser: Optional[serial.Serial] = None
        self._lock = threading.RLock()

    @property
    def is_open(self) -> bool:
        return bool(self._ser and self._ser.is_open)

    def connect(self) -> bool:
        with self._lock:
            if self.is_open:
                return True
            try:
                self._ser = serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    bytesize=8,
                    parity="N",
                    stopbits=1,
                    timeout=self.timeout,
                    write_timeout=self.timeout,
                )
                return True
            except Exception as exc:
                log_error(f"Bus connect failed {self.port}@{self.baudrate}: {exc}")
                self._ser = None
                return False

    def disconnect(self) -> None:
        with self._lock:
            if self._ser and self._ser.is_open:
                try:
                    self._ser.close()
                except Exception as exc:
                    log_error(f"Bus close failed {self.port}: {exc}")
            self._ser = None

    def _transaction(self, req_payload: bytes, expected_len: int, retries: int = 3) -> Optional[bytes]:
        with self._lock:
            if not self.is_open and not self.connect():
                return None

            assert self._ser is not None
            for attempt in range(retries):
                try:
                    self._ser.reset_input_buffer()
                    frame = bytearray(req_payload)
                    crc = calculate_crc(frame)
                    frame.extend([crc & 0xFF, (crc >> 8) & 0xFF])
                    self._ser.write(frame)

                    resp = self._ser.read(expected_len)
                    if len(resp) < expected_len:
                        log_error(
                            f"Bus short response on {self.port}, attempt {attempt + 1}: {len(resp)} < {expected_len}"
                        )
                        continue

                    recv_crc = (resp[-1] << 8) | resp[-2]
                    calc_crc = calculate_crc(resp[:-2])
                    if recv_crc != calc_crc:
                        log_error(f"Bus CRC mismatch on {self.port}, attempt {attempt + 1}")
                        continue

                    return bytes(resp)
                except Exception as exc:
                    log_error(f"Bus transaction error on {self.port}: {exc}")
            return None

    def read_holding_registers(
        self,
        slave_id: int,
        start_addr: int,
        count: int,
        function_code: int = 0x03,
    ) -> Optional[List[int]]:
        payload = bytes(
            [
                slave_id,
                function_code,
                (start_addr >> 8) & 0xFF,
                start_addr & 0xFF,
                (count >> 8) & 0xFF,
                count & 0xFF,
            ]
        )
        expected = 3 + 2 * count + 2
        resp = self._transaction(payload, expected_len=expected)
        if not resp:
            return None

        if resp[0] != slave_id:
            log_error(f"Bus read wrong slave id: got {resp[0]}, expected {slave_id}")
            return None

        if resp[1] == (function_code | 0x80):
            code = resp[2] if len(resp) > 2 else -1
            log_error(f"Modbus exception response code={code}")
            return None

        if resp[1] != function_code:
            log_error(f"Bus read wrong function code: got {resp[1]}, expected {function_code}")
            return None

        expected_byte_count = 2 * count
        if resp[2] != expected_byte_count:
            log_error(f"Bus wrong byte count: got {resp[2]}, expected {expected_byte_count}")
            return None

        data = resp[3 : 3 + expected_byte_count]
        return [(data[i] << 8) | data[i + 1] for i in range(0, len(data), 2)]

    def write_single_register(
        self,
        slave_id: int,
        reg_addr: int,
        value: int,
        function_code: int = 0x06,
    ) -> bool:
        payload = bytes(
            [
                slave_id,
                function_code,
                (reg_addr >> 8) & 0xFF,
                reg_addr & 0xFF,
                (value >> 8) & 0xFF,
                value & 0xFF,
            ]
        )
        resp = self._transaction(payload, expected_len=8, retries=2)
        if not resp:
            return False

        if resp[0] != slave_id or resp[1] != function_code:
            log_error(f"Bus write wrong response header: slave={resp[0]} fn={resp[1]}")
            return False

        if resp[:6] != payload[:6]:
            log_error("Bus write echo mismatch")
            return False

        return True

    def ping(self, slave_id: int) -> bool:
        values = self.read_holding_registers(slave_id, start_addr=0, count=1)
        return bool(values and len(values) == 1)
