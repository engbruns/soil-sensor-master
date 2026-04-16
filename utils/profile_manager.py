# Profile manager for user-editable sensor profiles.

import json
import os
import shutil

from config import EMBEDDED_PROFILES_DIR, PROFILES_DIR


def get_profiles_dir():
    """Return canonical writable directory for profiles."""
    os.makedirs(PROFILES_DIR, exist_ok=True)
    return PROFILES_DIR


class ProfileManager:
    def __init__(self):
        self.profiles_dir = get_profiles_dir()
        os.makedirs(self.profiles_dir, exist_ok=True)
        self._ensure_default_profiles()
        self.cache = {}
        self._load_all()

    def _ensure_default_profiles(self):
        """Copy bundled JSON profiles to user folder if missing."""
        if not os.path.exists(EMBEDDED_PROFILES_DIR):
            return

        for fname in os.listdir(EMBEDDED_PROFILES_DIR):
            if not fname.endswith('.json'):
                continue

            src = os.path.join(EMBEDDED_PROFILES_DIR, fname)
            dst = os.path.join(self.profiles_dir, fname)
            if os.path.exists(dst):
                continue

            try:
                shutil.copy2(src, dst)
            except Exception as exc:
                from .utils import log_error

                log_error(f"Failed to copy default profile {fname}: {exc}")

    def copy_profile(self, fname, new_name):
        data = self.get_profile(fname)
        if not data:
            return False
        new_fname = new_name.replace(" ", "_").lower() + ".json"
        return self.save_profile(new_fname, data)

    def _load_all(self):
        """Load all profiles from user profile directory into cache."""
        self.cache.clear()
        if not os.path.exists(self.profiles_dir):
            return

        for fname in os.listdir(self.profiles_dir):
            if not fname.endswith('.json'):
                continue

            path = os.path.join(self.profiles_dir, fname)
            try:
                with open(path, 'r', encoding='utf-8-sig') as f:
                    self.cache[fname] = json.load(f)
            except Exception as exc:
                from .utils import log_error

                log_error(f"Load profile {fname}: {exc}")

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
        except Exception as exc:
            from .utils import log_error

            log_error(f"Save profile {fname}: {exc}")
            return False

    def delete_profile(self, fname):
        path = os.path.join(self.profiles_dir, fname)
        try:
            os.remove(path)
            self.cache.pop(fname, None)
            return True
        except Exception as exc:
            from .utils import log_error

            log_error(f"Delete profile {fname}: {exc}")
            return False

    def create_default_profiles(self):
        """Backward-compatible no-op kept for legacy call sites."""
        pass
