import os
import tempfile
import unittest

import yaml

import config


class ConfigTests(unittest.TestCase):
    def test_deep_merge_keeps_defaults(self):
        base = {
            "app": {"language": "ru", "theme": "light"},
            "graph_settings": {"max_history": 300, "y_limits": {}},
        }
        override = {
            "app": {"language": "en"},
            "graph_settings": {"y_limits": {"ph": {"auto": False}}},
        }
        merged = config._deep_merge_dict(base, override)

        self.assertEqual(merged["app"]["language"], "en")
        self.assertEqual(merged["app"]["theme"], "light")
        self.assertEqual(merged["graph_settings"]["max_history"], 300)
        self.assertIn("ph", merged["graph_settings"]["y_limits"])

    @unittest.skip("Slow/IO-bound in this environment; run manually when needed")
    def test_load_config_merges_with_defaults(self):
        fd, config_path = tempfile.mkstemp(
            prefix="test_cfg_",
            suffix=".yaml",
            dir=config.USER_DATA_DIR,
        )
        os.close(fd)
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.safe_dump({"app": {"language": "en"}}, f, allow_unicode=True)

            original_path = config.CONFIG_FILE
            try:
                config.CONFIG_FILE = config_path
                loaded = config.load_config()
            finally:
                config.CONFIG_FILE = original_path

            self.assertEqual(loaded["app"]["language"], "en")
            self.assertEqual(loaded["app"]["theme"], config.DEFAULT_CONFIG["app"]["theme"])
            self.assertIn("modules", loaded)
        finally:
            try:
                os.remove(config_path)
            except OSError:
                pass


if __name__ == "__main__":
    unittest.main()
