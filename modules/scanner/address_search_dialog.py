# modules/scanner/address_search_dialog.py
# Расположение: modules/scanner/address_search_dialog.py
# Описание: Диалог для поиска адреса датчика на выбранном COM-порту.

import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import threading
import time
from utils.sensor import SoilSensor

class AddressSearchDialog(tk.Toplevel):
    def __init__(self, parent, core_api, tr):
        super().__init__(parent)
        self.parent = parent
        self.core_api = core_api
        self.tr = tr
        self.title(self.tr("search_address_title"))
        self.geometry("400x300")
        self.transient(parent)
        self.grab_set()

        self.create_widgets()
        self.refresh_ports()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text=self.tr("select_com_port")).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.port_combo = ttk.Combobox(main_frame, state="readonly", width=15)
        self.port_combo.grid(row=0, column=1, sticky=tk.W, pady=5)

        ttk.Button(main_frame, text=self.tr("refresh_ports"), command=self.refresh_ports).grid(row=0, column=2, padx=5, pady=5)

        ttk.Label(main_frame, text=self.tr("baudrate")).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.baud_var = tk.IntVar(value=4800)
        baud_combo = ttk.Combobox(main_frame, textvariable=self.baud_var, values=[2400, 4800, 9600], width=8)
        baud_combo.grid(row=1, column=1, sticky=tk.W, pady=5)

        self.scan_btn = ttk.Button(main_frame, text=self.tr("start_scan"), command=self.start_scan)
        self.scan_btn.grid(row=2, column=0, columnspan=3, pady=10)

        self.progress = ttk.Progressbar(main_frame, orient=tk.HORIZONTAL, length=300, mode='determinate')
        self.progress.grid(row=3, column=0, columnspan=3, pady=5)

        self.status_label = ttk.Label(main_frame, text="", foreground="blue")
        self.status_label.grid(row=4, column=0, columnspan=3, pady=5)

        # Список результатов
        self.result_tree = ttk.Treeview(main_frame, columns=("address"), show="headings", height=8)
        self.result_tree.heading("address", text=self.tr("found_addresses"))
        self.result_tree.column("address", width=100)
        self.result_tree.grid(row=5, column=0, columnspan=3, pady=5, sticky="nsew")
        main_frame.rowconfigure(5, weight=1)
        main_frame.columnconfigure(0, weight=1)

        self.result_tree.bind("<Double-1>", self.on_address_selected)

    def refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_combo['values'] = ports
        if ports and not self.port_combo.get():
            self.port_combo.set(ports[0])

    def start_scan(self):
        port = self.port_combo.get()
        if not port:
            messagebox.showerror(self.tr("error"), self.tr("port_required"))
            return
        baud = self.baud_var.get()
        self.scan_btn.config(state=tk.DISABLED)
        self.status_label.config(text=self.tr("scanning"))
        self.progress['value'] = 0
        # Очищаем предыдущие результаты
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)

        # Запускаем сканирование в фоновом потоке
        self.scanning = True
        self.thread = threading.Thread(target=self._scan, args=(port, baud), daemon=True)
        self.thread.start()

    def _scan(self, port, baud):
        found = []
        total = 247
        for addr in range(1, 248):
            if not self.scanning:
                break
            # Создаём временный датчик для проверки
            sensor = SoilSensor(port, baud, slave_id=addr, timeout=0.3)
            if sensor.connect():
                # Пинг: читаем один регистр (0x00)
                if sensor.ping(retries=1):
                    found.append(addr)
                sensor.disconnect()
            # Обновляем прогресс в UI
            progress = int(addr / total * 100)
            self.after(0, self.update_progress, progress)
            # Небольшая пауза между попытками, чтобы не перегружать порт
            time.sleep(0.05)

        self.after(0, self.scan_finished, found)

    def update_progress(self, value):
        self.progress['value'] = value

    def scan_finished(self, found):
        self.scanning = False
        self.scan_btn.config(state=tk.NORMAL)
        if found:
            self.status_label.config(text=self.tr("found_addresses").format(len(found)))
            for addr in found:
                self.result_tree.insert('', tk.END, values=(f"{addr}"))
        else:
            self.status_label.config(text=self.tr("no_addresses_found"), foreground="red")

    def on_address_selected(self, event):
        selected = self.result_tree.selection()
        if not selected:
            return
        addr_str = self.result_tree.item(selected[0], "values")[0]
        addr = int(addr_str)
        # Возвращаем выбранный адрес в родительское окно
        if self.parent and hasattr(self.parent, 'presenter') and hasattr(self.parent.presenter, 'on_address_found'):
            self.parent.presenter.on_address_found(addr)
        self.destroy()