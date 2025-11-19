# camera_service.py
import rtsp
import cv2
import numpy as np
import time
from config import RTSP_URL, FRAME_WIDTH, FRAME_HEIGHT


class CameraStream:
    def __init__(self):
        print(f"--- Đang kết nối Camera: {RTSP_URL} ---")
        try:
            # verbose=False để đỡ rác log
            self.client = rtsp.Client(rtsp_server_uri=RTSP_URL, verbose=False)
            time.sleep(2)  # Chờ warm-up
        except Exception as e:
            print(f"Lỗi khởi tạo Camera: {e}")
            self.client = None

    def is_opened(self):
        return self.client is not None and self.client.isOpened()

    def get_frame(self):
        """
        Trả về frame định dạng OpenCV (BGR) đã resize
        """
        if not self.client:
            return None

        try:
            pil_image = self.client.read()
            if pil_image is None:
                return None

            # Convert PIL -> OpenCV
            frame = np.array(pil_image)
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

            # Resize chuẩn
            frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))

            # Lật gương (Mirror) cho tự nhiên
            frame = cv2.flip(frame, 1)

            return frame
        except Exception:
            return None

    def release(self):
        if self.client:
            self.client.close()