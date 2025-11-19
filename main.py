import base64
import time
import threading
import cv2
from flask import Flask, Response
from flask_socketio import SocketIO
from flask_cors import CORS

# --- IMPORT MODULE CÁ NHÂN ---
from camera_service import CameraStream
from face_logic import FaceProcessor
import config as cfg 

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

# Trạng thái toàn cục
app_state = {
    "is_capturing": False
}

# --- CÁC SỰ KIỆN SOCKET ---

@socketio.on('start_capture')
def handle_start_capture():
    """Client bấm nút 'Bắt đầu'"""
    print("📢 Socket: BẮT ĐẦU CHỤP!")
    app_state["is_capturing"] = True

@socketio.on('stop_capture')
def handle_stop_capture():
    """Client bấm nút 'Hủy' hoặc đóng modal"""
    print("📢 Socket: HỦY CHỤP!")
    app_state["is_capturing"] = False

# --- HÀM XỬ LÝ VIDEO STREAM ---

def generate_frames():
    camera = CameraStream()
    processor = FaceProcessor()

    # Kiểm tra kết nối camera
    if not camera.is_opened():
        yield (b'--frame\r\nContent-Type: text/plain\r\n\r\nError Connect Camera\r\n')
        return

    print("=> Server Ready. Waiting for 'start_capture' event...")

    while True:
        frame = camera.get_frame()
        if frame is None:
            time.sleep(0.01)
            continue

        # --- LOGIC XỬ LÝ ---
        
        if app_state["is_capturing"]:
            # === TRẠNG THÁI: ĐANG QUÉT ===
            # Xử lý AI, vẽ khung
            frame, face_image, status, message = processor.process_and_draw(frame)

            # Gửi status realtime về Client
            socketio.emit('face_status', {
                'status': status,
                'message': message
            })

            # KHI CHỤP ĐƯỢC ẢNH
            if face_image is not None:
                print("-> ✅ Đã chụp được khuôn mặt hợp lệ!")

                # 1. Chuyển đổi ảnh sang Base64 (Không lưu file)
                retval, buffer = cv2.imencode('.jpg', face_image)
                
                if retval:
                    jpg_as_text = base64.b64encode(buffer).decode('utf-8')
                    base64_string = f"data:image/jpeg;base64,{jpg_as_text}"

                    # 2. Gửi ảnh về Client
                    socketio.emit('capture_success', {'url': base64_string})
                    print(f"-> 📡 Đã gửi ảnh Base64 về Client (Size: {len(base64_string)})")

                # 3. Reset trạng thái về Idle ngay lập tức
                app_state["is_capturing"] = False
                processor.consecutive_success_frames = 0 # Reset bộ đếm AI
                
                # Gửi thông báo về trạng thái chờ
                socketio.emit('face_status', {
                    'status': 'idle',
                    'message': 'Chờ quét thẻ tiếp theo...'
                })
                print("-> 🛑 Đã tự động đóng chế độ chụp.")

        else:
            # === TRẠNG THÁI: IDLE (CHỜ) ===
            # Reset bộ đếm để lần sau quét lại từ đầu
            if processor.consecutive_success_frames > 0:
                processor.consecutive_success_frames = 0
            
            # Không gọi process_and_draw để frame sạch, tiết kiệm CPU

        # --- STREAM HÌNH ẢNH VỀ TRÌNH DUYỆT ---
        ret, buffer = cv2.imencode('.jpg', frame)
        if ret:
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        time.sleep(cfg.FRAME_SLEEP_DELAY)

    # Khi vòng lặp kết thúc (nếu có cơ chế break)
    camera.release()

# --- ROUTES HTTP ---

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/test')
def test():
    return {"status": "ok", "message": "Server is running & CORS enabled"}

# --- MAIN ---
if __name__ == '__main__':
    print(f"🚀 Starting server on http://{cfg.SERVER_HOST}:{cfg.SERVER_PORT}")
    socketio.run(app, host=cfg.SERVER_HOST, port=cfg.SERVER_PORT, debug=True, allow_unsafe_werkzeug=True)