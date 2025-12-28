# --- START OF FILE main_player.py ---

import sys
import cv2
import mediapipe as mp
import numpy as np
import time

from PyQt5.QtMultimedia import QMediaPlayer
from PyQt5.QtWidgets import QApplication, QLabel
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QImage, QPixmap

from media_player_ui import VideoPlayer
from hand_helpers import get_str_guester


class HandTrackingThread(QThread):
    """
    运行手势识别的独立线程
    """
    frame_ready = pyqtSignal(QImage)
    gesture_detected = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._is_running = True
        self.last_gesture = " "

        self.cooldown_seconds = 1.0
        self.last_gesture_time = 0

    def run(self):
        """线程执行的核心代码"""
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)

        mp_hands = mp.solutions.hands
        hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7, min_tracking_confidence=0.7)
        mp_draw = mp.solutions.drawing_utils

        while self._is_running and cap.isOpened():
            success, img = cap.read()
            if not success:
                continue

            img = cv2.flip(img, 1)
            image_height, image_width, _ = np.shape(img)
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            results = hands.process(img_rgb)

            str_guester = " "
            if results.multi_hand_landmarks:
                # 在 hand_helpers.py 中已经处理了 list_lms 的 z 坐标，这里传递完整 landmarks
                hand_landmarks_for_logic = []
                for landmark in results.multi_hand_landmarks[0].landmark:
                    hand_landmarks_for_logic.append((landmark.x, landmark.y, landmark.z))

                hand = results.multi_hand_landmarks[0]
                mp_draw.draw_landmarks(img, hand, mp_hands.HAND_CONNECTIONS)

                list_lms = []
                for i in range(21):
                    pos_x = hand.landmark[i].x * image_width
                    pos_y = hand.landmark[i].y * image_height
                    # 为了绘制和旧逻辑兼容，我们只保留 x, y
                    list_lms.append([int(pos_x), int(pos_y)])

                # 使用完整的 landmarks (包含 z 轴) 进行手势判断
                list_lms_with_depth = []
                for i in range(21):
                    pos_x = hand.landmark[i].x
                    pos_y = hand.landmark[i].y
                    pos_z = hand.landmark[i].z
                    list_lms_with_depth.append([pos_x, pos_y, pos_z])

                list_lms_np = np.array(list_lms, dtype=np.int32)
                hull_index = [0, 1, 2, 3, 6, 10, 14, 19, 18, 17]
                hull = cv2.convexHull(list_lms_np[hull_index, :])

                ll = [4, 8, 12, 16, 20]
                up_fingers = []
                for i in ll:
                    pt = (int(list_lms_np[i][0]), int(list_lms_np[i][1]))
                    dist = cv2.pointPolygonTest(hull, pt, True)
                    if dist < 0:
                        up_fingers.append(i)

                # 注意：传递给 get_str_guester 的是带有深度的 list_lms_with_depth
                str_guester = get_str_guester(up_fingers, list_lms_with_depth)

                current_time = time.time()
                if str_guester != " " and str_guester != self.last_gesture and \
                        (current_time - self.last_gesture_time > self.cooldown_seconds):

                    self.gesture_detected.emit(str_guester)
                    self.last_gesture = str_guester
                    self.last_gesture_time = current_time

                elif str_guester == " ":
                    self.last_gesture = " "

            cv2.putText(img, ' %s' % (str_guester), (5, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 255), 2)

            rgb_image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)

            self.frame_ready.emit(qt_image)

        cap.release()
        print("手势识别线程已停止。")

    def stop(self):
        """停止线程"""
        self._is_running = False
        self.wait()


class GestureControlledPlayer(VideoPlayer):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("手势控制视频播放器")

        self.hand_thread = HandTrackingThread()
        self.hand_thread.frame_ready.connect(self.update_camera_feed)
        self.hand_thread.gesture_detected.connect(self.handle_gesture)
        self.hand_thread.start()

    def update_camera_feed(self, q_image):
        """更新摄像头画面，这里连接到父类的 self.camera_label"""
        pixmap = QPixmap.fromImage(q_image)
        scaled_pixmap = pixmap.scaled(self.camera_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.camera_label.setPixmap(scaled_pixmap)

    def handle_gesture(self, command):
        """根据手势指令控制播放器"""
        print(f"接收到指令: {command}")
        if self.player.mediaStatus() == QMediaPlayer.NoMedia:
            print("播放器未加载媒体，无法执行手势指令。")
            return

        if command == "Up":
            current_volume = self.player.volume()
            new_volume = min(current_volume + 10, 100)
            self.player.setVolume(new_volume)
            self.volume_slider.setValue(new_volume)
            print(f"音量: {new_volume}")
        elif command == "Down":
            current_volume = self.player.volume()
            new_volume = max(current_volume - 10, 0)
            self.player.setVolume(new_volume)
            self.volume_slider.setValue(new_volume)
            print(f"音量: {new_volume}")
        elif command == "Right":
            self.seek_relative(5000)
            print("快进 5秒")
        elif command == "Left":
            self.seek_relative(-5000)
            print("快退 5秒")

    def closeEvent(self, event):
        """关闭窗口时，确保线程也停止"""
        self.hand_thread.stop()
        # ### 新增代码：在此处添加打印信息 ###
        print("播放器线程已停止。")
        # ######################################
        super().closeEvent(event)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    player = GestureControlledPlayer()
    player.show()
    sys.exit(app.exec_())