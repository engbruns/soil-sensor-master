# utils/logger.py
# Расположение: utils/logger.py
# Описание: Логирование сессии в CSV-файл в пользовательской папке logs.

import csv
import os
from datetime import datetime
from config import LOGS_DIR

class SessionLogger:
    def __init__(self):
        os.makedirs(LOGS_DIR, exist_ok=True)
        self.filename = os.path.join(LOGS_DIR, f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        self.file = open(self.filename, 'w', newline='', encoding='utf-8')
        self.writer = None
        self.header_written = False

    def write_header(self, fieldnames):
        if not self.header_written and fieldnames:
            self.writer = csv.DictWriter(self.file, fieldnames=fieldnames)
            self.writer.writeheader()
            self.header_written = True

    def log(self, data):
        if not data:
            return
        row = data.copy()
        row['timestamp'] = datetime.now().isoformat(sep=' ', timespec='seconds')
        if not self.header_written:
            self.write_header(['timestamp'] + list(data.keys()))
        try:
            self.writer.writerow(row)
            self.file.flush()
        except Exception as e:
            from .utils import log_error
            log_error(f"Log write error: {e}")

    def close(self):
        if self.file and not self.file.closed:
            self.file.close()

    def get_filename(self):
        return self.filename