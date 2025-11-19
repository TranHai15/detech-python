# app.py
from flask import Flask, Response, send_from_directory
from flask_socketio import SocketIO
from flask_cors import CORS
import cv2
import time
import os
import threading

# Import module cá nhân
from camera_service import CameraStream
from face_logic import FaceProcessor
import config as cfg

app = Flask(__name__)

# --- CẤU HÌNH CORS ĐẦY ĐỦ ---
# 1. CORS cho Flask (HTTP requests)
CORS(app,
     resources={r"/*": {
         "origins": ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173"],
         "methods": ["GET", "POST", "OPTIONS", "PUT", "DELETE"],
         "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
         "supports_credentials": True
     }})

# 2. CORS cho Socket.IO (WebSocket/Polling)
socketio = SocketIO(
    app,
    cors_allowed_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173"],
    async_mode='threading',
    allow_upgrades=True,
    ping_timeout=60,
    ping_interval=25
)

IMAGE_FOLDER = 'captured_faces'
if not os.path.exists(IMAGE_FOLDER):
    os.makedirs(IMAGE_FOLDER)

app_state = {
    "is_capturing": False
}

# --- CÁC SỰ KIỆN SOCKET ---

@socketio.on('start_capture')
def handle_start_capture():
    """React gửi sự kiện này khi bấm nút 'Bắt đầu'"""
    print("📢 Nhận lệnh: BẮT ĐẦU CHỤP!")
    app_state["is_capturing"] = True

@socketio.on('stop_capture')
def handle_stop_capture():
    """React gửi sự kiện này nếu muốn hủy bỏ"""
    print("📢 Nhận lệnh: HỦY CHỤP!")
    app_state["is_capturing"] = False

# --- API HTTP ---
@app.route('/images/<path:filename>')
def serve_image(filename):
    return send_from_directory(IMAGE_FOLDER, filename)

def generate_frames():
    camera = CameraStream()
    processor = FaceProcessor()

    if not camera.is_opened():
        yield (b'--frame\r\nContent-Type: text/plain\r\n\r\nError Connect Camera\r\n')
        return

    print("=> Server Ready. Waiting for 'start_capture' event...")

    while True:
        frame = camera.get_frame()
        if frame is None:
            time.sleep(0.01)
            continue

        # --- LOGIC QUYẾT ĐỊNH DỰA TRÊN TRẠNG THÁI ---

        if app_state["is_capturing"]:
            # === TRẠNG THÁI: ĐANG QUÉT (ACTIVE) ===
            # Chạy AI, vẽ khung xanh đỏ
            frame_drawn, face_image, status, message = processor.process_and_draw(frame)
            frame = frame_drawn

            # Gửi status và message qua Socket.IO để FE hiển thị
            socketio.emit('face_status', {
                'status': status,
                'message': message
            })

            # Nếu chụp được ảnh
            if face_image is not None:
                print("-> ✅ Đã chụp được ảnh!")

                # 1. Lưu ảnh
                filename = f"face_{int(time.time())}.jpg"
                filepath = os.path.join(IMAGE_FOLDER, filename)
                cv2.imwrite(filepath, face_image)

                # 2. Gửi Socket trả ảnh về React
                image_url = f"http://localhost:5000/images/{filename}"
                socketio.emit('capture_success', {'url': image_url})
                print(f"-> Gửi ảnh về Client: {image_url}")

                # 3. ĐÓNG LẠI NGAY LẬP TỨC (Auto Close)
                app_state["is_capturing"] = False
                print("-> Đã đóng chế độ chụp. Quay về Idle.")
                
                # Gửi status về idle
                socketio.emit('face_status', {
                    'status': 'idle',
                    'message': 'Chờ quét thẻ tiếp theo...'
                })

        else:
            # === TRẠNG THÁI: CHỜ (IDLE) ===
            # Chỉ hiện video sạch, không vẽ gì để FE tự hiển thị message
            # Không chạy processor.process_and_draw để tiết kiệm CPU

            # Reset bộ đếm của AI để lần sau bật lên là tính lại từ đầu
            processor.consecutive_success_frames = 0

        # Encode gửi video stream
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

        time.sleep(0.01)

    camera.release()

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# Thêm route để test CORS
@app.route('/test')
def test():
    return {"status": "ok", "message": "CORS is working"}

if __name__ == '__main__':
    print("🚀 Starting server on http://0.0.0.0:5000")
    print("📡 CORS enabled for: http://localhost:3000, http://127.0.0.1:3000, http://localhost:5173")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
