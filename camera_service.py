# camera_service.py
import rtsp
import cv2
import numpy as np
import time
import logging
from config import RTSP_URL, FRAME_WIDTH, FRAME_HEIGHT

# Setup logging
logger = logging.getLogger(__name__)


class CameraStream:
    def __init__(self, max_reconnect_attempts=5, reconnect_delay=3):
        """
        Khởi tạo CameraStream với RTSP connection
        
        Args:
            max_reconnect_attempts: Số lần thử reconnect tối đa
            reconnect_delay: Thời gian chờ giữa các lần reconnect (giây)
        """
        self.rtsp_url = RTSP_URL
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_delay = reconnect_delay
        self.client = None
        self.reconnect_count = 0
        self.last_frame_time = 0
        self.frame_timeout = 5.0  # Timeout nếu không nhận được frame trong 5s
        
        self._connect()

    def _connect(self):
        """Kết nối hoặc reconnect đến RTSP stream"""
        logger.info(f"--- Đang kết nối Camera: {self.rtsp_url} ---")
        try:
            # Đóng connection cũ nếu có
            if self.client is not None:
                try:
                    self.client.close()
                except Exception as e:
                    logger.warning(f"Lỗi khi đóng connection cũ: {e}")
            
            # Tạo connection mới
            self.client = rtsp.Client(rtsp_server_uri=self.rtsp_url, verbose=False)
            time.sleep(2)  # Chờ warm-up
            
            # Kiểm tra connection
            if self.client.isOpened():
                logger.info("✅ Kết nối Camera thành công!")
                self.reconnect_count = 0
                return True
            else:
                logger.warning("⚠️ Camera connection không mở được")
                self.client = None
                return False
                
        except Exception as e:
            logger.error(f"❌ Lỗi khởi tạo Camera: {e}", exc_info=True)
            self.client = None
            return False

    def _try_reconnect(self):
        """Thử reconnect nếu connection bị mất"""
        if self.reconnect_count >= self.max_reconnect_attempts:
            logger.error(f"❌ Đã thử reconnect {self.max_reconnect_attempts} lần nhưng thất bại")
            return False
        
        self.reconnect_count += 1
        logger.warning(f"🔄 Đang thử reconnect lần {self.reconnect_count}/{self.max_reconnect_attempts}...")
        time.sleep(self.reconnect_delay)
        return self._connect()

    def is_opened(self):
        """Kiểm tra camera có đang mở không"""
        if self.client is None:
            return False
        
        try:
            return self.client.isOpened()
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra camera status: {e}")
            return False

    def get_frame(self):
        """
        Trả về frame định dạng OpenCV (BGR) đã resize
        Tự động reconnect nếu connection bị mất
        """
        # Kiểm tra connection
        if not self.is_opened():
            if not self._try_reconnect():
                return None
        
        try:
            # Đọc frame từ RTSP
            pil_image = self.client.read()
            
            if pil_image is None:
                # Kiểm tra timeout
                current_time = time.time()
                if current_time - self.last_frame_time > self.frame_timeout:
                    logger.warning("⚠️ Không nhận được frame trong thời gian dài, thử reconnect...")
                    if not self._try_reconnect():
                        return None
                return None
            
            # Cập nhật thời gian nhận frame thành công
            self.last_frame_time = time.time()
            
            # Convert PIL -> OpenCV
            frame = np.array(pil_image)
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

            # Resize chuẩn
            frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))

            # Lật gương (Mirror) cho tự nhiên
            frame = cv2.flip(frame, 1)

            return frame
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi đọc frame: {e}", exc_info=True)
            # Thử reconnect nếu có lỗi
            if not self.is_opened():
                self._try_reconnect()
            return None

    def release(self):
        """Đóng camera connection và giải phóng tài nguyên"""
        if self.client is not None:
            try:
                self.client.close()
                logger.info("✅ Đã đóng camera connection")
            except Exception as e:
                logger.error(f"❌ Lỗi khi đóng camera: {e}", exc_info=True)
            finally:
                self.client = None

    def __del__(self):
        """Destructor - đảm bảo camera được đóng khi object bị xóa"""
        self.release()
