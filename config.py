import copy
import os

import yaml

from utils.path_helper import get_appdata_dir, resource_path

# Writable user data directory (%APPDATA% on Windows).
USER_DATA_DIR = get_appdata_dir()
os.makedirs(USER_DATA_DIR, exist_ok=True)

# Writable runtime files.
PROFILES_DIR = os.path.join(USER_DATA_DIR, "profiles")
LOGS_DIR = os.path.join(USER_DATA_DIR, "logs")
CONFIG_FILE = os.path.join(USER_DATA_DIR, "config.yaml")
os.makedirs(PROFILES_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# Read-only bundled resources.
EMBEDDED_PROFILES_DIR = resource_path("profiles")
LOCALE_DIR = resource_path("locale")

DEFAULT_CONFIG = {
    "app": {
        "language": "ru",
        "theme": "light",
    },
    "modules": {
        "enabled": ["monitor", "scanner", "calibration", "profiles"],
    },
    "graph_settings": {
        "max_history": 300,
        "y_limits": {},
    },
    "last_port": "",
    "last_baudrate": 4800,
    "last_profile": "",
    "last_address": 1,
}

MODBUS_BAUDRATES = [2400, 4800, 9600]


def _deep_merge_dict(base, override):
    """Recursively merge dictionaries without mutating the inputs."""
    if not isinstance(base, dict) or not isinstance(override, dict):
        return copy.deepcopy(override)

    merged = copy.deepcopy(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge_dict(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def load_config():
    """Load config from YAML and merge with defaults."""
    defaults = copy.deepcopy(DEFAULT_CONFIG)
    if not os.path.exists(CONFIG_FILE):
        return defaults

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f)
    except Exception as exc:
        print(f"Config load error, defaults will be used: {exc}")
        return defaults

    if loaded is None:
        return defaults

    if not isinstance(loaded, dict):
        print("Config load warning: root YAML node must be a mapping; defaults will be used")
        return defaults

    return _deep_merge_dict(defaults, loaded)


def save_config(config):
    """Save config to user YAML file."""
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
    except Exception as exc:
        print(f"Config save error: {exc}")
