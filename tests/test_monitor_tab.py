import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication

from qt_app.widgets.monitor_tab import MonitorTab


class _FakeRegistry:
    def list_connected_names(self):
        return []

    def list_connected(self):
        return []


class _ImmediateCancelWorker(QObject):
    finished_with_result = pyqtSignal(object, object, object, str)
    finished = pyqtSignal()

    def __init__(self, registry, sensor_names=None):
        super().__init__()
        _ = registry
        _ = sensor_names
        self._running = False
        self.stop_called = False

    def isRunning(self):
        return self._running

    def start(self):
        self._running = True
        self.finished_with_result.emit([], {}, {}, "monitor poll cancelled")
        self._running = False
        self.finished.emit()

    def stop(self):
        self.stop_called = True
        self._running = False

    def wait(self, _wait_ms):
        return True

    def deleteLater(self):
        return None


class _RunningWorker(QObject):
    def __init__(self):
        super().__init__()
        self._running = True
        self.stop_called = False
        self.wait_calls = []
        self.deleted = False

    def isRunning(self):
        return self._running

    def stop(self):
        self.stop_called = True
        self._running = False

    def wait(self, wait_ms):
        self.wait_calls.append(int(wait_ms))
        return True

    def deleteLater(self):
        self.deleted = True


class MonitorTabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tab = MonitorTab(registry=_FakeRegistry(), settings={})
        self.tab.timer.stop()

    def tearDown(self):
        self.tab.shutdown(wait_ms=10)
        self.tab.deleteLater()
        self.app.processEvents()

    def test_poll_cancelled_worker_finishes_cleanly(self):
        with patch("qt_app.widgets.monitor_tab.MonitorPollThread", _ImmediateCancelWorker):
            self.tab.last_sensor_names = ["stale-sensor"]
            self.tab.poll_once()
            self.app.processEvents()

        self.assertIsNone(self.tab._poll_worker)
        self.assertFalse(self.tab._poll_pending)
        self.assertEqual(self.tab.table.columnCount(), 1)
        self.assertEqual(self.tab.table.rowCount(), 1)

    def test_shutdown_stops_running_worker(self):
        worker = _RunningWorker()
        self.tab._poll_worker = worker
        self.tab.shutdown(wait_ms=321)

        self.assertFalse(self.tab._active)
        self.assertFalse(self.tab.timer.isActive())
        self.assertTrue(worker.stop_called)
        self.assertEqual(worker.wait_calls, [321])
        self.assertTrue(worker.deleted)
        self.assertIsNone(self.tab._poll_worker)


if __name__ == "__main__":
    unittest.main()
