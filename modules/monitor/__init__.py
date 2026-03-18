# modules/monitor/__init__.py
# Расположение: modules/monitor/__init__.py
# Описание: Определение модуля MonitorModule.


# modules/monitor/__init__.py
from core.module_interface import BaseModule
from .panel import MonitorPanel

class MonitorModule(BaseModule):
    def get_name(self):
        return "monitor"

    def get_panel_class(self):
        return self._create_panel

    def _create_panel(self, parent):
        # Передаём главное окно (self.core_api.app) как аргумент app
        return MonitorPanel(parent, self.core_api.app)

    def on_activate(self, core_api):
        self.core_api = core_api

    def on_deactivate(self):
        pass