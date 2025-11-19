# config.py

# --- CẤU HÌNH CAMERA ---
RTSP_URL = 'rtsp://admin:Promise%40123@192.168.100.62/ONVIF/MediaInput?profile=def_profile1'

# --- CẤU HÌNH XỬ LÝ ẢNH ---
FRAME_WIDTH = 640
FRAME_HEIGHT = 480

# --- CẤU HÌNH VÙNG AN TOÀN (SAFE ZONE) ---
ZONE_WIDTH = 180
ZONE_HEIGHT = 260
# Tự động tính toán căn giữa
ZONE_X = (FRAME_WIDTH - ZONE_WIDTH) // 2
ZONE_Y = (FRAME_HEIGHT - ZONE_HEIGHT) // 2

# --- CẤU HÌNH LOGIC CHỤP ẢNH ---
REQUIRED_FRAMES = 30    # Số frame cần giữ yên để chụp (khoảng 0.5s)
MIN_FACE_RATIO = 0.6    # Tỷ lệ mặt tối thiểu (để tránh quá xa)
MAX_FACE_RATIO = 0.9    # Tỷ lệ mặt tối đa (để tránh quá gần)
CENTER_TOLERANCE = 50   # Sai số cho phép khi căn giữa (pixel)