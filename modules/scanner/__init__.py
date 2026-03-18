# modules/scanner/__init__.py
# Расположение: modules/scanner/__init__.py
# Описание: Определение модуля ScannerModule.

from core.module_interface import BaseModule
from .panel import ScannerPanel
from .presenter import ScannerPresenter
from .engine import ScannerEngine

class ScannerModule(BaseModule):
    def get_name(self):
        return "scanner"

    def get_panel_class(self):
        return self._create_panel

    def _create_panel(self, parent):
        engine = ScannerEngine(self.core_api)
        presenter = ScannerPresenter(engine, parent, self.core_api)
        self.presenter = presenter
        return presenter.get_view()

    def on_activate(self, core_api):
        self.core_api = core_api

    def on_deactivate(self):
        if hasattr(self, 'presenter'):
            self.presenter.destroy()