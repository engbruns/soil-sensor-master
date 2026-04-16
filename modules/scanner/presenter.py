# modules/scanner/presenter.py
# Presenter for scanner module.

from .panel import ScannerPanel
from .engine import ScannerEngine
from .analyzer import analyze
from core.constants import STANDARD_PARAMS, ADDRESS_HINTS


class ScannerPresenter:
    def __init__(self, engine, parent, core_api):
        self.engine = engine
        self.core_api = core_api
        self.tr = core_api.tr
        self._alive = True
        self.current_snapshot = []
        self.manual_mapping = {}
        self.reference_values = []
        self.last_probs = None
        self.selected_sensor = None

        self.view = ScannerPanel(parent, self, self.tr)
        print("ScannerPresenter created")
        self.on_sensors_changed()

    def on_sensor_selected(self, name):
        self.selected_sensor = self.core_api.get_sensor(name)
        if not self.selected_sensor or not self.selected_sensor.connected:
            self.view.show_message(self.tr("sensor_not_connected"))

    def on_start_collect(self, addresses, num_cycles):
        if not self.selected_sensor or not self.selected_sensor.connected:
            self.view.show_message(self.tr("sensor_not_connected"))
            return
        self.view.set_collecting(True)
        self.engine.start_collect(
            sensor=self.selected_sensor,
            addresses=addresses,
            num_cycles=num_cycles,
            progress_callback=self.on_progress,
            finished_callback=self.on_collect_finished,
        )

    def on_stop_collect(self):
        self.engine.stop()
        self.view.set_collecting(False)

    def on_progress(self, percent):
        if self._alive:
            self.view.after(0, self.view.update_progress, percent)

    def on_collect_finished(self, snapshot, success):
        if not self._alive:
            return
        self.view.set_collecting(False)
        if success and snapshot:
            self.current_snapshot = snapshot
            self.view.update_table(snapshot, self.manual_mapping)
            self.view.enable_analyze(True)
            self.view.enable_save(True)
        else:
            self.view.show_message(self.tr("scan_failed"))

    def on_analyze_clicked(self):
        if not self.current_snapshot:
            self.view.show_message(self.tr("no_data"))
            return
        if not self.reference_values:
            self.view.show_message(self.tr("no_references"))
            return
        probs = analyze(self.current_snapshot, self.reference_values, STANDARD_PARAMS, ADDRESS_HINTS)
        self.last_probs = probs
        self.view.update_table_with_probs(self.current_snapshot, self.manual_mapping, probs, self.tr)

    def on_assign_clicked(self, addr_hex, current_param):
        from .assign_dialog import AssignParamDialog

        AssignParamDialog(self.view, addr_hex, current_param, self.on_param_assigned, self.tr)

    def on_param_assigned(self, addr_hex, mapping):
        addr = int(addr_hex, 16)
        self.manual_mapping[addr] = mapping
        self.view.update_table(self.current_snapshot, self.manual_mapping)

    def on_graph_clicked(self, addr_hex, raw_values, median):
        from .graph_dialog import GraphDialog

        GraphDialog(self.view, addr_hex, raw_values, median)

    def on_add_reference(self, param_key, value, tolerance):
        self.reference_values.append({"param": param_key, "value": value, "tolerance": tolerance})

    def on_remove_reference(self, index):
        if 0 <= index < len(self.reference_values):
            del self.reference_values[index]

    def open_address_search(self):
        from .address_search_dialog import AddressSearchDialog

        AddressSearchDialog(self.view, self.core_api, self.tr)

    def on_save_profile(self):
        if not self.current_snapshot:
            self.view.show_message(self.tr("no_data"))
            return
        from .save_profile_dialog import SaveProfileDialog

        SaveProfileDialog(self.view, self.core_api, self.current_snapshot, self.manual_mapping, self.last_probs, self.tr)

    def on_sensors_changed(self):
        self.view.update_sensor_list()
        name = self.view.sensor_combo.get()
        self.selected_sensor = self.core_api.get_sensor(name) if name else None

    def on_show(self):
        pass

    def on_hide(self):
        if self.engine.running:
            self.on_stop_collect()

    def destroy(self):
        self._alive = False
        self.engine.stop()
        if self.view and self.view.winfo_exists():
            self.view.destroy()

    def get_view(self):
        return self.view
