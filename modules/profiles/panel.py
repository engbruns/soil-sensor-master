# modules/profiles/panel.py
import tkinter as tk
from tkinter import ttk, messagebox
import os
import subprocess

class ProfilesPanel(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.tr = app.tr
        self.profile_manager = app.profile_manager
        self.create_widgets()
        self.refresh_list()

    def create_widgets(self):
        # Кнопки управления
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(btn_frame, text=self.tr("refresh"), command=self.refresh_list).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text=self.tr("open"), command=self.open_profile).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text=self.tr("delete"), command=self.delete_profile).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text=self.tr("new"), command=self.create_new).pack(side=tk.LEFT, padx=2)

        # Список профилей
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

    def open_profile(self):
        fname = self.get_selected_filename()
        if not fname:
            messagebox.showinfo(self.tr("info"), self.tr("select_profile"))
            return
        path = os.path.join(self.profile_manager.profiles_dir, fname)
        try:
            if os.name == 'nt':
                os.startfile(path)
            else:
                subprocess.run(["xdg-open", path])
        except Exception as e:
            messagebox.showerror(self.tr("error"), self.tr("open_failed"))

    def delete_profile(self):
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
            else:
                messagebox.showerror(self.tr("error"), self.tr("delete_failed"))

    def create_new(self):
        dlg = tk.Toplevel(self)
        dlg.title(self.tr("new_profile"))
        dlg.geometry("300x200")
        dlg.transient(self)
        dlg.grab_set()

        ttk.Label(dlg, text=self.tr("profile_name")).pack(pady=5)
        name_var = tk.StringVar()
        ttk.Entry(dlg, textvariable=name_var, width=30).pack(pady=5)

        ttk.Label(dlg, text=self.tr("description")).pack(pady=5)
        desc_var = tk.StringVar()
        ttk.Entry(dlg, textvariable=desc_var, width=30).pack(pady=5)

        def save():
            profile_name = name_var.get().strip()
            if not profile_name:
                messagebox.showerror(self.tr("error"), self.tr("enter_name"))
                return
            fname = profile_name.replace(" ", "_").lower() + ".json"
            profile_data = {
                "name": profile_name,
                "description": desc_var.get().strip(),
                "device": {
                    "default_address": 1,
                    "default_baudrate": 4800,
                    "available_baudrates": [2400, 4800, 9600]
                },
                "parameters": [],
                "system_registers": [],
                "calibration": None
            }
            if self.profile_manager.save_profile(fname, profile_data):
                self.refresh_list()
                dlg.destroy()
                messagebox.showinfo(self.tr("success"), self.tr("profile_created"))
            else:
                messagebox.showerror(self.tr("error"), self.tr("save_failed"))

        ttk.Button(dlg, text=self.tr("save"), command=save).pack(pady=5)
        ttk.Button(dlg, text=self.tr("cancel"), command=dlg.destroy).pack(pady=5)

    def on_double_click(self, event):
        fname = self.get_selected_filename()
        if fname:
            self.app.profile_var.set(fname)
            self.app.load_profile(fname)