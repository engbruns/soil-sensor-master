# core/core_api.py
# Расположение: core/core_api.py
# Описание: API ядра для модулей.

class CoreAPI:
    def __init__(self, app, settings, profile_manager, logger, sensor, tr):
        self.app = app
        self.settings = settings
        self.profile_manager = profile_manager
        self.logger = logger
        self.sensor = sensor
        self.tr = tr

    def get_setting(self, key, default=None):
        return self.settings.get(key, default)

    def set_setting(self, key, value):
        self.settings[key] = value

    def get_current_profile_data(self):
        """Возвращает данные текущего профиля или None."""
        fname = self.get_setting("last_profile")
        if fname and self.profile_manager:
            return self.profile_manager.get_profile(fname)
        return None