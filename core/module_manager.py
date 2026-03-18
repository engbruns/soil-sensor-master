# core/module_manager.py
# Расположение: core/module_manager.py
# Описание: Менеджер модулей – поиск, загрузка и активация модулей.

import importlib
import inspect
import traceback
from pathlib import Path
from .module_interface import BaseModule
from utils.path_helper import resource_path

class ModuleManager:
    def __init__(self, core_api, modules_path="modules"):
        self.core_api = core_api
        # Преобразуем путь с помощью resource_path и сразу создаём Path-объект
        self.modules_path = Path(resource_path(modules_path))
        self._available_modules = {}   # имя -> класс модуля
        self._active_modules = {}       # имя -> экземпляр модуля
        self._panels = {}               # имя -> фабрика панели

    def discover_modules(self):
        """Сканирует папку modules_path и находит все модули, наследующие BaseModule."""
        self._available_modules.clear()
        if not self.modules_path.exists():
            print(f"Modules path {self.modules_path} does not exist")
            return
        for item in self.modules_path.iterdir():
            if not item.is_dir() or item.name.startswith("_"):
                continue
            module_name = item.name
            try:
                # Импортируем пакет модуля
                pkg = importlib.import_module(f"{self.modules_path.name}.{module_name}")
                # Ищем класс, наследующий BaseModule
                found = False
                for name, obj in inspect.getmembers(pkg, inspect.isclass):
                    if issubclass(obj, BaseModule) and obj is not BaseModule:
                        self._available_modules[module_name] = obj
                        found = True
                        break
                if not found:
                    print(f"Module {module_name} does not contain a BaseModule subclass")
                else:
                    print(f"Discovered module: {module_name}")
            except Exception as e:
                print(f"Error loading module {module_name}: {e}")
                traceback.print_exc()

    def load_enabled_modules(self, enabled_names):
        """Загружает и активирует модули из списка enabled_names."""
        self._active_modules.clear()
        self._panels.clear()
        for name in enabled_names:
            print(f"Loading module {name}...")
            if name in self._available_modules:
                module_class = self._available_modules[name]
                try:
                    instance = module_class()
                    instance.on_activate(self.core_api)
                    self._active_modules[name] = instance
                    self._panels[name] = instance.get_panel_class()
                    print(f"Module {name} activated successfully")
                except Exception as e:
                    print(f"Error activating module {name}: {e}")
                    traceback.print_exc()
            else:
                print(f"Module {name} not found in available modules")

    def get_active_panels(self):
        """Возвращает словарь {имя_модуля: фабрика_панели} для активных модулей."""
        return self._panels.copy()

    def deactivate_all(self):
        """Деактивирует все активные модули (при завершении программы)."""
        for name, instance in self._active_modules.items():
            try:
                instance.on_deactivate()
                print(f"Module {name} deactivated")
            except Exception as e:
                print(f"Error deactivating module {name}: {e}")
        self._active_modules.clear()
        self._panels.clear()