# face_logic.py
import cv2
import mediapipe as mp
import config as cfg


class FaceProcessor:
    def __init__(self):
        # Khởi tạo MediaPipe
        self.mp_face_detection = mp.solutions.face_detection
        # model_selection=0 dùng cho khoảng cách gần (trong vòng 2 mét), 1 là cho xa (5 mét)
        self.face_detection = self.mp_face_detection.FaceDetection(
            min_detection_confidence=0.7, model_selection=0)

        self.consecutive_success_frames = 0

    def is_face_in_zone(self, bbox):
        """
        Kiểm tra xem tâm khuôn mặt có nằm trong vùng Safe Zone hay không
        """
        # Chuyển toạ độ tương đối (0-1) sang pixel
        real_x = int(bbox.xmin * cfg.FRAME_WIDTH)
        real_y = int(bbox.ymin * cfg.FRAME_HEIGHT)
        real_w = int(bbox.width * cfg.FRAME_WIDTH)
        real_h = int(bbox.height * cfg.FRAME_HEIGHT)

        # Tính tâm khuôn mặt
        center_x = real_x + real_w // 2
        center_y = real_y + real_h // 2

        # Tính giới hạn của vùng Zone
        zone_left = cfg.ZONE_X
        zone_right = cfg.ZONE_X + cfg.ZONE_WIDTH
        zone_top = cfg.ZONE_Y
        zone_bottom = cfg.ZONE_Y + cfg.ZONE_HEIGHT

        # KIỂM TRA: Tâm mặt có lọt trong hình chữ nhật của Zone không?
        if (zone_left < center_x < zone_right) and (zone_top < center_y < zone_bottom):
            return True
        return False

    def check_quality_rules(self, bbox):
        """
        Kiểm tra các luật khắt khe (Khoảng cách, Căn giữa chuẩn)
        Chỉ chạy hàm này khi mặt đã nằm trong Zone.
        """
        real_x = int(bbox.xmin * cfg.FRAME_WIDTH)
        real_w = int(bbox.width * cfg.FRAME_WIDTH)

        face_center_x = real_x + real_w // 2
        zone_center_x = cfg.ZONE_X + cfg.ZONE_WIDTH // 2

        # 1. Kiểm tra độ lệch tâm (Center Tolerance)
        if abs(face_center_x - zone_center_x) > cfg.CENTER_TOLERANCE:
            return False, "Vui lòng di chuyển vào khung hình"

        # 2. Kiểm tra tỷ lệ xa gần (Ratio)
        ratio = real_w / cfg.ZONE_WIDTH
        if ratio < cfg.MIN_FACE_RATIO:
            return False, "Vui lòng lại gần hơn"
        if ratio > cfg.MAX_FACE_RATIO:
            return False, "Vui lòng ra xa hơn"

        return True, "Vui lòng giữ nguyên"

    def process_and_draw(self, frame):
        frame_drawn = frame.copy()
        cropped_image = None

        results = self.face_detection.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        message = "Vui lòng di chuyển vào khung hình"
        status = "waiting"  # waiting, adjusting, ready, capturing
        color = (0, 0, 255)  # Đỏ
        thickness = 2

        target_face = None  # Khuôn mặt được chọn để xử lý

        if results.detections:
            # --- BƯỚC 1: LỌC (FILTERING) ---
            # Chỉ lấy những khuôn mặt có tâm nằm trong khung xanh
            faces_inside_zone = []

            for detection in results.detections:
                bbox = detection.location_data.relative_bounding_box
                if self.is_face_in_zone(bbox):
                    faces_inside_zone.append(detection)

            # --- BƯỚC 2: XỬ LÝ DỰA TRÊN SỐ LƯỢNG TRONG ZONE ---
            if len(faces_inside_zone) == 0:
                message = "Vui lòng di chuyển vào khung hình"
                status = "waiting"
                self.consecutive_success_frames = 0

            elif len(faces_inside_zone) > 1:
                # Có 2 người chen chúc trong cái khung bé tí
                message = "Vui lòng thực hiện đăng ký lần lượt"
                status = "error"
                self.consecutive_success_frames = 0

            else:  # Chính xác là 1 người trong Zone
                target_face = faces_inside_zone[0]
                bbox = target_face.location_data.relative_bounding_box

                # --- BƯỚC 3: KIỂM TRA CHẤT LƯỢNG (XA/GẦN/CĂN GIỮA) ---
                is_valid, msg = self.check_quality_rules(bbox)
                message = msg
                status = "adjusting" if not is_valid else "ready"

                if is_valid:
                    color = (0, 255, 0)  # Xanh
                    thickness = 4
                    self.consecutive_success_frames += 1

                    if self.consecutive_success_frames >= cfg.REQUIRED_FRAMES:
                        message = "Đã chụp xong!"
                        status = "capturing"

                        # CẮT ẢNH
                        y1 = max(0, cfg.ZONE_Y)
                        y2 = cfg.ZONE_Y + cfg.ZONE_HEIGHT
                        x1 = max(0, cfg.ZONE_X)
                        x2 = cfg.ZONE_X + cfg.ZONE_WIDTH
                        cropped_image = frame[y1:y2, x1:x2]

                        self.consecutive_success_frames = 0
                else:
                    color = (0, 255, 255)  # Vàng
                    self.consecutive_success_frames = 0

        else:
            status = "waiting"
            self.consecutive_success_frames = 0

        # --- VẼ GIAO DIỆN (CHỈ VẼ KHUNG, KHÔNG VẼ TEXT) ---
        # ====== TẠO OVERLAY ĐỂ VẼ TRONG SUỐT ======
        overlay = frame_drawn.copy()

        # Vẽ hình chữ nhật đầy (fill) lên overlay để tạo nền trong suốt
        cv2.rectangle(
            overlay,
            (cfg.ZONE_X, cfg.ZONE_Y),
            (cfg.ZONE_X + cfg.ZONE_WIDTH, cfg.ZONE_Y + cfg.ZONE_HEIGHT),
            (255, 255, 255),  # màu
            -1  # fill
        )

        # Độ trong suốt
        alpha = 0.0

        # Blend overlay vào frame_drawn → tạo nền trong suốt
        frame_drawn = cv2.addWeighted(overlay, alpha, frame_drawn, 1 - alpha, 0)

        # ====== KHÔNG VẼ VIỀN RECTANGLE ======
        # (bỏ hẳn đoạn vẽ viền rectangle)

        # ====== CHỈ VẼ ELLIPSE (HIỆN ĐẦY ĐỦ) ======
        ellipse_center_x = cfg.ZONE_X + cfg.ZONE_WIDTH // 2
        ellipse_center_y = cfg.ZONE_Y + cfg.ZONE_HEIGHT // 2
        ellipse_axes_x = cfg.ZONE_WIDTH // 2 - 10
        ellipse_axes_y = cfg.ZONE_HEIGHT // 2 - 10

        cv2.ellipse(
            frame_drawn,
            (ellipse_center_x, ellipse_center_y),
            (ellipse_axes_x, ellipse_axes_y),
            0, 0, 360, color, 6
        )
        # Không vẽ text trên video nữa, sẽ gửi qua Socket.IO
        # cv2.rectangle(frame_drawn, (0, 0), (cfg.FRAME_WIDTH, 60), (0, 0, 0), -1)
        # cv2.putText(frame_drawn, message, (20, 40),
        #             cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

        return frame_drawn, cropped_image, status, message