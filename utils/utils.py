# utils/utils.py
# Расположение: utils/utils.py
# Описание: Вспомогательные функции: вычисление CRC, медиана, логирование ошибок.

import statistics
import logging
import os

ERROR_LOG_FILE = os.path.join(os.path.dirname(__file__), "..", "logs", "error.log")
os.makedirs(os.path.dirname(ERROR_LOG_FILE), exist_ok=True)

logging.basicConfig(
    filename=ERROR_LOG_FILE,
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def log_error(msg):
    """Записывает сообщение об ошибке в лог-файл."""
    logging.error(msg)

def safe_median(data):
    """Безопасно вычисляет медиану, игнорируя None."""
    if not data:
        return None
    clean = [x for x in data if isinstance(x, (int, float))]
    if not clean:
        return None
    try:
        return statistics.median(clean)
    except Exception as e:
        log_error(f"Median calculation error: {e}")
        return None

def calculate_crc(data):
    """Вычисляет CRC16 для Modbus RTU."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc