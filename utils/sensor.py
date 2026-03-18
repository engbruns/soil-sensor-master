# utils/sensor.py
# Расположение: utils/sensor.py
# Описание: Класс SoilSensor для работы с Modbus RTU через последовательный порт.

# utils/sensor.py
import serial
from .utils import calculate_crc, log_error

class SoilSensor:
    def __init__(self, port, baudrate, slave_id=1, timeout=2):
        self.port = port
        self.baudrate = baudrate
        self.slave_id = slave_id
        self.timeout = timeout
        self.ser = None
        self.connected = False

    def connect(self):
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=8,
                parity='N',
                stopbits=1,
                timeout=self.timeout,
                write_timeout=self.timeout
            )
            self.connected = True
            return True
        except Exception as e:
            log_error(f"Connect error: {e}")
            self.connected = False
            return False

    def disconnect(self):
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except Exception as e:
                log_error(f"Disconnect error: {e}")
        self.connected = False

    def read_registers(self, start_addr, num_regs, function_code=0x03):
        if not self.connected or not self.ser:
            return None
        try:
            self.ser.reset_input_buffer()
            req = bytearray([self.slave_id, function_code,
                             (start_addr >> 8) & 0xFF, start_addr & 0xFF,
                             (num_regs >> 8) & 0xFF, num_regs & 0xFF])
            crc = calculate_crc(req)
            req.extend([crc & 0xFF, (crc >> 8) & 0xFF])
            self.ser.write(req)
            expected = 3 + 2 * num_regs + 2
            resp = self.ser.read(expected)
            if len(resp) < expected:
                log_error(f"Short response: {len(resp)} < {expected}")
                return None
            recv_crc = (resp[-1] << 8) | resp[-2]
            calc_crc = calculate_crc(resp[:-2])
            if recv_crc != calc_crc:
                log_error("CRC mismatch")
                return None
            data = resp[3:3+2*num_regs]
            return [(data[i] << 8) | data[i+1] for i in range(0, len(data), 2)]
        except Exception as e:
            log_error(f"Read error: {e}")
            return None

    def write_register(self, reg_addr, value, function_code=0x06):
        """Записывает одно 16-битное значение в регистр."""
        if not self.connected or not self.ser:
            return False
        try:
            req = bytearray([self.slave_id, function_code,
                             (reg_addr >> 8) & 0xFF, reg_addr & 0xFF,
                             (value >> 8) & 0xFF, value & 0xFF])
            crc = calculate_crc(req)
            req.extend([crc & 0xFF, (crc >> 8) & 0xFF])
            self.ser.write(req)
            # Ожидаем ответ (8 байт: адрес, функция, регистр, значение, CRC)
            resp = self.ser.read(8)
            if len(resp) < 8:
                log_error(f"Write short response: {len(resp)}")
                return False
            # Проверка CRC
            recv_crc = (resp[-1] << 8) | resp[-2]
            calc_crc = calculate_crc(resp[:-2])
            if recv_crc != calc_crc:
                log_error("Write CRC mismatch")
                return False
            # Можно дополнительно проверить, что ответ соответствует запросу
            return True
        except Exception as e:
            log_error(f"Write error: {e}")
            return False