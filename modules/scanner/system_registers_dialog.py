# modules/scanner/system_registers_dialog.py
import tkinter as tk
from tkinter import ttk, messagebox
import struct

class SystemRegistersDialog(tk.Toplevel):
    def __init__(self, parent, core_api, profile, tr):
        super().__init__(parent)
        self.parent = parent
        self.core_api = core_api
        self.profile = profile
        self.tr = tr
        self.title(self.tr("system_registers"))
        self.geometry("800x400")
        self.transient(parent)
        self.grab_set()

        self.tree = ttk.Treeview(self, columns=("name", "address", "value", "unit", "action"), show="headings")
        self.tree.heading("name", text=self.tr("name"))
        self.tree.heading("address", text=self.tr("address"))
        self.tree.heading("value", text=self.tr("value"))
        self.tree.heading("unit", text=self.tr("unit"))
        self.tree.heading("action", text=self.tr("action"))
        self.tree.column("name", width=150)
        self.tree.column("address", width=80)
        self.tree.column("value", width=100)
        self.tree.column("unit", width=80)
        self.tree.column("action", width=100)

        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        vsb.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Button(btn_frame, text=self.tr("refresh"), command=self.load_values).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text=self.tr("close"), command=self.destroy).pack(side=tk.LEFT, padx=5)

        self.load_values()

    def load_values(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        sensor = self.core_api.sensor
        if not sensor or not sensor.connected:
            messagebox.showerror(self.tr("error"), self.tr("sensor_not_connected"))
            return

        self.system_regs = self.profile.get("system_registers", [])
        for idx, reg in enumerate(self.system_regs):
            if not isinstance(reg, dict):
                continue
            addr = reg["address"]
            # Чтение значения
            if reg.get("type") == "float32":
                vals = sensor.read_registers(addr, 2)
                if vals and len(vals) == 2:
                    combined = (vals[0] << 16) | vals[1]
                    value = struct.unpack('>f', struct.pack('>I', combined))[0]
                else:
                    value = None
            else:
                vals = sensor.read_registers(addr, 1)
                if vals and len(vals) == 1:
                    raw = vals[0]
                    factor = reg.get("factor", 1)
                    offset = reg.get("offset", 0)
                    value = raw * factor + offset
                else:
                    value = None

            display_name = self.tr(reg.get("name_key", reg["key"]))
            item = self.tree.insert("", tk.END, values=(
                display_name,
                f"0x{addr:02X}",
                f"{value:.2f}" if value is not None else "---",
                reg.get("unit", ""),
                self.tr("edit")
            ))
            self.tree.item(item, tags=(str(idx),))

        self.tree.bind("<Button-1>", self.on_click)

    def on_click(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        col = self.tree.identify_column(event.x)
        if col == "#5":  # колонка "action"
            tags = self.tree.item(item, "tags")
            if tags and tags[0]:
                try:
                    idx = int(tags[0])
                    if 0 <= idx < len(self.system_regs):
                        self.edit_register(self.system_regs[idx])
                    else:
                        messagebox.showerror(self.tr("error"), "Invalid register index")
                except ValueError:
                    messagebox.showerror(self.tr("error"), "Invalid register tag")

    def edit_register(self, reg):
        EditDialog(self, self.core_api, reg, self.tr, self.load_values)

class EditDialog(tk.Toplevel):
    def __init__(self, parent, core_api, reg, tr, callback):
        super().__init__(parent)
        self.parent = parent
        self.core_api = core_api
        self.reg = reg
        self.tr = tr
        self.callback = callback
        self.title(f"{tr('edit')} {tr(reg.get('name_key', reg['key']))}")
        self.geometry("300x150")
        self.transient(parent)
        self.grab_set()

        ttk.Label(self, text=f"{tr('address')}: 0x{reg['address']:02X}").pack(pady=5)
        ttk.Label(self, text=self.tr("new_value")).pack(pady=5)
        self.value_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.value_var).pack(pady=5)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text=self.tr("write"), command=self.write).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text=self.tr("cancel"), command=self.destroy).pack(side=tk.LEFT, padx=5)

    def write(self):
        try:
            new_val = float(self.value_var.get())
        except ValueError:
            messagebox.showerror(self.tr("error"), self.tr("invalid_number"))
            return

        sensor = self.core_api.sensor
        if not sensor or not sensor.connected:
            messagebox.showerror(self.tr("error"), self.tr("sensor_not_connected"))
            return

        addr = self.reg["address"]
        factor = self.reg.get("factor", 1)
        offset = self.reg.get("offset", 0)
        raw = (new_val - offset) / factor
        if not raw.is_integer():
            messagebox.showerror(self.tr("error"), self.tr("value_not_integer"))
            return
        raw = int(raw)

        if "min" in self.reg and raw < self.reg["min"]:
            messagebox.showerror(self.tr("error"), f"{self.tr('min')} {self.reg['min']}")
            return
        if "max" in self.reg and raw > self.reg["max"]:
            messagebox.showerror(self.tr("error"), f"{self.tr('max')} {self.reg['max']}")
            return
        if "values" in self.reg and raw not in self.reg["values"]:
            messagebox.showerror(self.tr("error"), f"{self.tr('allowed')} {self.reg['values']}")
            return

        # Выполняем запись
        success = sensor.write_register(addr, raw)
        if success:
            messagebox.showinfo(self.tr("success"), self.tr("write_success"))
            self.callback()
            self.destroy()
        else:
            messagebox.showerror(self.tr("error"), self.tr("write_failed"))