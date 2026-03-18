# ui/dialogs/modules_settings_dialog.py
# Расположение: ui/dialogs/modules_settings_dialog.py
# Описание: Диалог для включения/отключения модулей.

import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os

class ModulesSettingsDialog(tk.Toplevel):
    def __init__(self, parent, module_manager, config_data, tr):
        super().__init__(parent)
        self.parent = parent
        self.module_manager = module_manager
        self.config_data = config_data
        self.tr = tr
        self.title(self.tr("modules_settings_title"))
        self.geometry("300x250")
        self.transient(parent)
        self.grab_set()

        ttk.Label(self, text=self.tr("modules_settings_label")).pack(pady=5)

        self.vars = {}
        for name in self.module_manager._available_modules.keys():
            var = tk.BooleanVar(value=name in self.config_data["modules"]["enabled"])
            cb = ttk.Checkbutton(self, text=name.capitalize(), variable=var)
            cb.pack(anchor=tk.W, padx=20, pady=2)
            self.vars[name] = var

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text=self.tr("save"), command=self.save).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text=self.tr("cancel"), command=self.destroy).pack(side=tk.LEFT, padx=5)

    def save(self):
        enabled = [name for name, var in self.vars.items() if var.get()]
        self.config_data["modules"]["enabled"] = enabled
        if messagebox.askyesno(self.tr("restart_title"), self.tr("restart_question")):
            python = sys.executable
            os.execl(python, python, *sys.argv)
        self.destroy()