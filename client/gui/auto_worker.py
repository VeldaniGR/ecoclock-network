"""Worker en QThread: bucle next → compute → submit para modo automático."""
from __future__ import annotations

import time
from typing import Any

from PyQt6.QtCore import QThread, pyqtSignal

from client import ndvi
from client.gui import services


class AutoWorker(QThread):
    task_started = pyqtSignal(dict)       # task
    task_finished = pyqtSignal(dict, float)  # result, compute_time
    error = pyqtSignal(str)
    stopped = pyqtSignal(int)             # completed count

    def __init__(
        self,
        base_url: str,
        token: str,
        sleep_sec: float = 1.0,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._base_url = base_url
        self._token = token
        self._sleep_sec = sleep_sec
        self._stop = False
        self._completed = 0

    def request_stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        while not self._stop:
            try:
                task = services.next_task(self._base_url, self._token)
                self.task_started.emit(task)
                t0 = time.time()
                output = ndvi.compute(task)
                dt = round(time.time() - t0, 3)
                result = services.submit_task(
                    self._base_url,
                    self._token,
                    task["id"],
                    output,
                    dt,
                )
                self._completed += 1
                self.task_finished.emit(result, dt)
            except Exception as exc:  # noqa: BLE001
                self.error.emit(str(exc))
                break
            if self._stop:
                break
            time.sleep(max(0.0, self._sleep_sec))
        self.stopped.emit(self._completed)
