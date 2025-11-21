import cv2
import mediapipe as mp
import numpy as np
import config as cfg


class FaceProcessor:
    def __init__(self):
        # Khởi tạo MediaPipe
        self.mp_face_detection = mp.solutions.face_detection
        self.face_detection = self.mp_face_detection.FaceDetection(
            min_detection_confidence=cfg.FACE_DETECTION_CONFIDENCE,
            model_selection=cfg.FACE_DETECTION_MODEL)

        self.consecutive_success_frames = 0

        # --- KHỞI TẠO ICON ---
        # Load ảnh gốc (Ví dụ ảnh gốc màu trắng hoặc đen đều được)
        self.icon_img = cv2.imread(cfg.ICON_PATH, cv2.IMREAD_UNCHANGED)
        self.icon_resized = None

        if self.icon_img is None:
            print(f"[WARNING] Không tìm thấy file ảnh tại: {cfg.ICON_PATH}")
        else:
            # Resize một lần duy nhất lúc khởi tạo

            # --- [THAY ĐỔI Ở ĐÂY] Tăng kích thước lên 1.7 lần ---
            # Chúng ta nhân thêm 1.7 vào công thức tính chiều cao mục tiêu
            target_h = int(cfg.ZONE_HEIGHT * cfg.ICON_SCALE_RATIO * 2)

            h_orig, w_orig = self.icon_img.shape[:2]
            aspect_ratio = w_orig / h_orig
            target_w = int(target_h * aspect_ratio)

            # Lưu ý: Nếu kích thước quá to có thể bị tràn ra ngoài màn hình,
            # code vẽ bên dưới đã có phần xử lý cắt (crop) để tránh lỗi.
            self.icon_resized = cv2.resize(self.icon_img, (target_w, target_h), interpolation=cv2.INTER_AREA)
            self.icon_h, self.icon_w = self.icon_resized.shape[:2]
            print(f"Icon mới đã resize: {self.icon_w}x{self.icon_h}")

    def recolor_icon(self, icon_bgra, target_color_bgr):
        """
        Hàm đổi màu icon nhưng giữ nguyên độ trong suốt.
        icon_bgra: Ảnh icon gốc (4 kênh màu)
        target_color_bgr: Màu muốn đổi sang (Blue, Green, Red)
        """
        if icon_bgra is None: return None

        # Tạo một bản sao để không làm hỏng ảnh gốc trong bộ nhớ
        colored_icon = icon_bgra.copy()

        # Tách kênh Alpha (độ trong suốt - kênh thứ 4)
        alpha_channel = colored_icon[:, :, 3]

        # Tạo mặt nạ: Những chỗ nào có hình (alpha > 0)
        mask = alpha_channel > 0

        # Gán màu mới vào 3 kênh màu (BGR) chỉ tại những điểm có hình
        colored_icon[mask, 0] = target_color_bgr[0]  # Blue
        colored_icon[mask, 1] = target_color_bgr[1]  # Green
        colored_icon[mask, 2] = target_color_bgr[2]  # Red

        return colored_icon

    # ... (Giữ nguyên các hàm is_face_in_zone và check_quality_rules cũ) ...
    def is_face_in_zone(self, bbox):
        real_x = int(bbox.xmin * cfg.FRAME_WIDTH)
        real_y = int(bbox.ymin * cfg.FRAME_HEIGHT)
        real_w = int(bbox.width * cfg.FRAME_WIDTH)
        real_h = int(bbox.height * cfg.FRAME_HEIGHT)
        center_x = real_x + real_w // 2
        center_y = real_y + real_h // 2
        zone_left = cfg.ZONE_X
        zone_right = cfg.ZONE_X + cfg.ZONE_WIDTH
        zone_top = cfg.ZONE_Y
        zone_bottom = cfg.ZONE_Y + cfg.ZONE_HEIGHT
        if (zone_left < center_x < zone_right) and (zone_top < center_y < zone_bottom):
            return True
        return False

    def check_quality_rules(self, bbox):
        real_x = int(bbox.xmin * cfg.FRAME_WIDTH)
        real_w = int(bbox.width * cfg.FRAME_WIDTH)
        face_center_x = real_x + real_w // 2
        zone_center_x = cfg.ZONE_X + cfg.ZONE_WIDTH // 2

        if abs(face_center_x - zone_center_x) > cfg.CENTER_TOLERANCE:
            return False, "Vui lòng di chuyển vào giữa"

        ratio = real_w / cfg.ZONE_WIDTH
        if ratio < cfg.MIN_FACE_RATIO:
            return False, "Vui lòng lại gần hơn"
        if ratio > cfg.MAX_FACE_RATIO:
            return False, "Vui lòng ra xa hơn"
        return True, "Vui lòng giữ nguyên"

    # def process_and_draw(self, frame):
    #     frame_drawn = frame.copy()
    #     cropped_image = None
    #
    #     results = self.face_detection.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    #
    #     message = "Vui lòng di chuyển vào khung hình"
    #     status = "waiting"
    #
    #     # Mặc định là màu đỏ hoặc trắng tuỳ bạn chọn cho trạng thái chờ
    #     color = cfg.COLOR_RED
    #
    #     if results.detections:
    #         faces_inside_zone = []
    #         for detection in results.detections:
    #             bbox = detection.location_data.relative_bounding_box
    #             if self.is_face_in_zone(bbox):
    #                 faces_inside_zone.append(detection)
    #
    #         if len(faces_inside_zone) == 0:
    #             message = "Vui lòng di chuyển vào khung hình"
    #             status = "waiting"
    #             self.consecutive_success_frames = 0
    #             color = cfg.COLOR_RED  # Không có mặt -> Đỏ
    #
    #         elif len(faces_inside_zone) > 1:
    #             message = "Vui lòng thực hiện lần lượt"
    #             status = "error"
    #             self.consecutive_success_frames = 0
    #             color = cfg.COLOR_RED  # Lỗi -> Đỏ
    #
    #         else:
    #             target_face = faces_inside_zone[0]
    #             bbox = target_face.location_data.relative_bounding_box
    #             is_valid, msg = self.check_quality_rules(bbox)
    #             message = msg
    #             status = "adjusting" if not is_valid else "ready"
    #
    #             if is_valid:
    #                 color = cfg.COLOR_GREEN  # Thành công -> Xanh
    #                 self.consecutive_success_frames += 1
    #                 if self.consecutive_success_frames >= cfg.REQUIRED_FRAMES:
    #                     message = "Đã chụp xong!"
    #                     status = "capturing"
    #                     y1 = max(0, cfg.ZONE_Y)
    #                     y2 = cfg.ZONE_Y + cfg.ZONE_HEIGHT
    #                     x1 = max(0, cfg.ZONE_X)
    #                     x2 = cfg.ZONE_X + cfg.ZONE_WIDTH
    #                     cropped_image = frame[y1:y2, x1:x2]
    #                     self.consecutive_success_frames = 0
    #             else:
    #                 color = cfg.COLOR_YELLOW  # Cần điều chỉnh -> Vàng
    #                 self.consecutive_success_frames = 0
    #     else:
    #         status = "waiting"
    #         color = cfg.COLOR_RED  # Không phát hiện gì -> Đỏ
    #         self.consecutive_success_frames = 0
    #
    #     # --- VẼ GIAO DIỆN ---
    #
    #     # 1. Nền mờ
    #     overlay = frame_drawn.copy()
    #     cv2.rectangle(overlay, (cfg.ZONE_X, cfg.ZONE_Y),
    #                   (cfg.ZONE_X + cfg.ZONE_WIDTH, cfg.ZONE_Y + cfg.ZONE_HEIGHT),
    #                   cfg.COLOR_WHITE, -1)
    #     frame_drawn = cv2.addWeighted(overlay, cfg.OVERLAY_ALPHA, frame_drawn, 1 - cfg.OVERLAY_ALPHA, 0)
    #
    #     # 2. Vẽ Icon đã được TÔ MÀU theo biến `color`
    #     if self.icon_resized is not None:
    #         # --- [BƯỚC MỚI] ĐỔI MÀU ICON ---
    #         # Gọi hàm đổi màu dựa trên biến color hiện tại
    #         current_icon = self.recolor_icon(self.icon_resized, color)
    #
    #         # Tính toán vị trí vẽ (như cũ)
    #         zone_center_x = cfg.ZONE_X + cfg.ZONE_WIDTH // 2
    #         zone_center_y = cfg.ZONE_Y + cfg.ZONE_HEIGHT // 2
    #         pos_x = zone_center_x - self.icon_w // 2
    #         pos_y = zone_center_y - self.icon_h // 2
    #
    #         y1, y2 = max(0, pos_y), min(frame_drawn.shape[0], pos_y + self.icon_h)
    #         x1, x2 = max(0, pos_x), min(frame_drawn.shape[1], pos_x + self.icon_w)
    #
    #         if y1 < y2 and x1 < x2:
    #             icon_crop_y1 = y1 - pos_y
    #             icon_crop_y2 = icon_crop_y1 + (y2 - y1)
    #             icon_crop_x1 = x1 - pos_x
    #             icon_crop_x2 = icon_crop_x1 + (x2 - x1)
    #
    #             # Dùng icon đã tô màu (current_icon) thay vì icon gốc
    #             icon_slice = current_icon[icon_crop_y1:icon_crop_y2, icon_crop_x1:icon_crop_x2]
    #             bg_slice = frame_drawn[y1:y2, x1:x2]
    #
    #             # Trộn ảnh
    #             if icon_slice.shape[2] == 4:
    #                 alpha_mask = icon_slice[:, :, 3] / 255.0
    #                 alpha_inv = 1.0 - alpha_mask
    #                 for c in range(0, 3):
    #                     bg_slice[:, :, c] = (alpha_mask * icon_slice[:, :, c] +
    #                                          alpha_inv * bg_slice[:, :, c])
    #
    #     # 3. Vẽ Ellipse
    #     ellipse_center_x = cfg.ZONE_X + cfg.ZONE_WIDTH // 2
    #     ellipse_center_y = cfg.ZONE_Y + cfg.ZONE_HEIGHT // 2
    #     ellipse_axes_x = cfg.ZONE_WIDTH // 2 - cfg.ELLIPSE_OFFSET
    #     ellipse_axes_y = cfg.ZONE_HEIGHT // 2 - cfg.ELLIPSE_OFFSET
    #
    #     cv2.ellipse(frame_drawn, (ellipse_center_x, ellipse_center_y),
    #                 (ellipse_axes_x, ellipse_axes_y), 0, 0, 360, color, cfg.THICKNESS_ELLIPSE)
    #
    #     return frame_drawn, cropped_image, status, message
    def process_and_draw(self, frame):
        frame_drawn = frame.copy()
        cropped_image = None

        results = self.face_detection.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        message = "Vui lòng di chuyển vào khung hình"
        status = "waiting"
        color = cfg.COLOR_RED

        if results.detections:
            faces_inside_zone = []
            for detection in results.detections:
                bbox = detection.location_data.relative_bounding_box
                if self.is_face_in_zone(bbox):
                    faces_inside_zone.append(detection)

            if len(faces_inside_zone) == 0:
                message = "Vui lòng di chuyển vào khung hình"
                status = "waiting"
                self.consecutive_success_frames = 0
                color = cfg.COLOR_RED

            elif len(faces_inside_zone) > 1:
                message = "Vui lòng thực hiện lần lượt"
                status = "error"
                self.consecutive_success_frames = 0
                color = cfg.COLOR_RED

            else:
                target_face = faces_inside_zone[0]
                bbox = target_face.location_data.relative_bounding_box
                is_valid, msg = self.check_quality_rules(bbox)
                message = msg
                status = "adjusting" if not is_valid else "ready"

                if is_valid:
                    color = cfg.COLOR_GREEN
                    self.consecutive_success_frames += 1
                    if self.consecutive_success_frames >= cfg.REQUIRED_FRAMES:
                        message = "Đã chụp xong!"
                        status = "capturing"
                        y1 = max(0, cfg.ZONE_Y)
                        y2 = cfg.ZONE_Y + cfg.ZONE_HEIGHT
                        x1 = max(0, cfg.ZONE_X)
                        x2 = cfg.ZONE_X + cfg.ZONE_WIDTH
                        cropped_image = frame[y1:y2, x1:x2]
                        self.consecutive_success_frames = 0
                else:
                    color = cfg.COLOR_YELLOW
                    self.consecutive_success_frames = 0
        else:
            status = "waiting"
            color = cfg.COLOR_RED
            self.consecutive_success_frames = 0

        # --- VẼ GIAO DIỆN ---

        # 1. Nền mờ (Giữ nguyên)
        overlay_bg = frame_drawn.copy()
        cv2.rectangle(overlay_bg, (cfg.ZONE_X, cfg.ZONE_Y),
                      (cfg.ZONE_X + cfg.ZONE_WIDTH, cfg.ZONE_Y + cfg.ZONE_HEIGHT),
                      cfg.COLOR_WHITE, -1)
        frame_drawn = cv2.addWeighted(overlay_bg, cfg.OVERLAY_ALPHA, frame_drawn, 1 - cfg.OVERLAY_ALPHA, 0)

        # 2. Vẽ Icon (Giữ nguyên)
        if self.icon_resized is not None:
            current_icon = self.recolor_icon(self.icon_resized, color)

            zone_center_x = cfg.ZONE_X + cfg.ZONE_WIDTH // 2
            zone_center_y = cfg.ZONE_Y + cfg.ZONE_HEIGHT // 2
            pos_x = zone_center_x - self.icon_w // 2
            pos_y = zone_center_y - self.icon_h // 2

            y1, y2 = max(0, pos_y), min(frame_drawn.shape[0], pos_y + self.icon_h)
            x1, x2 = max(0, pos_x), min(frame_drawn.shape[1], pos_x + self.icon_w)

            if y1 < y2 and x1 < x2:
                icon_crop_y1 = y1 - pos_y
                icon_crop_y2 = icon_crop_y1 + (y2 - y1)
                icon_crop_x1 = x1 - pos_x
                icon_crop_x2 = icon_crop_x1 + (x2 - x1)

                icon_slice = current_icon[icon_crop_y1:icon_crop_y2, icon_crop_x1:icon_crop_x2]
                bg_slice = frame_drawn[y1:y2, x1:x2]

                if icon_slice.shape[2] == 4:
                    alpha_mask = icon_slice[:, :, 3] / 255.0
                    alpha_inv = 1.0 - alpha_mask
                    for c in range(0, 3):
                        bg_slice[:, :, c] = (alpha_mask * icon_slice[:, :, c] +
                                             alpha_inv * bg_slice[:, :, c])

        # 3. Vẽ Ellipse (LOGIC VẪN CÒN NHƯNG ẨN ĐI)
        overlay_ellipse = frame_drawn.copy()

        ellipse_center_x = cfg.ZONE_X + cfg.ZONE_WIDTH // 2
        ellipse_center_y = cfg.ZONE_Y + cfg.ZONE_HEIGHT // 2
        ellipse_axes_x = cfg.ZONE_WIDTH // 2 - cfg.ELLIPSE_OFFSET
        ellipse_axes_y = cfg.ZONE_HEIGHT // 2 - cfg.ELLIPSE_OFFSET

        # Vẫn thực hiện lệnh vẽ vào lớp overlay
        cv2.ellipse(overlay_ellipse,
                    (ellipse_center_x, ellipse_center_y),
                    (ellipse_axes_x, ellipse_axes_y),
                    0, 0, 360,
                    (255, 255, 255),
                    cfg.THICKNESS_ELLIPSE)

        # --- [CHỈNH Ở ĐÂY] ---
        # Đặt alpha = 0 để nó hoàn toàn trong suốt (tàng hình)
        alpha_ellipse = 0

        # Hàm trộn ảnh sẽ lấy: 0% lớp Ellipse + 100% Lớp ảnh gốc => Kết quả là không thấy Ellipse
        frame_drawn = cv2.addWeighted(overlay_ellipse, alpha_ellipse, frame_drawn, 1 - alpha_ellipse, 0)

        return frame_drawn, cropped_image, status, message