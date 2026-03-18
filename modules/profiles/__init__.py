# modules/profiles/__init__.py
from core.module_interface import BaseModule
from .panel import ProfilesPanel

class ProfilesModule(BaseModule):
    def get_name(self):
        return "profiles"

    def get_panel_class(self):
        return self._create_panel

    def _create_panel(self, parent):
        return ProfilesPanel(parent, self.core_api.app)

    def on_activate(self, core_api):
        self.core_api = core_api

    def on_deactivate(self):
        pass