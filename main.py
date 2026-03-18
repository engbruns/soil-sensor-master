# main.py
# Расположение: корень проекта
# Описание: Точка входа. Запускает главное окно.

import os
import sys
from ui.main_window import MainWindow

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    app = MainWindow()
    app.mainloop()