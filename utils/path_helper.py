# utils/path_helper.py
import os
import sys

def resource_path(relative_path):
    """Возвращает абсолютный путь к ресурсу. Работает и в разработке, и в скомпилированном exe."""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_appdata_dir(subfolder="SoilSensorMonitor"):
    """Возвращает путь к папке приложения в AppData (Windows) или ~/.config (Linux/Mac)."""
    if sys.platform == "win32":
        base = os.environ.get('APPDATA', os.path.expanduser('~'))
    else:
        base = os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
    path = os.path.join(base, subfolder)
    os.makedirs(path, exist_ok=True)
    return path