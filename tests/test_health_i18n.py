import unittest

from utils.i18n import Translator


class HealthI18nTests(unittest.TestCase):
    def test_health_keys_exist_in_supported_locales(self):
        keys = [
            "health_caption",
            "health_none",
            "health_total",
            "health_ok",
            "health_unstable",
            "health_reconnecting",
            "health_degraded",
        ]

        tr = Translator("ru")
        for key in keys:
            self.assertNotEqual(tr.tr(key), key)

        tr.load_language("en")
        self.assertEqual(tr.tr("health_caption"), "Health")
        self.assertEqual(tr.tr("health_none"), "Sensors: none")

        tr.load_language("zh")
        for key in keys:
            self.assertNotEqual(tr.tr(key), key)


if __name__ == "__main__":
    unittest.main()
