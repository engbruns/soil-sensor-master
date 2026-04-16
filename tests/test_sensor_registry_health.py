import unittest

from qt_app.backend.models import ConnectedSensor, SensorConfig
from qt_app.backend.sensor_registry import SensorRegistry


class _DummyProfileManager:
    def __init__(self, profile):
        self._profile = profile

    def get_profile(self, _name):
        return self._profile


class _DummySensor:
    def __init__(self, responses=None, connected=True):
        self.responses = list(responses or [])
        self.connected = bool(connected)
        self.connect_calls = 0
        self.ping_calls = 0

    def connect(self):
        self.connect_calls += 1
        self.connected = True
        return True

    def disconnect(self):
        self.connected = False

    def ping(self):
        self.ping_calls += 1
        return self.connected

    def read_registers(self, _start_addr, _num_regs, function_code=0x03):
        _ = function_code
        if not self.connected:
            return None
        if self.responses:
            value = self.responses.pop(0)
            if isinstance(value, Exception):
                raise value
            return value
        return [123]

    def write_register(self, _reg_addr, _value, function_code=0x06):
        _ = function_code
        return self.connected


def _build_registry(sensor, simulated=False):
    profile = {
        "parameters": [
            {"key": "param_1", "address": 1, "factor": 1.0, "offset": 0.0},
            {"key": "param_2", "address": 2, "factor": 1.0, "offset": 0.0},
        ]
    }
    registry = SensorRegistry(_DummyProfileManager(profile))
    cfg = SensorConfig(
        name="Sensor-1",
        port="sim" if simulated else "COM7",
        address=1,
        baudrate=9600,
        profile="default",
        simulated=simulated,
    )
    registry._sensors[cfg.name] = ConnectedSensor(
        config=cfg,
        sensor=sensor,
        profile_data=profile,
    )
    return registry, cfg.name


class SensorRegistryHealthTests(unittest.TestCase):
    def test_marks_unstable_when_some_parameters_fail(self):
        sensor = _DummySensor(responses=[[321], None], connected=True)
        registry, name = _build_registry(sensor, simulated=False)

        values = registry.read_parameter_values(name)

        self.assertIsNotNone(values)
        health = registry.get_sensor_health(name)
        self.assertIsNotNone(health)
        self.assertEqual(health["status"], "unstable")
        self.assertEqual(health["consecutive_failures"], 0)
        self.assertIn("parameter reads failed", str(health["last_error"]))

    def test_reconnects_after_consecutive_failures_for_real_sensor(self):
        sensor = _DummySensor(connected=False)
        registry, name = _build_registry(sensor, simulated=False)

        first = registry.read_parameter_values(name)
        second = registry.read_parameter_values(name)

        self.assertIsNone(first)
        self.assertIsNone(second)
        self.assertEqual(sensor.connect_calls, 1)
        self.assertEqual(sensor.ping_calls, 1)
        health = registry.get_sensor_health(name)
        self.assertIsNotNone(health)
        self.assertEqual(health["status"], "connected")
        self.assertEqual(health["consecutive_failures"], 0)

    def test_simulated_sensor_does_not_try_reconnect(self):
        sensor = _DummySensor(connected=False)
        registry, name = _build_registry(sensor, simulated=True)

        registry.read_parameter_values(name)
        registry.read_parameter_values(name)

        self.assertEqual(sensor.connect_calls, 0)
        health = registry.get_sensor_health(name)
        self.assertIsNotNone(health)
        self.assertEqual(health["status"], "degraded")
        self.assertGreaterEqual(health["consecutive_failures"], 2)


if __name__ == "__main__":
    unittest.main()
