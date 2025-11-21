import base64
import time
import threading
import cv2
import logging
from flask import Flask, Response
from flask_socketio import SocketIO
from flask_cors import CORS

# --- IMPORT MODULE CÁ NHÂN ---
from camera_service import CameraStream
from face_logic import FaceProcessor
import config as cfg

# --- SETUP LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- KHỞI TẠO FLASK & CONFIG ---
app = Flask(__name__)

# 1. Cấu hình CORS (HTTP)
CORS(app, resources={r"/*": {
    "origins": cfg.FRONTEND_ORIGINS,
    "methods": ["GET", "POST", "OPTIONS", "PUT", "DELETE"],
    "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
    "supports_credentials": True
}})

# 2. Cấu hình Socket.IO
socketio = SocketIO(
    app,
    cors_allowed_origins=cfg.FRONTEND_ORIGINS,
    async_mode='threading',
    allow_upgrades=True,
    ping_timeout=cfg.SOCKET_PING_TIMEOUT,
    ping_interval=cfg.SOCKET_PING_INTERVAL
)

# --- SINGLETON FACE PROCESSOR ---
# Tạo 1 instance duy nhất để tái sử dụng, tránh load model nhiều lần
_face_processor = None
_processor_lock = threading.Lock()

def get_face_processor():
    """Lấy singleton instance của FaceProcessor"""
    global _face_processor
    if _face_processor is None:
        with _processor_lock:
            if _face_processor is None:
                logger.info("🔄 Khởi tạo FaceProcessor (lần đầu)...")
                _face_processor = FaceProcessor()
                logger.info("✅ FaceProcessor đã sẵn sàng")
    return _face_processor

# --- TRẠNG THÁI TOÀN CỤC VỚI THREAD SAFETY ---
app_state = {
    "is_capturing": False
}
app_state_lock = threading.Lock()  # Lock để đảm bảo thread safety

def set_capturing(value):
    """Thread-safe setter cho is_capturing"""
    with app_state_lock:
        app_state["is_capturing"] = value

def get_capturing():
    """Thread-safe getter cho is_capturing"""
    with app_state_lock:
        return app_state["is_capturing"]

# --- CÁC SỰ KIỆN SOCKET ---

@socketio.on('start_capture')
def handle_start_capture():
    """Client bấm nút 'Bắt đầu'"""
    logger.info("📢 Socket: BẮT ĐẦU CHỤP!")
    set_capturing(True)
    
    # Reset counter khi bắt đầu capture
    processor = get_face_processor()
    with _processor_lock:
        processor.consecutive_success_frames = 0


@socketio.on('stop_capture')
def handle_stop_capture():
    """Client bấm nút 'Hủy' hoặc đóng modal"""
    logger.info("📢 Socket: HỦY CHỤP!")
    set_capturing(False)
    
    # Reset counter khi stop capture
    processor = get_face_processor()
    with _processor_lock:
        processor.consecutive_success_frames = 0
    
    # Gửi thông báo về trạng thái idle
    try:
        socketio.emit('face_status', {
            'status': 'idle',
            'message': 'Đã hủy chụp'
        })
    except Exception as e:
        logger.error(f"Lỗi khi emit face_status: {e}")


# --- HÀM XỬ LÝ VIDEO STREAM ---

def compress_image_for_base64(image, max_size_kb=200, quality=85):
    """
    Nén ảnh để giảm kích thước Base64
    
    Args:
        image: OpenCV image (numpy array)
        max_size_kb: Kích thước tối đa (KB)
        quality: JPEG quality (0-100)
    
    Returns:
        Base64 string hoặc None nếu lỗi
    """
    try:
        # Thử với quality ban đầu
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
        retval, buffer = cv2.imencode('.jpg', image, encode_params)
        
        if not retval:
            logger.error("Lỗi khi encode ảnh")
            return None
        
        # Kiểm tra kích thước
        size_kb = len(buffer) / 1024
        
        # Nếu quá lớn, giảm quality
        if size_kb > max_size_kb:
            quality = int(quality * (max_size_kb / size_kb))
            quality = max(30, quality)  # Không giảm quá thấp
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
            retval, buffer = cv2.imencode('.jpg', image, encode_params)
            if not retval:
                return None
        
        # Encode Base64
        jpg_as_text = base64.b64encode(buffer).decode('utf-8')
        base64_string = f"data:image/jpeg;base64,{jpg_as_text}"
        
        logger.info(f"📦 Ảnh đã nén: {len(base64_string) / 1024:.2f} KB")
        return base64_string
        
    except Exception as e:
        logger.error(f"Lỗi khi nén ảnh: {e}", exc_info=True)
        return None


