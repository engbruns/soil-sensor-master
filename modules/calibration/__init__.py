# modules/calibration/__init__.py
from core.module_interface import BaseModule
from .panel import CalibrationPanel
from .presenter import CalibrationPresenter
from .engine import CalibrationEngine

class CalibrationModule(BaseModule):
    def get_name(self):
        return "calibration"

    def get_panel_class(self):
        return self._create_panel

    def _create_panel(self, parent):
        engine = CalibrationEngine(self.core_api)
        presenter = CalibrationPresenter(engine, parent, self.core_api)
        self.presenter = presenter
        return presenter.get_view()

    def on_activate(self, core_api):
        self.core_api = core_api

    def on_deactivate(self):
        if hasattr(self, 'presenter'):
            self.presenter.destroy()