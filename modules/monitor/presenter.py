# modules/monitor/presenter.py
# Расположение: modules/monitor/presenter.py
# Описание: Presenter для монитора – связывает engine и view.

from .panel import MonitorPanel

class MonitorPresenter:
    def __init__(self, engine, parent, core_api):
        self.engine = engine
        self.core_api = core_api
        self.tr = core_api.tr
        profile_data = core_api.get_current_profile_data()
        self.params = profile_data.get("parameters", []) if profile_data else []
        self.view = MonitorPanel(parent, self, self.tr, self.params)
        self._alive = True
        print(f"MonitorPresenter created for profile: {core_api.get_setting('last_profile')}")
        self.engine.start(self.on_new_data)

    def on_new_data(self, data):
        if self._alive:
            if data is None:
                self.view.after(0, self.view.show_disconnected)
            else:
                self.view.after(0, self.view.update_data, data)

    def get_view(self):
        return self.view

    def destroy(self):
        print("MonitorPresenter destroy called")
        self._alive = False
        self.engine.stop()
        if self.view and self.view.winfo_exists():
            self.view.destroy()