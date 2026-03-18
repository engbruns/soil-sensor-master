# core/constants.py
# Расположение: core/constants.py
# Описание: Глобальные константы, используемые модулями (коэффициенты, адресные подсказки).

STANDARD_PARAMS = {
    "temperature": {"factor": 0.1, "offset": 0, "unit_key": "unit_temperature"},
    "humidity": {"factor": 0.1, "offset": 0, "unit_key": "unit_percent"},
    "ph": {"factor": 0.01, "offset": 0, "unit_key": ""},
    "ec": {"factor": 1, "offset": 0, "unit_key": "unit_ec"},
    "nitrogen": {"factor": 1, "offset": 0, "unit_key": "unit_mgkg"},
    "phosphorus": {"factor": 1, "offset": 0, "unit_key": "unit_mgkg"},
    "potassium": {"factor": 1, "offset": 0, "unit_key": "unit_mgkg"},
    "salinity": {"factor": 1, "offset": 0, "unit_key": ""},
    "tds": {"factor": 1, "offset": 0, "unit_key": "unit_ppm"},
    "device_address": {"factor": 1, "offset": 0, "unit_key": ""},
    "firmware": {"factor": 1, "offset": 0, "unit_key": ""}
}

# Адресные подсказки для сканера (адрес -> список возможных параметров)
ADDRESS_HINTS = {
    0x00: ["humidity"],
    0x01: ["temperature"],
    0x02: ["ec"],
    0x03: ["ph"],
    0x04: ["nitrogen"],
    0x05: ["phosphorus"],
    0x06: ["potassium"],
    0x07: ["firmware", "device_address"],
    0x08: ["baudrate", "firmware"],
    0x0B: ["error_status"],
    0x0C: ["device_address"],
    0x12: ["humidity"],
    0x13: ["temperature"],
    0x15: ["ec"],
    0x1E: ["nitrogen"],
    0x1F: ["phosphorus"],
    0x20: ["potassium"],
}