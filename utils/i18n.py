# utils/i18n.py
# Расположение: utils/i18n.py
# Описание: Класс Translator для загрузки файлов локализации и перевода строк.

# utils/i18n.py
import json
import os
from config import LOCALE_DIR

class Translator:
    def __init__(self, language="ru"):
        self.language = language
        self.strings = {}
        self.load_language(language)

    def load_language(self, language):
        file_path = os.path.join(LOCALE_DIR, f"{language}.json")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.strings = json.load(f)
        except FileNotFoundError:
            # fallback to Russian
            fallback = os.path.join(LOCALE_DIR, "ru.json")
            if os.path.exists(fallback):
                with open(fallback, 'r', encoding='utf-8') as f:
                    self.strings = json.load(f)
            else:
                self.strings = {}
        except Exception as e:
            print(f"Error loading language file: {e}")
            self.strings = {}

    def tr(self, key):
        return self.strings.get(key, key)

    def get_available_languages(self):
        """Возвращает список кодов языков, для которых есть файлы в папке locale."""
        langs = []
        if not os.path.exists(LOCALE_DIR):
            return langs
        for f in os.listdir(LOCALE_DIR):
            if f.endswith('.json'):
                langs.append(f[:-5])
        return langs

    def get_language_display_name(self, lang):
        """Возвращает название языка на его родном языке (из файла локализации)."""
        file_path = os.path.join(LOCALE_DIR, f"{lang}.json")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("language_name", lang)
        except:
            return lang