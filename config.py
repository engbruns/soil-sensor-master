# config.py
# Расположение: корень проекта
# Описание: Содержит константы путей, настройки по умолчанию и функции загрузки/сохранения конфигурации YAML.

import os
import yaml
from utils.path_helper import resource_path

# BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # СТАРЫЙ СПОСОБ
BASE_DIR = os.path.dirname(resource_path(""))
PROFILES_DIR = os.path.join(BASE_DIR, "profiles")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
LOCALE_DIR = os.path.join(BASE_DIR, "locale")
CONFIG_FILE = os.path.join(BASE_DIR, "config.yaml")

DEFAULT_CONFIG = {
    "app": {
        "language": "ru",
        "theme": "light"
    },
    "modules": {
        "enabled": ["monitor", "scanner", "calibration", "profiles"]
    },
    "graph_settings": {
        "max_history": 300,
        "y_limits": {}
    },
    "last_port": "",
    "last_baudrate": 4800,
    "last_profile": "",
    "last_address": 1
}

MODBUS_BAUDRATES = [2400, 4800, 9600]

def load_config():
    """Загружает конфигурацию из YAML-файла, если файл существует и корректен, иначе возвращает DEFAULT_CONFIG."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                if config is not None:  # убедимся, что загруженные данные не None
                    return config
        except Exception:
            pass  # при ошибке чтения или парсинга используем умолчания
    return DEFAULT_CONFIG.copy()

def save_config(config):
    """Сохраняет конфигурацию в YAML-файл."""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
    except Exception as e:
        print(f"Ошибка сохранения конфига: {e}")  # техническое сообщение, не локализуется