def generate_frames():
    """
    Generator function để stream video frames
    Tự động quản lý camera và resource cleanup
    """
    camera = None
    processor = None
    
    try:
        # Khởi tạo camera
        camera = CameraStream()
        processor = get_face_processor()  # Sử dụng singleton

        # Kiểm tra kết nối camera
        if not camera.is_opened():
            error_msg = b'--frame\r\nContent-Type: text/plain\r\n\r\nError Connect Camera\r\n'
            yield error_msg
            return

        logger.info("=> Server Ready. Waiting for 'start_capture' event...")
        
        # Frame rate control
        target_fps = 30  # Giới hạn 30 FPS
        frame_interval = 1.0 / target_fps
        last_frame_time = 0

        while True:
            current_time = time.time()
            
            # Kiểm tra frame rate
            elapsed = current_time - last_frame_time
            if elapsed < frame_interval:
                time.sleep(frame_interval - elapsed)
            
            last_frame_time = time.time()
            
            # Đọc frame từ camera
            frame = camera.get_frame()
            if frame is None:
                time.sleep(0.01)
                continue

            # --- LOGIC XỬ LÝ ---
            is_capturing = get_capturing()

            if is_capturing:
                # === TRẠNG THÁI: ĐANG QUÉT ===
                try:
                    # Xử lý AI, vẽ khung
                    frame, face_image, status, message = processor.process_and_draw(frame)

                    # Gửi status realtime về Client
                    try:
                        socketio.emit('face_status', {
                            'status': status,
                            'message': message
                        })
                    except Exception as e:
                        logger.error(f"Lỗi khi emit face_status: {e}")

                    # KHI CHỤP ĐƯỢC ẢNH
                    if face_image is not None:
                        logger.info("-> ✅ Đã chụp được khuôn mặt hợp lệ!")

                        # Nén và encode ảnh
                        base64_string = compress_image_for_base64(face_image)
                        
                        if base64_string:
                            # Gửi ảnh về Client
                            try:
                                socketio.emit('capture_success', {'url': base64_string})
                                logger.info(f"-> 📡 Đã gửi ảnh Base64 về Client")
                            except Exception as e:
                                logger.error(f"Lỗi khi emit capture_success: {e}")

                        # Reset trạng thái về Idle ngay lập tức
                        set_capturing(False)
                        
                        # Reset bộ đếm AI
                        with _processor_lock:
                            processor.consecutive_success_frames = 0

                        # Gửi thông báo về trạng thái chờ
                        try:
                            socketio.emit('face_status', {
                                'status': 'idle',
                                'message': 'Vui lòng thử lại...'
                            })
                        except Exception as e:
                            logger.error(f"Lỗi khi emit face_status: {e}")
                        
                        logger.info("-> 🛑 Đã tự động đóng chế độ chụp.")

                except Exception as e:
                    logger.error(f"Lỗi trong quá trình xử lý face: {e}", exc_info=True)
                    # Tiếp tục stream ngay cả khi có lỗi

            else:
                # === TRẠNG THÁI: IDLE (CHỜ) ===
                # Reset bộ đếm để lần sau quét lại từ đầu
                with _processor_lock:
                    if processor.consecutive_success_frames > 0:
                        processor.consecutive_success_frames = 0

                # Không gọi process_and_draw để frame sạch, tiết kiệm CPU

            # --- STREAM HÌNH ẢNH VỀ TRÌNH DUYỆT ---
            try:
                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                if ret:
                    frame_bytes = buffer.tobytes()
                    yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            except Exception as e:
                logger.error(f"Lỗi khi encode frame: {e}")

    except GeneratorExit:
        # Client đã disconnect
        logger.info("Client đã disconnect, đang cleanup...")
    except Exception as e:
        logger.error(f"Lỗi nghiêm trọng trong generate_frames: {e}", exc_info=True)
    finally:
        # Cleanup resources
        if camera is not None:
            try:
                camera.release()
                logger.info("✅ Đã release camera")
            except Exception as e:
                logger.error(f"Lỗi khi release camera: {e}")


# --- ROUTES HTTP ---

@app.route('/video_feed')
def video_feed():
    """Endpoint để stream video"""
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/test')
def test():
    """Test endpoint"""
    return {"status": "ok", "message": "Server is running & CORS enabled"}


@app.route('/health')
def health():
    """Health check endpoint với camera status"""
    try:
        # Test camera connection
        test_camera = CameraStream()
        camera_ok = test_camera.is_opened()
        test_camera.release()
        
        return {
            "status": "ok",
            "camera": "connected" if camera_ok else "disconnected",
            "face_processor": "ready" if _face_processor is not None else "not_initialized"
        }
    except Exception as e:
        logger.error(f"Lỗi trong health check: {e}")
        return {
            "status": "error",
            "message": str(e)
        }, 500


# --- MAIN ---
if __name__ == '__main__':
    logger.info(f"🚀 Starting server on http://{cfg.SERVER_HOST}:{cfg.SERVER_PORT}")
    
    # Pre-initialize FaceProcessor để tránh delay lần đầu
    logger.info("🔄 Pre-initializing FaceProcessor...")
    get_face_processor()
    
    socketio.run(app, host=cfg.SERVER_HOST, port=cfg.SERVER_PORT, debug=True, allow_unsafe_werkzeug=True)
