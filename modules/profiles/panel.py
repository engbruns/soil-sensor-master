# modules/profiles/panel.py
# Расположение: modules/profiles/panel.py
# Описание: Панель управления профилями с возможностью создания, редактирования, удаления.

import tkinter as tk
from tkinter import ttk, messagebox
import os
from .edit_dialog import ProfileEditDialog

class ProfilesPanel(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.tr = app.tr
        self.profile_manager = app.profile_manager
        self.create_widgets()
        self.refresh_list()

    def create_widgets(self):
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(btn_frame, text=self.tr("new_profile"), command=self.create_new).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text=self.tr("edit_profile"), command=self.edit_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text=self.tr("delete_profile"), command=self.delete_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text=self.tr("refresh"), command=self.refresh_list).pack(side=tk.LEFT, padx=2)

        # Таблица профилей
        columns = ("name", "description")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=20)
        self.tree.heading("name", text=self.tr("profile_name"))
        self.tree.heading("description", text=self.tr("description"))
        self.tree.column("name", width=200)
        self.tree.column("description", width=400)

        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10,0), pady=10)
        vsb.pack(side=tk.RIGHT, fill=tk.Y, padx=(0,10), pady=10)

        self.tree.bind("<Double-1>", self.on_double_click)

    def refresh_list(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        profiles = self.profile_manager.list_profiles()
        for fname in profiles:
            data = self.profile_manager.get_profile(fname)
            name = data.get("name", fname)
            desc = data.get("description", "")
            self.tree.insert("", tk.END, values=(name, desc), tags=(fname,))

    def get_selected_filename(self):
        selected = self.tree.selection()
        if not selected:
            return None
        return self.tree.item(selected[0], "tags")[0]

    def create_new(self):
        dlg = ProfileEditDialog(self, self.profile_manager, tr=self.tr)
        self.wait_window(dlg)
        if dlg.result:
            # Сохраняем профиль
            name = dlg.result.get("name", "").replace(" ", "_").lower()
            if not name:
                name = "new_profile"
            fname = name + ".json"
            # Проверяем уникальность имени
            while fname in self.profile_manager.list_profiles():
                fname = name + "_1.json"
                name = name + "_1"
            dlg.result["name"] = name
            if self.profile_manager.save_profile(fname, dlg.result):
                self.refresh_list()
                # Обновляем выпадающий список в главном окне
                if hasattr(self.app, 'refresh_profiles'):
                    self.app.refresh_profiles()
                messagebox.showinfo(self.tr("success"), self.tr("profile_created"))
            else:
                messagebox.showerror(self.tr("error"), self.tr("save_failed"))

    def edit_selected(self):
        fname = self.get_selected_filename()
        if not fname:
            messagebox.showinfo(self.tr("info"), self.tr("select_profile"))
            return
        data = self.profile_manager.get_profile(fname)
        if not data:
            messagebox.showerror(self.tr("error"), self.tr("profile_not_found"))
            return
        # Создаём копию, чтобы не испортить оригинал до сохранения
        import copy
        edit_data = copy.deepcopy(data)
        dlg = ProfileEditDialog(self, self.profile_manager, edit_data, self.tr)
        self.wait_window(dlg)
        if dlg.result:
            # Сохраняем изменения
            if self.profile_manager.save_profile(fname, dlg.result):
                self.refresh_list()
                if self.app.current_profile == fname:
                    self.app.current_profile_data = dlg.result
                if hasattr(self.app, 'refresh_profiles'):
                    self.app.refresh_profiles()
                messagebox.showinfo(self.tr("success"), self.tr("profile_saved"))
            else:
                messagebox.showerror(self.tr("error"), self.tr("save_failed"))

    def delete_selected(self):
        fname = self.get_selected_filename()
        if not fname:
            messagebox.showinfo(self.tr("info"), self.tr("select_profile"))
            return
        if messagebox.askyesno(self.tr("confirm"), self.tr("delete_confirm").format(fname)):
            if self.profile_manager.delete_profile(fname):
                self.refresh_list()
                if self.app.current_profile == fname:
                    self.app.current_profile = None
                    self.app.current_profile_data = None
                if hasattr(self.app, 'refresh_profiles'):
                    self.app.refresh_profiles()
            else:
                messagebox.showerror(self.tr("error"), self.tr("delete_failed"))

    def on_double_click(self, event):
        fname = self.get_selected_filename()
        if fname:
            # При двойном клике загружаем профиль в главное окно
            if hasattr(self.app, 'load_profile'):
                self.app.load_profile(fname)
            # Или можно просто открыть на редактирование:
            # self.edit_selected()