# core/module_interface.py
# Расположение: core/module_interface.py
# Описание: Абстрактный базовый класс для всех модулей. Определяет обязательные методы.

from abc import ABC, abstractmethod

class BaseModule(ABC):
    @abstractmethod
    def get_name(self) -> str:
        """Возвращает уникальное имя модуля (используется как ключ)."""
        pass

    @abstractmethod
    def get_panel_class(self):
        """Возвращает класс (или фабрику) панели, которая будет встроена в главное окно."""
        pass

    @abstractmethod
    def on_activate(self, core_api):
        """Вызывается при активации модуля. Здесь можно инициализировать ресурсы."""
        pass

    @abstractmethod
    def on_deactivate(self):
        """Вызывается при деактивации модуля. Освобождение ресурсов (остановка потоков)."""
        pass