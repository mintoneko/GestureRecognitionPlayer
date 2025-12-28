import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QSlider, QLabel,
                             QFileDialog, QStyle, QListWidget, QListWidgetItem)
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtCore import Qt, QUrl


class VideoPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyQt5 视频播放器")
        self.resize(1000, 600)

        self.playlist = []
        self.current_index = -1

        # ### 第1处修改：添加一个变量来跟踪侧边栏状态 ###
        self.sidebar_is_visible = True
        # #################################################

        self.player = QMediaPlayer(None, QMediaPlayer.VideoSurface)

        self.video_widget = QVideoWidget()
        p = self.video_widget.palette()
        p.setColor(self.video_widget.backgroundRole(), Qt.black)
        self.video_widget.setPalette(p)

        self.camera_label = QLabel("摄像头加载中...")
        self.camera_label.setFixedSize(240, 180)
        self.camera_label.setStyleSheet("border: 1px solid #555555; background-color: black;")
        self.camera_label.setAlignment(Qt.AlignCenter)

        self.playlist_widget = QListWidget()
        self.playlist_widget.setMinimumWidth(240)
        self.playlist_widget.itemDoubleClicked.connect(self.play_selected_video_from_list)

        self.init_ui()

        self.player.setVideoOutput(self.video_widget)
        self.player.stateChanged.connect(self.media_state_changed)
        self.player.positionChanged.connect(self.position_changed)
        self.player.durationChanged.connect(self.duration_changed)
        self.player.error.connect(self.handle_errors)
        self.player.mediaStatusChanged.connect(self.media_status_changed)

        self.player.setVolume(50)
        self.volume_slider.setValue(50)

    def init_ui(self):
        """设置界面布局"""
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        main_horizontal_layout = QHBoxLayout(central_widget)

        # --- 左侧：视频播放区域 ---
        left_panel_layout = QVBoxLayout()
        left_panel_widget = QWidget()
        left_panel_widget.setLayout(left_panel_layout)

        left_panel_layout.addWidget(self.video_widget)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.sliderMoved.connect(self.set_position)
        left_panel_layout.addWidget(self.slider)

        # 底部控制栏
        hbox_layout = QHBoxLayout()
        self.btn_open = QPushButton("打开目录")
        self.btn_open.clicked.connect(self.open_folder)
        hbox_layout.addWidget(self.btn_open)

        self.btn_prev = QPushButton()
        self.btn_prev.setIcon(self.style().standardIcon(QStyle.SP_MediaSkipBackward))
        self.btn_prev.setToolTip("上一部")
        self.btn_prev.clicked.connect(self.play_prev)
        hbox_layout.addWidget(self.btn_prev)

        self.btn_rw = QPushButton("<< 5s")
        self.btn_rw.setToolTip("后退5s")
        self.btn_rw.clicked.connect(lambda: self.seek_relative(-5000))
        hbox_layout.addWidget(self.btn_rw)

        self.btn_play = QPushButton()
        self.btn_play.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.btn_play.setToolTip("播放/暂停")
        self.btn_play.clicked.connect(self.play_video)
        hbox_layout.addWidget(self.btn_play)

        self.btn_ff = QPushButton("5s >>")
        self.btn_ff.setToolTip("快进5s")
        self.btn_ff.clicked.connect(lambda: self.seek_relative(5000))
        hbox_layout.addWidget(self.btn_ff)

        self.btn_next = QPushButton()
        self.btn_next.setIcon(self.style().standardIcon(QStyle.SP_MediaSkipForward))
        self.btn_next.setToolTip("下一部")
        self.btn_next.clicked.connect(self.play_next)
        hbox_layout.addWidget(self.btn_next)

        self.label_vol = QLabel("音量")
        hbox_layout.addWidget(self.label_vol)

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setFixedWidth(100)
        self.volume_slider.valueChanged.connect(self.set_volume)
        hbox_layout.addWidget(self.volume_slider)

        self.btn_toggle_sidebar = QPushButton()
        self.btn_toggle_sidebar.setIcon(self.style().standardIcon(QStyle.SP_ArrowRight))
        self.btn_toggle_sidebar.setToolTip("隐藏侧边栏")

        # ### 第2处修改：移除 setCheckable ###
        # self.btn_toggle_sidebar.setCheckable(True)  # <-- 注释或删除此行
        # ######################################

        self.btn_toggle_sidebar.clicked.connect(self.toggle_sidebar)
        hbox_layout.addWidget(self.btn_toggle_sidebar)

        left_panel_layout.addLayout(hbox_layout)

        # --- 右侧：摄像头和播放列表区域 ---
        right_panel_layout = QVBoxLayout()
        self.right_panel_widget = QWidget()
        self.right_panel_widget.setLayout(right_panel_layout)
        self.right_panel_widget.setFixedWidth(260)

        right_panel_layout.addWidget(self.camera_label)
        right_panel_layout.addWidget(QLabel("播放列表:"))
        right_panel_layout.addWidget(self.playlist_widget)

        # 将左右面板添加到主水平布局
        main_horizontal_layout.addWidget(left_panel_widget)
        main_horizontal_layout.addWidget(self.right_panel_widget)

    # ### 第3处修改：更新 toggle_sidebar 的逻辑 ###
    def toggle_sidebar(self):
        """根据自定义变量显示或隐藏右侧面板"""
        if self.sidebar_is_visible:
            # 当前是可见的，所以我们要隐藏它
            self.right_panel_widget.hide()
            self.btn_toggle_sidebar.setIcon(self.style().standardIcon(QStyle.SP_ArrowLeft))
            self.btn_toggle_sidebar.setToolTip("显示侧边栏")
            self.sidebar_is_visible = False  # 更新状态
        else:
            # 当前是隐藏的，所以我们要显示它
            self.right_panel_widget.show()
            self.btn_toggle_sidebar.setIcon(self.style().standardIcon(QStyle.SP_ArrowRight))
            self.btn_toggle_sidebar.setToolTip("隐藏侧边栏")
            self.sidebar_is_visible = True  # 更新状态

    # ############################################

    def open_folder(self):
        """打开目录并扫描视频文件"""
        folder_path = QFileDialog.getExistingDirectory(self, "选择影视目录")
        if folder_path:
            self.playlist.clear()
            self.playlist_widget.clear()
            video_extensions = ('.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv')

            for file_name in os.listdir(folder_path):
                if file_name.lower().endswith(video_extensions):
                    full_path = os.path.join(folder_path, file_name)
                    self.playlist.append(full_path)
                    # self.playlist_widget.addItem(QListWidgetItem(file_name)) # 初始添加是多余的

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
        """加载当前索引的视频"""
        if 0 <= self.current_index < len(self.playlist):
            file_path = self.playlist[self.current_index]
            self.player.setMedia(QMediaContent(QUrl.fromLocalFile(file_path)))
            self.setWindowTitle(f"正在播放: {os.path.basename(file_path)}")
            self.btn_play.setEnabled(True)
            self.player.play()
            self.update_playlist_selection()
        else:
            self.player.stop()
            self.setWindowTitle("PyQt5 视频播放器")
            self.playlist_widget.clearSelection()

    def update_playlist_selection(self):
        """根据当前播放索引更新QListWidget的选中状态"""
        if 0 <= self.current_index < self.playlist_widget.count():
            self.playlist_widget.setCurrentRow(self.current_index)
        else:
            self.playlist_widget.clearSelection()

    def play_selected_video_from_list(self, item):
        """通过双击播放列表中的视频"""
        self.current_index = self.playlist_widget.row(item)
        self.load_video()

    def play_video(self):
        """切换播放/暂停状态"""
        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def media_state_changed(self, state):
        """当播放器状态改变时更新图标"""
        if self.player.state() == QMediaPlayer.PlayingState:
            self.btn_play.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        else:
            self.btn_play.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))

    def media_status_changed(self, status):
        """监听媒体播放状态，实现自动播放下一首"""
        if status == QMediaPlayer.EndOfMedia:
            self.play_next()

    def position_changed(self, position):
        """更新进度条位置"""
        self.slider.setValue(position)

    def duration_changed(self, duration):
        """更新进度条总长度"""
        self.slider.setRange(0, duration)

    def set_position(self, position):
        """拖动进度条跳转"""
        self.player.setPosition(position)

    def seek_relative(self, delta_ms):
        """快进或快退 delta_ms 毫秒"""
        current_pos = self.player.position()
        new_pos = current_pos + delta_ms
        if new_pos < 0: new_pos = 0
        if new_pos > self.player.duration(): new_pos = self.player.duration()
        self.player.setPosition(new_pos)

    def play_prev(self):
        """上一部"""
        if self.playlist:
            if self.current_index == -1:
                self.current_index = 0
            else:
                self.current_index = (self.current_index - 1 + len(self.playlist)) % len(self.playlist)
            self.load_video()

    def play_next(self):
        """下一部"""
        if self.playlist:
            if self.current_index == -1:
                self.current_index = 0
            else:
                self.current_index = (self.current_index + 1) % len(self.playlist)
            self.load_video()

    def set_volume(self, volume):
        """设置音量"""
        self.player.setVolume(volume)

    def handle_errors(self):
        """错误处理"""
        self.btn_play.setEnabled(False)
        err_msg = "Error: " + self.player.errorString()
        print(err_msg)


if __name__ == '__main__':
    import sys

    app = QApplication(sys.argv)
    player = VideoPlayer()
    player.show()
    sys.exit(app.exec_())