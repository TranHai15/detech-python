# ============================================
# FILE CẤU HÌNH TẬP TRUNG - FACE SERVER
# ============================================
# Tất cả các hằng số được khai báo ở đây để dễ quản lý và build

# ============================================
# 1. CẤU HÌNH SERVER & NETWORK
# ============================================
# Port của face-server
SERVER_PORT = 5000
SERVER_HOST = "0.0.0.0"  # 0.0.0.0 để chấp nhận kết nối từ mọi IP

# Base URL của server (dùng để tạo URL ảnh)
SERVER_BASE_URL = "http://localhost:5000"

# Danh sách các domain/port của Frontend được phép gọi API và Socket
FRONTEND_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173"
]

# Socket.IO Configuration
SOCKET_PING_TIMEOUT = 60
SOCKET_PING_INTERVAL = 25

# ============================================
# 2. CẤU HÌNH CAMERA RTSP
# ============================================
RTSP_URL = 'rtsp://admin:Promise%40123@192.168.100.62/ONVIF/MediaInput?profile=def_profile1'

# ============================================
# 3. CẤU HÌNH XỬ LÝ ẢNH/VIDEO
# ============================================
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FRAME_SLEEP_DELAY = 0.01  # Delay giữa các frame (giây)

# ============================================
# 4. CẤU HÌNH VÙNG AN TOÀN (SAFE ZONE)
# ============================================
ZONE_WIDTH = 180
ZONE_HEIGHT = 260
# Tự động tính toán căn giữa
ZONE_X = (FRAME_WIDTH - ZONE_WIDTH) // 2
ZONE_Y = (FRAME_HEIGHT - ZONE_HEIGHT) // 2

# ============================================
# 5. CẤU HÌNH LOGIC CHỤP ẢNH
# ============================================
REQUIRED_FRAMES = 30    # Số frame cần giữ yên để chụp (khoảng 0.5s)
MIN_FACE_RATIO = 0.6    # Tỷ lệ mặt tối thiểu (để tránh quá xa)
MAX_FACE_RATIO = 0.9    # Tỷ lệ mặt tối đa (để tránh quá gần)
CENTER_TOLERANCE = 50   # Sai số cho phép khi căn giữa (pixel)

# ============================================
# 6. CẤU HÌNH MEDIAPIPE FACE DETECTION
# ============================================
FACE_DETECTION_CONFIDENCE = 0.7  # Ngưỡng tin cậy phát hiện khuôn mặt (0-1)
FACE_DETECTION_MODEL = 0  # 0 = gần (2m), 1 = xa (5m)

# ============================================
# 7. CẤU HÌNH VẼ GIAO DIỆN
# ============================================
# Màu sắc (BGR format cho OpenCV)
COLOR_RED = (0, 0, 255)
COLOR_GREEN = (0, 255, 0)
COLOR_YELLOW = (0, 255, 255)
COLOR_WHITE = (255, 255, 255)

# Độ dày đường vẽ
THICKNESS_NORMAL = 2
THICKNESS_THICK = 4
THICKNESS_ELLIPSE = 6

# Độ trong suốt overlay
OVERLAY_ALPHA = 0.0

# Offset cho ellipse (khoảng cách từ viền zone)
ELLIPSE_OFFSET = 10

# ============================================
# 8. CẤU HÌNH THƯ MỤC & FILE
# ============================================
IMAGE_FOLDER = 'captured_faces'
IMAGE_PREFIX = 'face_'
IMAGE_EXTENSION = '.jpg'
