import json
import os

from config import LOCALE_DIR


class Translator:
    def __init__(self, language="ru"):
        self.language = language
        self.strings = {}
        self.load_language(language)

    @staticmethod
    def _language_file(language):
        return os.path.join(LOCALE_DIR, f"{language}.json")

    @staticmethod
    def _load_file(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}

    def load_language(self, language):
        self.language = language
        file_path = self._language_file(language)
        try:
            self.strings = self._load_file(file_path)
        except FileNotFoundError:
            fallback = self._language_file("ru")
            if os.path.exists(fallback):
                self.strings = self._load_file(fallback)
            else:
                self.strings = {}
        except Exception as exc:
            print(f"Error loading language file: {exc}")
            self.strings = {}

    def tr(self, key):
        return self.strings.get(key, key)

    def get_available_languages(self):
        """Return sorted list of available locale codes."""
        langs = []
        if not os.path.exists(LOCALE_DIR):
            return langs
        for file_name in os.listdir(LOCALE_DIR):
            if file_name.endswith(".json"):
                langs.append(file_name[:-5])
        return sorted(set(langs))

    def get_language_display_name(self, lang):
        """Return display name from locale file, or language code."""
        file_path = self._language_file(lang)
        try:
            data = self._load_file(file_path)
            return data.get("language_name", lang)
        except Exception:
            return lang
