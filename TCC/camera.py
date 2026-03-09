import threading
from typing import Optional

import cv2


class CameraManager:
    def __init__(self, camera_index: int = 0) -> None:
        self.camera_index = camera_index
        self._cap: Optional[cv2.VideoCapture] = None
        self._lock = threading.Lock()

    def start(self) -> None:
        with self._lock:
            if self._cap is None or not self._cap.isOpened():
                self._cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)

    def read(self):
        with self._lock:
            if self._cap is None or not self._cap.isOpened():
                self.start()
            if self._cap is None:
                return False, None
            return self._cap.read()

    def release(self) -> None:
        with self._lock:
            if self._cap is not None and self._cap.isOpened():
                self._cap.release()
            self._cap = None
