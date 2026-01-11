import sys
import cv2
import mediapipe as mp
import numpy as np
import time

from PyQt5.QtMultimedia import QMediaPlayer
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QImage, QPixmap

from ui import VideoPlayer
from hand import get_gesture_state


class HandTrackingThread(QThread):
    frame_ready = pyqtSignal(QImage)
    gesture_detected = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self._is_running = True

        self.last_mode = "NONE"
        self.last_action = None
        self.last_trigger_time = 0

        # 连续触发的时间间隔 (秒)，想要1秒4次就将数值改为0.25
        self.continuous_interval = 0.33

    def run(self):
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)

        mp_hands = mp.solutions.hands
        hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7, min_tracking_confidence=0.5)
        mp_draw = mp.solutions.drawing_utils

        while self._is_running and cap.isOpened():
            success, img = cap.read()
            if not success:
                continue

            img = cv2.flip(img, 1)
            h, w, _ = img.shape
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            results = hands.process(img_rgb)

            current_mode = "NONE"
            current_action = None

            if results.multi_hand_landmarks:
                hand = results.multi_hand_landmarks[0]
                mp_draw.draw_landmarks(img, hand, mp_hands.HAND_CONNECTIONS)

                list_lms_depth = []
                list_lms_pixel = []
                for lm in hand.landmark:
                    list_lms_depth.append([lm.x, lm.y, lm.z])
                    list_lms_pixel.append([int(lm.x * w), int(lm.y * h)])

                list_lms_np = np.array(list_lms_pixel, dtype=np.int32)
                hull_index = [0, 1, 2, 3, 6, 10, 14, 19, 18, 17]
                hull = cv2.convexHull(list_lms_np[hull_index, :])

                up_fingers = []
                tips = [4, 8, 12, 16, 20]
                for i in tips:
                    pt = (int(list_lms_pixel[i][0]), int(list_lms_pixel[i][1]))
                    dist = cv2.pointPolygonTest(hull, pt, True)
                    if dist < 0:
                        up_fingers.append(i)

                current_mode, current_action = get_gesture_state(up_fingers, list_lms_depth)

            # === 核心交互逻辑 ===
            now = time.time()
            should_emit = False

            if current_mode != "NONE" and current_action is not None:
                # 1. 状态改变 -> 立即触发
                if (current_mode != self.last_mode) or (current_action != self.last_action):
                    should_emit = True
                    self.last_trigger_time = now

                # 2. 状态不变且为 CONTINUE 模式 -> 连续触发
                #    <--- 修改判断条件为 "CONTINUE"
                elif current_mode == "CONTINUE":
                    if now - self.last_trigger_time > self.continuous_interval:
                        should_emit = True
                        self.last_trigger_time = now

            self.last_mode = current_mode
            self.last_action = current_action

            if should_emit:
                self.gesture_detected.emit(current_mode, current_action)

            # === OSD 显示调试信息 (修改部分) ===
            if current_action:
                display_text = f"{current_mode}: {current_action}"
                # 修改点：
                # 1. 位置 (10, 40) - 稍微下移适应大字体
                # 2. 字体比例 1.2 - 增大
                # 3. 颜色 (0, 0, 255) - 红色 (OpenCV是BGR格式)
                # 4. 线宽 3 - 加粗
                cv2.putText(img, display_text, (10, 40), cv2.FONT_HERSHEY_SIMPLEX,
                            1.2, (0, 0, 255), 3)

            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            qt_img = QImage(rgb_img.data, w, h, w * 3, QImage.Format_RGB888)
            self.frame_ready.emit(qt_img)

        cap.release()
        hands.close()

    def stop(self):
        self._is_running = False
        self.wait()


class GestureControlledPlayer(VideoPlayer):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("手势播放器")

        self.hand_thread = HandTrackingThread()
        self.hand_thread.frame_ready.connect(self.update_camera_feed)
        self.hand_thread.gesture_detected.connect(self.handle_gesture_command)
        self.hand_thread.start()

    def update_camera_feed(self, q_image):
        pixmap = QPixmap.fromImage(q_image)
        scaled_pixmap = pixmap.scaled(self.camera_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.camera_label.setPixmap(scaled_pixmap)

    def handle_gesture_command(self, mode, action):
        """
        处理手势指令
        mode: ONCE, CONTINUE, FIST, PALM
        """
        print(f"执行指令: [{mode}] {action}")

        if mode == "FIST" and action == "Pause":
            if self.player.state() == QMediaPlayer.PlayingState:
                self.player.pause()
                self.video_widget.show_osd("⏸", "握拳暂停")

        elif mode == "PALM" and action == "Play":
            if self.player.state() != QMediaPlayer.PlayingState:
                self.player.play()
                self.video_widget.show_osd("▶", "张手播放")

        # <--- 修改这里，匹配新的字符串 "ONCE" 和 "CONTINUE"
        elif mode in ["ONCE", "CONTINUE"]:

            # 双指连续模式显示火箭图标
            prefix = "🚀" if mode == "CONTINUE" else ""

            if action == "Up":
                vol = min(self.player.volume() + 5, 100)
                self.set_volume(vol)
                self.video_widget.show_osd("🔊", f"{prefix}{vol}%")

            elif action == "Down":
                vol = max(self.player.volume() - 5, 0)
                self.set_volume(vol)
                icon = "🔉" if vol > 0 else "🔇"
                self.video_widget.show_osd(icon, f"{prefix}{vol}%")

            elif action == "Right":
                self.seek_relative(5000)
                self.video_widget.show_osd("⏩", f"{prefix}+5s")

            elif action == "Left":
                self.seek_relative(-5000)
                self.video_widget.show_osd("⏪", f"{prefix}-5s")

    def closeEvent(self, event):
        self.hand_thread.stop()
        super().closeEvent(event)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    player = GestureControlledPlayer()
    player.show()
    sys.exit(app.exec_())