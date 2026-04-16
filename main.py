import os
import sys

from config import USER_DATA_DIR


def _run_legacy_tk():
    from ui.main_window import MainWindow

    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    os.makedirs(USER_DATA_DIR, exist_ok=True)

    try:
        from qt_app.app import run as run_qt

        sys.exit(run_qt())
    except ModuleNotFoundError as exc:
        # Fallback path for environments where PyQt6 is not yet installed.
        if "PyQt6" in str(exc):
            print("PyQt6 not installed. Falling back to legacy Tkinter UI.")
            _run_legacy_tk()
        else:
            raise
