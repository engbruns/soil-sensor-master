import unittest

from utils.i18n import Translator


class I18nTests(unittest.TestCase):
    def test_available_languages_include_core_locales(self):
        tr = Translator("ru")
        languages = tr.get_available_languages()
        self.assertIn("ru", languages)
        self.assertIn("en", languages)
        self.assertIn("zh", languages)

    def test_qt_keys_available_from_locale_files(self):
        tr = Translator("ru")
        self.assertEqual(tr.tr("menu_file"), "Файл")
        self.assertEqual(tr.tr("action_save"), "Сохранить конфиг")
        self.assertEqual(tr.tr("tab_monitor"), "Монитор")

        tr.load_language("en")
        self.assertEqual(tr.tr("menu_file"), "File")
        self.assertEqual(tr.tr("action_save"), "Save config")
        self.assertEqual(tr.tr("tab_monitor"), "Monitor")

    def test_folder_and_debug_actions_localized(self):
        tr = Translator("ru")
        self.assertNotEqual(tr.tr("action_open_logs"), "action_open_logs")
        self.assertNotEqual(tr.tr("action_open_profiles"), "action_open_profiles")
        self.assertNotEqual(tr.tr("action_debug_console"), "action_debug_console")

        tr.load_language("en")
        self.assertEqual(tr.tr("action_open_logs"), "Open logs folder")
        self.assertEqual(tr.tr("action_open_profiles"), "Open profiles folder")
        self.assertEqual(tr.tr("action_debug_console"), "Error Console (live)")


if __name__ == "__main__":
    unittest.main()
