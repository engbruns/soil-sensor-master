# utils/path_helper.py
import os
import sys

def resource_path(relative_path):
    """Получить абсолютный путь к ресурсу. Работает и в разработке, и в скомпилированном exe."""
    try:
        # PyInstaller создаёт временную папку и хранит путь в _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        # Если мы не в скомпилированной версии, берём путь к папке со скриптом
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)