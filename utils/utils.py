import logging
import os
import statistics

from config import LOGS_DIR


LOG_FILE = os.path.join(LOGS_DIR, "error.log")
LOGGER = logging.getLogger("soilsens")
LOGGER.setLevel(logging.ERROR)
LOGGER.propagate = False

if not LOGGER.handlers:
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        file_handler.setLevel(logging.ERROR)
        file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        LOGGER.addHandler(file_handler)
    except Exception:
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.ERROR)
        stream_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        LOGGER.addHandler(stream_handler)


def log_error(msg):
    """Writes an error message to logger."""
    LOGGER.error(msg)


def safe_median(data):
    """Safely calculates median ignoring None values."""
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
    """Calculates CRC16 for Modbus RTU payload."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc
