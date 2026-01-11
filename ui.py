import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QSlider, QLabel,
                             QFileDialog, QStyle, QListWidget, QListWidgetItem,
                             QMenu, QAction, QActionGroup, QFrame)
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtCore import Qt, QUrl, QTimer, pyqtSignal, QPoint, QSize


# === 1. OSD 控件 (默认显示 1秒) ===
class OSDWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(160, 100)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.setStyleSheet("""
            QWidget {
                background-color: rgba(0, 0, 0, 180);
                border-radius: 12px;
            }
            QLabel {
                color: white;
                background-color: transparent;
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
                font-weight: bold;
            }
        """)

        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setStyleSheet("font-size: 40px;")
        layout.addWidget(self.icon_label)

        self.text_label = QLabel()
        self.text_label.setAlignment(Qt.AlignCenter)
        self.text_label.setStyleSheet("font-size: 20px;")
        layout.addWidget(self.text_label)

        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide)

    def show_message(self, icon_text, message, duration=600):
        self.icon_label.setText(icon_text)
        self.text_label.setText(message)
        self.show()
        self.raise_()
        self.hide_timer.start(duration)


# === 2. 可点击进度条 ===
class ClickableSlider(QSlider):
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            val = self.style().sliderValueFromPosition(
                self.minimum(), self.maximum(),
                event.x(), self.width()
            )
            self.setValue(val)
            self.sliderMoved.emit(val)
        super().mousePressEvent(event)


# === 3. 视频窗口 (集成 OSD) ===
class FullScreenVideoWidget(QVideoWidget):
    doubleClicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.osd = OSDWidget(self)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.doubleClicked.emit()
        super().mouseDoubleClickEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.osd.move(
            (self.width() - self.osd.width()) // 2,
            (self.height() - self.osd.height()) // 2
        )

    def show_osd(self, icon, text):
        self.osd.show_message(icon, text)


# === 4. 音量弹出条窗口 ===
class VolumePopup(QWidget):
    volumeChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(60, 160)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 10)
        layout.setSpacing(5)

        self.bg_widget = QWidget(self)
        self.bg_widget.setObjectName("VolumePopupBg")
        self.bg_widget.setStyleSheet("""
            #VolumePopupBg {
                background-color: #151515;
                border: 1px solid #333;
                border-radius: 6px;
            }
        """)
        bg_layout = QVBoxLayout(self.bg_widget)
        bg_layout.setContentsMargins(0, 10, 0, 15)

        self.label = QLabel("100")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("color: #e0e0e0; font-size: 14px; background: transparent; border: none;")
        bg_layout.addWidget(self.label)

        self.slider = QSlider(Qt.Vertical)
        self.slider.setRange(0, 100)
        self.slider.setCursor(Qt.PointingHandCursor)
        self.slider.setFocusPolicy(Qt.NoFocus)
        self.slider.setStyleSheet("""
            QSlider::groove:vertical {
                background: #3e3e3e;
                width: 6px;
                border-radius: 3px;
            }
            QSlider::add-page:vertical {
                background: #00aaff;
                border-radius: 3px;
            }
            QSlider::sub-page:vertical {
                background: #3e3e3e;
                border-radius: 3px;
            }
            QSlider::handle:vertical {
                background: #00aaff;
                height: 16px;
                width: 16px;
                margin: 0 -5px;
                border-radius: 8px;
            }
        """)
        self.slider.valueChanged.connect(self.on_slider_value_changed)
        bg_layout.addWidget(self.slider, 0, Qt.AlignHCenter)

        layout.addWidget(self.bg_widget)

    def on_slider_value_changed(self, value):
        self.label.setText(str(value))
        self.volumeChanged.emit(value)

    def set_volume(self, value):
        self.slider.blockSignals(True)
        self.slider.setValue(value)
        self.label.setText(str(value))
        self.slider.blockSignals(False)


# === 5. 音量按钮 ===
class VolumeButton(QPushButton):
    volumeChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIcon(QApplication.style().standardIcon(QStyle.SP_MediaVolume))
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(40, 30)
        self.setFocusPolicy(Qt.NoFocus)

        self.popup = VolumePopup(self)
        self.popup.hide()
        self.popup.volumeChanged.connect(self.volumeChanged)

        self.hide_timer = QTimer(self)
        self.hide_timer.setInterval(200)
        self.hide_timer.timeout.connect(self.check_hide)

    def enterEvent(self, event):
        self.hide_timer.stop()
        if not self.popup.isVisible():
            self.show_popup()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hide_timer.start()
        super().leaveEvent(event)

    def show_popup(self):
        global_pos = self.mapToGlobal(QPoint(0, 0))
        x = global_pos.x() + (self.width() - self.popup.width()) // 2
        y = global_pos.y() - self.popup.height() + 5
        self.popup.move(x, y)
        self.popup.show()

    def check_hide(self):
        if not self.underMouse() and not self.popup.underMouse():
            self.popup.hide()
            self.hide_timer.stop()

    def set_value(self, value):
        if value == 0:
            self.setIcon(self.style().standardIcon(QStyle.SP_MediaVolumeMuted))
        else:
            self.setIcon(self.style().standardIcon(QStyle.SP_MediaVolume))
        self.popup.set_volume(value)


# === 6. 悬停菜单按钮 ===
class HoverMenuButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.NoFocus)

    def enterEvent(self, event):
        if self.menu():
            self.showMenu()
        super().enterEvent(event)


class VideoPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyQt5 视频播放器")
        self.resize(1000, 600)

        self.setStyleSheet("QMainWindow { background-color: #1e1e1e; }")
        self.setFocusPolicy(Qt.StrongFocus)

        self.playlist = []
        self.current_index = -1
        self.sidebar_is_visible = True
        self.sidebar_width = 260
        self.video_duration = 0
        self.last_volume = 50

        self.player = QMediaPlayer(None, QMediaPlayer.VideoSurface)

        self.init_ui_components()

        self.player.setVideoOutput(self.video_widget)

        self.player.stateChanged.connect(self.media_state_changed)
        self.player.positionChanged.connect(self.position_changed)
        self.player.durationChanged.connect(self.duration_changed)
        self.player.error.connect(self.handle_errors)
        self.player.mediaStatusChanged.connect(self.media_status_changed)

        self.player.setVolume(100)
        self.btn_volume.set_value(100)

    def init_ui_components(self):
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        # --- A. 视频层 ---
        self.video_widget = FullScreenVideoWidget(self.central_widget)
        self.video_widget.doubleClicked.connect(self.toggle_fullscreen_mode)

        p = self.video_widget.palette()
        p.setColor(self.video_widget.backgroundRole(), Qt.black)
        self.video_widget.setPalette(p)

        # --- B. 底部控制栏 ---
        self.controls_widget = QWidget(self.central_widget)

        controls_style = """
            QWidget {
                background-color: #2b2b2b;
                color: #f0f0f0;
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
            }
            QPushButton {
                background-color: #505050;
                border: none;
                border-radius: 6px;
                padding: 3px 15px;
                color: white;
                font-size: 14px;
                min-height: 18px;
            }
            QPushButton:hover {
                background-color: #606060;
            }
            QPushButton:pressed {
                background-color: #404040;
            }
            QPushButton:disabled {
                background-color: #333333;
                color: #777777;
            }
            QPushButton::menu-indicator {
                image: none;
                width: 0px; 
            }
            QMenu {
                background-color: #151515; 
                border: 1px solid #333333;
                color: #f0f0f0;
                padding: 4px;
                border-radius: 6px;
            }
            QMenu::item {
                padding: 8px 30px; 
                background-color: transparent;
                font-size: 16px; 
                border-radius: 4px;
                margin: 2px 4px;
            }
            QMenu::item:selected {
                background-color: #333333; 
            }
            QMenu::item:checked {
                color: #3399ff; 
                font-weight: bold;
            }
            QMenu::indicator {
                width: 0px;
                height: 0px;
                image: none;
            }
            QSlider::groove:horizontal {
                border: 0px;
                background: #3e3e3e;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #0078D7;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #ffffff;
                width: 14px;
                height: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }
            QLabel#TimeLabel {
                color: #e0e0e0;
                font-family: Consolas, "Courier New", monospace; 
                font-weight: bold;
                font-size: 13px;
                background-color: transparent;
                padding: 0 5px;
            }
        """
        self.controls_widget.setStyleSheet(controls_style)

        controls_layout = QVBoxLayout(self.controls_widget)
        controls_layout.setContentsMargins(15, 10, 15, 15)
        controls_layout.setSpacing(10)

        # === 进度条区域 ===
        seek_layout = QHBoxLayout()
        seek_layout.setSpacing(10)

        self.label_current_time = QLabel("00:00")
        self.label_current_time.setObjectName("TimeLabel")
        seek_layout.addWidget(self.label_current_time)

        self.slider = ClickableSlider(Qt.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.setCursor(Qt.PointingHandCursor)
        self.slider.setFocusPolicy(Qt.NoFocus)
        self.slider.sliderMoved.connect(self.set_position)
        seek_layout.addWidget(self.slider)

        self.label_total_time = QLabel("00:00")
        self.label_total_time.setObjectName("TimeLabel")
        seek_layout.addWidget(self.label_total_time)

        controls_layout.addLayout(seek_layout)

        # === 按钮布局 ===
        btns_layout = QHBoxLayout()
        btns_layout.setSpacing(20)

        btns_layout.addStretch(1)

        def create_btn(text="", icon=None, slot=None, width=None):
            b = QPushButton(text)
            if icon: b.setIcon(icon)
            if slot: b.clicked.connect(slot)
            if width: b.setFixedWidth(width)
            b.setCursor(Qt.PointingHandCursor)
            b.setFocusPolicy(Qt.NoFocus)
            return b

        self.btn_open = create_btn("打开目录", slot=self.open_folder)
        btns_layout.addWidget(self.btn_open)

        self.btn_prev = create_btn(icon=self.style().standardIcon(QStyle.SP_MediaSkipBackward), slot=self.play_prev)
        btns_layout.addWidget(self.btn_prev)

        self.btn_rw = create_btn("<< 5s", slot=self.on_btn_rw_clicked)
        btns_layout.addWidget(self.btn_rw)

        self.btn_play = create_btn(icon=self.style().standardIcon(QStyle.SP_MediaPlay), slot=self.play_video)
        btns_layout.addWidget(self.btn_play)

        self.btn_ff = create_btn("5s >>", slot=self.on_btn_ff_clicked)
        btns_layout.addWidget(self.btn_ff)

        self.btn_next = create_btn(icon=self.style().standardIcon(QStyle.SP_MediaSkipForward), slot=self.play_next)
        btns_layout.addWidget(self.btn_next)

        self.btn_volume = VolumeButton()
        self.btn_volume.volumeChanged.connect(self.set_volume)
        btns_layout.addWidget(self.btn_volume)

        self.btn_speed = HoverMenuButton("倍速")
        self.btn_speed.setCursor(Qt.PointingHandCursor)
        self.btn_speed.setFixedWidth(60)

        speed_menu = QMenu(self.btn_speed)
        speed_menu.setWindowFlags(speed_menu.windowFlags() | Qt.FramelessWindowHint)
        speed_menu.setAttribute(Qt.WA_TranslucentBackground)

        speeds = [2.0, 1.5, 1.25, 1.0, 0.75, 0.5]
        self.speed_action_group = QActionGroup(self)

        for speed in speeds:
            action_text = f"{speed}x"
            action = QAction(action_text, self)
            action.setCheckable(True)
            action.setData(speed)
            if speed == 1.0:
                action.setChecked(True)
            action.triggered.connect(self.update_playback_speed)
            self.speed_action_group.addAction(action)
            speed_menu.addAction(action)

        self.btn_speed.setMenu(speed_menu)
        btns_layout.addWidget(self.btn_speed)

        self.btn_toggle_sidebar = create_btn(icon=self.style().standardIcon(QStyle.SP_ArrowRight),
                                             slot=self.toggle_sidebar)
        self.btn_toggle_sidebar.setToolTip("隐藏侧边栏")
        btns_layout.addWidget(self.btn_toggle_sidebar)

        btns_layout.addStretch(1)

        controls_layout.addLayout(btns_layout)

        # --- C. 侧边栏容器 ---
        self.right_panel_widget = QWidget(self.central_widget)
        sidebar_style = """
            QWidget { 
                background-color: #2b2b2b; 
                color: #f0f0f0;
                border-left: 1px solid #3e3e3e;
            }
            QListWidget {
                background-color: #1e1e1e;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                color: #ddd;
                outline: 0;
            }
            QListWidget::item:selected {
                background-color: #0078D7;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #333;
            }
            QScrollBar:horizontal { border: none; background: #1e1e1e; height: 8px; }
            QScrollBar::handle:horizontal { background: #555; min-width: 20px; border-radius: 4px; }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }
            QScrollBar::vertical { border: none; background: #1e1e1e; width: 8px; }
            QScrollBar::handle:vertical { background: #555; min-height: 20px; border-radius: 4px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            QScrollBar::corner { background: #1e1e1e; }
        """
        self.right_panel_widget.setStyleSheet(sidebar_style)

        right_layout = QVBoxLayout(self.right_panel_widget)
        right_layout.setContentsMargins(10, 10, 10, 10)

        self.camera_label = QLabel("摄像头加载中...")
        self.camera_label.setFixedSize(240, 180)
        self.camera_label.setStyleSheet(
            "border: 2px solid #3e3e3e; background-color: #000; color: #888; border-radius: 4px;")
        self.camera_label.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.camera_label)

        right_layout.addWidget(QLabel("播放列表:"))

        self.playlist_widget = QListWidget()
        self.playlist_widget.setFocusPolicy(Qt.NoFocus)
        self.playlist_widget.itemDoubleClicked.connect(self.play_selected_video_from_list)
        right_layout.addWidget(self.playlist_widget)

    def on_btn_rw_clicked(self):
        self.seek_relative(-5000)
        self.video_widget.show_osd("⏪", "-5s")

    def on_btn_ff_clicked(self):
        self.seek_relative(5000)
        self.video_widget.show_osd("⏩", "+5s")

    # === [关键] 键盘事件处理 ===
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Left:
            self.seek_relative(-5000)
            self.video_widget.show_osd("⏪", "-5s")
        elif event.key() == Qt.Key_Right:
            self.seek_relative(5000)
            self.video_widget.show_osd("⏩", "+5s")
        elif event.key() == Qt.Key_Up:
            new_vol = min(self.player.volume() + 5, 100)
            self.set_volume(new_vol)
            self.video_widget.show_osd("🔊", f"{new_vol}%")
        elif event.key() == Qt.Key_Down:
            new_vol = max(self.player.volume() - 5, 0)
            self.set_volume(new_vol)
            icon = "🔉" if new_vol > 0 else "🔇"
            self.video_widget.show_osd(icon, f"{new_vol}%")
        elif event.key() == Qt.Key_M:
            self.toggle_mute()
        # [修改] F键 或 Enter键 均可触发全屏
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_F):
            self.toggle_fullscreen_mode()
        elif event.key() == Qt.Key_Escape:
            if self.isFullScreen():
                self.showNormal()
        elif event.key() == Qt.Key_Space:
            self.play_video()
            if self.player.state() == QMediaPlayer.PlayingState:
                self.video_widget.show_osd("⏸", "暂停")
            else:
                self.video_widget.show_osd("▶", "播放")
        elif event.key() == Qt.Key_A:
            self.open_folder()
        elif event.key() == Qt.Key_B:
            self.toggle_sidebar()
        elif event.key() == Qt.Key_BracketLeft:
            self.play_prev()
            self.video_widget.show_osd("⏮", "上一部")
        elif event.key() == Qt.Key_BracketRight:
            self.play_next()
            self.video_widget.show_osd("⏭", "下一部")
        else:
            super().keyPressEvent(event)

    def toggle_mute(self):
        current_vol = self.player.volume()
        if current_vol > 0:
            self.last_volume = current_vol
            self.set_volume(0)
            self.video_widget.show_osd("🔇", "静音")
        else:
            target = self.last_volume if self.last_volume > 0 else 50
            self.set_volume(target)
            self.video_widget.show_osd("🔊", f"{target}%")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_layout_geometry()

    def update_layout_geometry(self):
        w = self.central_widget.width()
        h = self.central_widget.height()

        controls_hint = self.controls_widget.sizeHint()
        c_h = max(controls_hint.height(), 90)

        if self.sidebar_is_visible:
            self.right_panel_widget.setVisible(True)
            self.right_panel_widget.setGeometry(w - self.sidebar_width, 0, self.sidebar_width, h)
            self.right_panel_widget.raise_()

            self.controls_widget.setGeometry(0, h - c_h, w - self.sidebar_width, c_h)
            self.btn_toggle_sidebar.setIcon(self.style().standardIcon(QStyle.SP_ArrowRight))
        else:
            self.right_panel_widget.setVisible(False)
            self.controls_widget.setGeometry(0, h - c_h, w, c_h)
            self.btn_toggle_sidebar.setIcon(self.style().standardIcon(QStyle.SP_ArrowLeft))

        self.video_widget.setGeometry(0, 0, w, h - c_h)
        self.video_widget.lower()

    def toggle_sidebar(self):
        self.sidebar_is_visible = not self.sidebar_is_visible
        self.update_layout_geometry()

    def toggle_fullscreen_mode(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def format_time(self, ms):
        seconds = (ms) // 1000
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)

        total_seconds = self.video_duration // 1000
        if total_seconds >= 3600:
            return f"{h:02d}:{m:02d}:{s:02d}"
        else:
            return f"{m:02d}:{s:02d}"

    def update_playback_speed(self):
        action = self.sender()
        if action:
            speed = action.data()
            self.player.setPlaybackRate(speed)
            self.btn_speed.setText(f"{speed}x")
            self.video_widget.show_osd("🚀", f"{speed}x")

    def open_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "选择影视目录")
        if folder_path:
            self.playlist.clear()
            self.playlist_widget.clear()
            video_extensions = ('.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv')

            for file_name in os.listdir(folder_path):
                if file_name.lower().endswith(video_extensions):
                    full_path = os.path.join(folder_path, file_name)
                    self.playlist.append(full_path)

            if self.playlist:
                self.playlist.sort()
                self.playlist_widget.clear()
                for file_path in self.playlist:
                    self.playlist_widget.addItem(QListWidgetItem(os.path.basename(file_path)))

                self.current_index = 0
                self.load_video()
                print(f"已加载 {len(self.playlist)} 个视频")
            else:
                print("未找到视频文件")

    def load_video(self):
        if 0 <= self.current_index < len(self.playlist):
            file_path = self.playlist[self.current_index]
            self.player.setMedia(QMediaContent(QUrl.fromLocalFile(file_path)))
            self.setWindowTitle(f"正在播放: {os.path.basename(file_path)}")
            self.btn_play.setEnabled(True)
            self.player.play()

            current_rate = self.player.playbackRate()
            if current_rate != 1.0:
                self.player.setPlaybackRate(current_rate)

            self.update_playlist_selection()
        else:
            self.player.stop()
            self.setWindowTitle("PyQt5 视频播放器")
            self.playlist_widget.clearSelection()

    def update_playlist_selection(self):
        if 0 <= self.current_index < self.playlist_widget.count():
            self.playlist_widget.setCurrentRow(self.current_index)
        else:
            self.playlist_widget.clearSelection()

    def play_selected_video_from_list(self, item):
        self.current_index = self.playlist_widget.row(item)
        self.load_video()

    def play_video(self):
        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.pause()
            self.video_widget.show_osd("⏸", "暂停")
        else:
            self.player.play()
            self.video_widget.show_osd("▶", "播放")

    def media_state_changed(self, state):
        if self.player.state() == QMediaPlayer.PlayingState:
            self.btn_play.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        else:
            self.btn_play.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))

    def media_status_changed(self, status):
        if status == QMediaPlayer.EndOfMedia:
            self.play_next()

    def position_changed(self, position):
        if not self.slider.isSliderDown():
            self.slider.setValue(position)
        self.label_current_time.setText(self.format_time(position))

    def duration_changed(self, duration):
        self.video_duration = duration
        self.slider.setRange(0, duration)
        self.label_total_time.setText(self.format_time(duration))

        current_pos = self.player.position()
        self.label_current_time.setText(self.format_time(current_pos))

    def set_position(self, position):
        self.player.setPosition(position)
        self.label_current_time.setText(self.format_time(position))

    def seek_relative(self, delta_ms):
        current_pos = self.player.position()
        new_pos = current_pos + delta_ms
        if new_pos < 0: new_pos = 0
        if new_pos > self.player.duration(): new_pos = self.player.duration()
        self.player.setPosition(new_pos)

    def play_prev(self):
        if self.playlist:
            if self.current_index == -1:
                self.current_index = 0
            else:
                self.current_index = (self.current_index - 1 + len(self.playlist)) % len(self.playlist)
            self.load_video()

    def play_next(self):
        if self.playlist:
            if self.current_index == -1:
                self.current_index = 0
            else:
                self.current_index = (self.current_index + 1) % len(self.playlist)
            self.load_video()

    def set_volume(self, volume):
        self.player.setVolume(volume)
        self.btn_volume.set_value(volume)

    def handle_errors(self):
        self.btn_play.setEnabled(False)
        err_msg = "Error: " + self.player.errorString()
        print(err_msg)


if __name__ == '__main__':
    import sys

    app = QApplication(sys.argv)
    player = VideoPlayer()
    player.show()
    sys.exit(app.exec_())