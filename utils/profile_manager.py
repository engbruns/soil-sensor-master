# utils/profile_manager.py
# Расположение: utils/profile_manager.py
# Описание: Менеджер профилей – загрузка, сохранение, удаление JSON-файлов.

import os
import json
from config import PROFILES_DIR

class ProfileManager:
    def __init__(self):
        self.profiles_dir = PROFILES_DIR
        os.makedirs(self.profiles_dir, exist_ok=True)
        self.cache = {}
        self._load_all()

    def _load_all(self):
        self.cache.clear()
        if not os.path.exists(self.profiles_dir):
            return
        for fname in os.listdir(self.profiles_dir):
            if fname.endswith('.json'):
                path = os.path.join(self.profiles_dir, fname)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        self.cache[fname] = json.load(f)
                except Exception as e:
                    from .utils import log_error
                    log_error(f"Load profile {fname}: {e}")

    def list_profiles(self):
        return list(self.cache.keys())

    def get_profile(self, fname):
        return self.cache.get(fname)

    def save_profile(self, fname, data):
        if not fname.endswith('.json'):
            fname += '.json'
        path = os.path.join(self.profiles_dir, fname)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            self.cache[fname] = data
            return True
        except Exception as e:
            from .utils import log_error
            log_error(f"Save profile {fname}: {e}")
            return False

    def delete_profile(self, fname):
        path = os.path.join(self.profiles_dir, fname)
        try:
            os.remove(path)
            self.cache.pop(fname, None)
            return True
        except Exception as e:
            from .utils import log_error
            log_error(f"Delete profile {fname}: {e}")
            return False

    def create_default_profiles(self):
        """Создаёт несколько базовых профилей, если их нет."""
        defaults = [
            {
                "name": "JXCT 7-in-1 (пример)",
                "description": "Пример профиля для 7-в-1 (адреса требуют уточнения)",
                "device": {"default_address": 1, "default_baudrate": 4800, "available_baudrates": [2400,4800,9600]},
                "parameters": [
                    {"key": "temperature", "name": "temperature", "unit": "°C", "address": 19, "factor": 0.1, "offset": 0},
                    {"key": "humidity", "name": "humidity", "unit": "%", "address": 18, "factor": 0.1, "offset": 0},
                    {"key": "ph", "name": "pH", "unit": "", "address": 6, "factor": 0.01, "offset": 0},
                    {"key": "ec", "name": "EC", "unit": "µS/cm", "address": 21, "factor": 1, "offset": 0},
                    {"key": "nitrogen", "name": "nitrogen", "unit": "mg/kg", "address": 30, "factor": 1, "offset": 0},
                    {"key": "phosphorus", "name": "phosphorus", "unit": "mg/kg", "address": 31, "factor": 1, "offset": 0},
                    {"key": "potassium", "name": "potassium", "unit": "mg/kg", "address": 32, "factor": 1, "offset": 0}
                ]
            },
            {
                "name": "JXCT NPK",
                "description": "Отдельный NPK датчик",
                "device": {"default_address": 1, "default_baudrate": 9600, "available_baudrates": [2400,4800,9600]},
                "parameters": [
                    {"key": "nitrogen", "name": "nitrogen", "unit": "mg/kg", "address": 30, "factor": 1, "offset": 0},
                    {"key": "phosphorus", "name": "phosphorus", "unit": "mg/kg", "address": 31, "factor": 1, "offset": 0},
                    {"key": "potassium", "name": "potassium", "unit": "mg/kg", "address": 32, "factor": 1, "offset": 0}
                ]
            }
        ]
        for prof in defaults:
            fname = prof["name"].replace(" ", "_").lower() + ".json"
            if fname not in self.cache:
                self.save_profile(fname, prof)