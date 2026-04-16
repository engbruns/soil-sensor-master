from __future__ import annotations

from typing import Dict, Iterable, List

PRIMARY_PARAM_ORDER = [
    "temperature",
    "humidity",
    "ph",
    "ec",
    "nitrogen",
    "phosphorus",
    "potassium",
    "salinity",
    "tds",
]

_PARAM_LABELS: Dict[str, Dict[str, str]] = {
    "ru": {
        "temperature": "Температура",
        "humidity": "Влажность",
        "ph": "pH",
        "ec": "EC",
        "nitrogen": "Азот (N)",
        "phosphorus": "Фосфор (P)",
        "potassium": "Калий (K)",
        "salinity": "Соленость",
        "tds": "TDS",
        "device_address": "Адрес устройства",
        "firmware": "Прошивка",
        "baudrate": "Скорость",
        "error_status": "Статус ошибки",
    },
    "en": {
        "temperature": "Temperature",
        "humidity": "Humidity",
        "ph": "pH",
        "ec": "EC",
        "nitrogen": "Nitrogen (N)",
        "phosphorus": "Phosphorus (P)",
        "potassium": "Potassium (K)",
        "salinity": "Salinity",
        "tds": "TDS",
        "device_address": "Device address",
        "firmware": "Firmware",
        "baudrate": "Baud rate",
        "error_status": "Error status",
    },
    "zh": {
        "temperature": "温度",
        "humidity": "湿度",
        "ph": "pH",
        "ec": "电导率",
        "nitrogen": "氮 (N)",
        "phosphorus": "磷 (P)",
        "potassium": "钾 (K)",
        "salinity": "盐度",
        "tds": "TDS",
        "device_address": "设备地址",
        "firmware": "固件",
        "baudrate": "波特率",
        "error_status": "错误状态",
    },
}


def normalize_language(language: str) -> str:
    return language if language in _PARAM_LABELS else "ru"


def param_label(param_key: str, language: str = "ru") -> str:
    lang = normalize_language(language)
    key = str(param_key or "")
    return _PARAM_LABELS.get(lang, {}).get(key, key)


def ordered_param_keys(keys: Iterable[str]) -> List[str]:
    present = [str(k) for k in keys if k]
    present_set = set(present)
    ordered = [k for k in PRIMARY_PARAM_ORDER if k in present_set]
    tail = sorted([k for k in present_set if k not in set(PRIMARY_PARAM_ORDER)])
    return ordered + tail
