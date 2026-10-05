"""
AcoustiGap - Desktop Graphical User Interface
Built with PySide6: Real-time Spectrogram, Sender (Messenger & File),
Receiver (Messenger & File), Channel Diagnostics, and Configuration Tabs.
"""

from __future__ import annotations

from datetime import datetime
import logging
import os
import sys
import threading
import time
from typing import Optional

import numpy as np
from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QColor, QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSlider,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..core.dsp import DspEngine, ProtocolId
from ..hardware.audio_stream import AudioReceiverStream, play_audio_samples
from ..hardware.devices import (
    get_default_input_device,
    get_default_output_device,
    list_input_devices,
    list_output_devices,
)
from ..hardware.noise_meter import analyze_audio_samples, measure_noise_floor
from ..protocol.chunker import FileChunker
from ..protocol.session import TransferSessionReceiver, TransferSessionSender
from .waterfall import SpectrogramWaterfallWidget

logger = logging.getLogger("acoustigap.gui")


def get_asset_path(filename: str) -> str:
    """Resolve asset path in development or in frozen PyInstaller executable."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, "assets", filename)
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_dir, "assets", filename)


# Modern Sleek Black & Grey Dark Theme Stylesheet
DARK_STYLESHEET = """
QMainWindow {
    background-color: #121212;
}
QWidget {
    color: #E0E0E0;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
}
QToolTip {
    background-color: #1E1E1E;
    color: #FFFFFF;
    border: 1px solid #444444;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 12px;
    font-family: 'Segoe UI', -apple-system, sans-serif;
}
QGroupBox {
    border: 1px solid #282828;
    border-radius: 8px;
    margin-top: 10px;
    font-weight: bold;
    color: #E5E5E5;
    padding-top: 12px;
    background-color: #181818;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 6px;
    background-color: #181818;
    color: #E5E5E5;
}
QTabWidget::pane {
    border: 1px solid #282828;
    border-radius: 8px;
    background-color: #161616;
}
QTabBar::tab {
    background-color: #121212;
    color: #888888;
    padding: 8px 18px;
    font-weight: 600;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 4px;
    border: 1px solid #222222;
    border-bottom: none;
}
QTabBar::tab:selected {
    background-color: #1A1A1A;
    color: #FFFFFF;
    border-top: 2px solid #999999;
    border-bottom: 2px solid #1A1A1A;
}
QTabBar::tab:hover {
    color: #F0F0F0;
    background-color: #181818;
}
QPushButton {
    background-color: #262626;
    color: #FFFFFF;
    border: 1px solid #383838;
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #333333;
    border-color: #4C4C4C;
}
QPushButton:pressed {
    background-color: #1C1C1C;
    border-color: #282828;
}
QPushButton:disabled {
    background-color: #161616;
    color: #555555;
    border-color: #222222;
}
QPushButton#secondaryBtn {
    background-color: #1E1E1E;
    color: #B5B5B5;
    border: 1px solid #2E2E2E;
}
QPushButton#secondaryBtn:hover {
    background-color: #2A2A2A;
    color: #FFFFFF;
    border-color: #3E3E3E;
}
QPushButton#actionBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2A2A2A, stop:1 #383838);
    border: 1px solid #4D4D4D;
    color: #FFFFFF;
    font-size: 13px;
    padding: 8px 16px;
}
QPushButton#actionBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #333333, stop:1 #444444);
    border-color: #666666;
}
QLineEdit, QTextEdit {
    background-color: #141414;
    border: 1px solid #262626;
    border-radius: 6px;
    padding: 6px 10px;
    color: #F0F0F0;
}
QLineEdit:focus, QTextEdit:focus {
    border: 1px solid #505050;
}
QComboBox {
    background-color: #141414;
    border: 1px solid #262626;
    border-radius: 6px;
    padding: 5px 32px 5px 10px;
    color: #F0F0F0;
    min-height: 32px;
    font-size: 13px;
}
QComboBox:hover, QComboBox:focus {
    border: 1px solid #484848;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 28px;
    border-left: 1px solid #262626;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
    background-color: #1A1A1A;
}
QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid #999999;
    width: 0;
    height: 0;
    margin-right: 2px;
}
QComboBox QAbstractItemView {
    background-color: #141414;
    border: 1px solid #383838;
    border-radius: 6px;
    color: #F0F0F0;
    selection-background-color: #2B2B2B;
    selection-color: #FFFFFF;
    padding: 4px;
}
QComboBox QAbstractItemView::item {
    min-height: 28px;
    padding: 4px 8px;
}
QProgressBar {
    border: 1px solid #262626;
    border-radius: 6px;
    text-align: center;
    background-color: #141414;
    color: #FFFFFF;
    font-weight: bold;
    height: 16px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3E3E3E, stop:1 #636363);
    border-radius: 5px;
}
QSlider::groove:horizontal {
    height: 6px;
    background: #202020;
    border-radius: 3px;
}
QSlider::sub-page:horizontal {
    background: #505050;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #D4D4D4;
    width: 16px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 8px;
}
QTableWidget {
    background-color: #141414;
    border: 1px solid #262626;
    border-radius: 6px;
    gridline-color: #1E1E1E;
}
QHeaderView::section {
    background-color: #1A1A1A;
    color: #999999;
    font-weight: bold;
    padding: 5px;
    border: 1px solid #262626;
}
"""


class AudioBridge(QObject):
    """Bridge for cross-thread audio signals to Qt UI thread."""

    samples_ready = Signal(np.ndarray)
    text_decoded = Signal(str, str)              # text, timestamp
    file_progress = Signal(int, int, str)        # current, total, filename
    file_completed = Signal(str, int, str, str)  # filename, size, hash, path
    send_progress = Signal(int, int)             # current, total
    send_finished = Signal(str, bool)            # message, success
    noise_test_progress = Signal(int, str)       # percent, status_text
    noise_test_result = Signal(str, str, str, str)  # rms, peak, health, summary_html


class MainWindow(QMainWindow):
    """Main AcoustiGap Application Window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AcoustiGap — Secure Acoustic Air-Gap Console")
        # Scaled for 1080p Full HD screens without taking up excessive screen space
        self.resize(980, 640)
        self.setMinimumSize(860, 520)

        # Set App Window Icon
        icon_path = get_asset_path("icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))


        self.bridge = AudioBridge()
        self.dsp = DspEngine()
        self.receiver_stream = AudioReceiverStream()
        self.active_receiver = TransferSessionReceiver()
        self._target_file_path: Optional[str] = None
        self._recv_dir = os.path.abspath("./received_files")
        os.makedirs(self._recv_dir, exist_ok=True)

        # For Noise Floor sampling from active stream
        self._is_sampling_noise = False
        self._noise_buffer: list[np.ndarray] = []
        self._noise_lock = threading.Lock()

        self._init_ui()
        self._connect_signals()
        self._start_listening()

    def _init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(8)

        # 1. Compact Header Bar
        header = QHBoxLayout()
        title_label = QLabel("🔊 AcoustiGap")
        title_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #FFFFFF;")
        header.addWidget(title_label)

        sub_label = QLabel("Air-Gap Transceiver • 48 kHz FSK Engine")
        sub_label.setStyleSheet("color: #8E8E8E; margin-left: 6px;")
        header.addWidget(sub_label)
        header.addStretch()

        # Quick config indicator in header
        self.header_config_lbl = QLabel("⚡ FAST • 🔊 65%")
        self.header_config_lbl.setStyleSheet(
            "background-color: #242424; color: #B0B0B0; border: 1px solid #333333; padding: 4px 10px; border-radius: 10px; font-weight: 600; margin-right: 6px;"
        )
        header.addWidget(self.header_config_lbl)

        self.status_badge = QLabel("● LISTENING")
        self.status_badge.setStyleSheet(
            "background-color: #064E3B; color: #34D399; padding: 4px 12px; border-radius: 10px; font-weight: bold;"
        )
        header.addWidget(self.status_badge)
        main_layout.addLayout(header)

        # 2. Compact Real-Time Waterfall Spectrogram (Height reduced to save screen space)
        wf_group = QGroupBox("Live Acoustic Spectrogram (Waterfall)")
        wf_layout = QVBoxLayout(wf_group)
        wf_layout.setContentsMargins(6, 8, 6, 6)
        self.waterfall = SpectrogramWaterfallWidget(width=950, height=130)
        wf_layout.addWidget(self.waterfall)
        main_layout.addWidget(wf_group)

        # 3. Main Tabs: [Sender] -> [Receiver] -> [Channel Diagnostics] -> [⚙️ Configuration]
        self.tabs = QTabWidget()

        # Build Tabs
        self._build_sender_tab()
        self._build_receiver_tab()
        self._build_diagnostics_tab()
        self._build_config_tab()

        main_layout.addWidget(self.tabs)

    # -------------------------------------------------------------
    # TAB 1: SENDER (Part 1: Messenger, Part 2: File)
    # -------------------------------------------------------------
    def _build_sender_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        # Part 1: Messenger (Text Sender)
        msg_box = QGroupBox("💬 Air-Gap Messenger (Send Text)")
        mb_layout = QVBoxLayout(msg_box)

        mb_layout.addWidget(QLabel("Message to Broadcast:"))
        self.send_text_input = QLineEdit()
        self.send_text_input.setPlaceholderText("Enter message or secret to transmit via sound waves...")
        self.send_text_input.returnPressed.connect(self._send_text_message)
        mb_layout.addWidget(self.send_text_input)

        # Quick preset buttons
        preset_layout = QHBoxLayout()
        for preset in ["PING", "HELLO AIR-GAP", "READY", "ACK 200"]:
            btn = QPushButton(preset)
            btn.setObjectName("secondaryBtn")
            btn.clicked.connect(lambda _, p=preset: self.send_text_input.setText(p))
            preset_layout.addWidget(btn)
        mb_layout.addLayout(preset_layout)

        self.btn_send_text = QPushButton("🚀 Broadcast Text via Audio")
        self.btn_send_text.clicked.connect(self._send_text_message)
        mb_layout.addWidget(self.btn_send_text)

        mb_layout.addWidget(QLabel("Sent History Log:"))
        self.sender_history_log = QTextEdit()
        self.sender_history_log.setReadOnly(True)
        self.sender_history_log.setPlaceholderText("Broadcasted messages will be logged here...")
        mb_layout.addWidget(self.sender_history_log)

        layout.addWidget(msg_box, 1)

        # Part 2: File Transfer (Send File)
        file_box = QGroupBox("📁 File Transfer (Send File)")
        fb_layout = QVBoxLayout(file_box)

        self.send_file_info = QLabel("No file selected.\nClick below to choose a file to transmit.")
        self.send_file_info.setStyleSheet("color: #9E9E9E; font-style: italic; padding: 2px;")
        fb_layout.addWidget(self.send_file_info)

        btn_select_file = QPushButton("📂 Browse / Select File to Send...")
        btn_select_file.setObjectName("secondaryBtn")
        btn_select_file.clicked.connect(self._browse_file)
        fb_layout.addWidget(btn_select_file)

        fb_layout.addWidget(QLabel("Transmission Progress:"))
        self.send_progress = QProgressBar()
        self.send_progress.setValue(0)
        fb_layout.addWidget(self.send_progress)

        self.send_status_lbl = QLabel("Ready to transmit.")
        self.send_status_lbl.setStyleSheet("color: #8E8E8E;")
        fb_layout.addWidget(self.send_status_lbl)

        self.btn_send_file = QPushButton("🚀 Transmit File Acoustically")
        self.btn_send_file.setObjectName("actionBtn")
        self.btn_send_file.clicked.connect(self._start_send_file)
        fb_layout.addWidget(self.btn_send_file)

        fb_layout.addWidget(QLabel("File Transmission Log:"))
        self.send_file_log = QTextEdit()
        self.send_file_log.setReadOnly(True)
        self.send_file_log.setPlaceholderText("File transmission packet progress will appear here...")
        fb_layout.addWidget(self.send_file_log)

        layout.addWidget(file_box, 1)

        self.tabs.addTab(tab, "📤 Sender")

    # -------------------------------------------------------------
    # TAB 2: RECEIVER (Part 1: Messenger, Part 2: File)
    # -------------------------------------------------------------
    def _build_receiver_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        # Part 1: Messenger (Received Text)
        msg_box = QGroupBox("💬 Air-Gap Messenger (Received Messages)")
        mb_layout = QVBoxLayout(msg_box)

        self.recv_text_log = QTextEdit()
        self.recv_text_log.setReadOnly(True)
        self.recv_text_log.setPlaceholderText("Incoming decoded text messages will appear here in real time...")
        mb_layout.addWidget(self.recv_text_log)

        btn_row = QHBoxLayout()
        btn_clear = QPushButton("🗑️ Clear Log")
        btn_clear.setObjectName("secondaryBtn")
        btn_clear.clicked.connect(self.recv_text_log.clear)
        btn_row.addWidget(btn_clear)

        btn_copy = QPushButton("📋 Copy All")
        btn_copy.setObjectName("secondaryBtn")
        btn_copy.clicked.connect(lambda: QApplication.clipboard().setText(self.recv_text_log.toPlainText()))
        btn_row.addWidget(btn_copy)
        mb_layout.addLayout(btn_row)

        layout.addWidget(msg_box, 1)

        # Part 2: File Transfer (Received Files)
        file_box = QGroupBox("📁 File Transfer (Received Files)")
        fb_layout = QVBoxLayout(file_box)

        # Storage directory row
        dir_row = QHBoxLayout()
        self.lbl_save_dir = QLabel(f"Save Path: <code>{os.path.basename(self._recv_dir)}</code>")
        self.lbl_save_dir.setToolTip(self._recv_dir)
        dir_row.addWidget(self.lbl_save_dir)

        btn_open_dir = QPushButton("📂 Open Folder")
        btn_open_dir.setObjectName("secondaryBtn")
        btn_open_dir.clicked.connect(lambda: os.startfile(self._recv_dir) if sys.platform == "win32" else None)
        dir_row.addWidget(btn_open_dir)
        fb_layout.addLayout(dir_row)

        fb_layout.addWidget(QLabel("Incoming Transfer Progress:"))
        self.recv_progress = QProgressBar()
        self.recv_progress.setValue(0)
        fb_layout.addWidget(self.recv_progress)

        self.recv_status_lbl = QLabel("Awaiting incoming file transmission...")
        self.recv_status_lbl.setStyleSheet("color: #8E8E8E;")
        fb_layout.addWidget(self.recv_status_lbl)

        fb_layout.addWidget(QLabel("Completed Received Files:"))
        self.recv_files_table = QTableWidget(0, 3)
        self.recv_files_table.setHorizontalHeaderLabels(["Filename", "Size", "SHA-256"])
        self.recv_files_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.recv_files_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.recv_files_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        fb_layout.addWidget(self.recv_files_table)

        layout.addWidget(file_box, 1)

        self.tabs.addTab(tab, "📥 Receiver")

    # -------------------------------------------------------------
    # TAB 3: CHANNEL DIAGNOSTICS (Noise Floor & SNR)
    # -------------------------------------------------------------
    def _build_diagnostics_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        top_row = QHBoxLayout()
        self.btn_noise = QPushButton("📊 Test Noise Floor & SNR (Sample 1.5s)")
        self.btn_noise.setObjectName("actionBtn")
        self.btn_noise.clicked.connect(self._run_noise_test)
        top_row.addWidget(self.btn_noise)

        self.diag_status_label = QLabel("Click button above to evaluate ambient room noise & channel health.")
        self.diag_status_label.setStyleSheet("color: #9E9E9E; margin-left: 8px;")
        top_row.addWidget(self.diag_status_label)
        top_row.addStretch()
        layout.addLayout(top_row)

        self.diag_progress = QProgressBar()
        self.diag_progress.setValue(0)
        self.diag_progress.setVisible(False)
        layout.addWidget(self.diag_progress)

        # Results display
        self.diag_results = QTextEdit()
        self.diag_results.setReadOnly(True)
        self.diag_results.setPlaceholderText("Diagnostic report with RMS noise, peak dBFS, channel health, and FFT peaks will appear here...")
        layout.addWidget(self.diag_results)

        self.tabs.addTab(tab, "🔬 Channel Diagnostics")

    # -------------------------------------------------------------
    # TAB 4: CONFIGURATION (Audio Devices, Protocol, Volume)
    # -------------------------------------------------------------
    def _build_config_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Row 1: 2-Column Side-by-Side (Left: Audio Devices, Right: Protocol & Volume)
        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(12)

        # Column 1: Audio Devices
        dev_group = QGroupBox("🎙️ Audio Device Selection (Microphone & Speaker)")
        dev_layout = QGridLayout(dev_group)
        dev_layout.setContentsMargins(12, 14, 12, 12)
        dev_layout.setSpacing(10)
        dev_layout.setColumnStretch(1, 1)

        dev_layout.addWidget(QLabel("Input Microphone:"), 0, 0)
        self.input_combo = QComboBox()
        self.input_combo.setMinimumHeight(34)
        self.input_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.input_combo.setMinimumContentsLength(16)
        self.input_combo.view().setMinimumWidth(500)
        self.input_combo.currentIndexChanged.connect(self._on_input_device_changed)
        self.input_combo.currentIndexChanged.connect(self._update_input_tooltip)
        dev_layout.addWidget(self.input_combo, 0, 1)

        dev_layout.addWidget(QLabel("Output Speaker:"), 1, 0)
        self.output_combo = QComboBox()
        self.output_combo.setMinimumHeight(34)
        self.output_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.output_combo.setMinimumContentsLength(16)
        self.output_combo.view().setMinimumWidth(500)
        self.output_combo.currentIndexChanged.connect(self._update_output_tooltip)
        dev_layout.addWidget(self.output_combo, 1, 1)

        btn_refresh_dev = QPushButton("🔄 Refresh Device List")
        btn_refresh_dev.setObjectName("secondaryBtn")
        btn_refresh_dev.clicked.connect(self._populate_devices)
        dev_layout.addWidget(btn_refresh_dev, 2, 1, Qt.AlignmentFlag.AlignRight)

        row1_layout.addWidget(dev_group, 1)

        # Column 2: Modulation Protocol & Volume
        proto_group = QGroupBox("⚡ Modulation Protocol & Volume Settings")
        proto_layout = QGridLayout(proto_group)
        proto_layout.setContentsMargins(12, 14, 12, 12)
        proto_layout.setSpacing(10)
        proto_layout.setColumnStretch(1, 1)

        proto_layout.addWidget(QLabel("Modulation Protocol:"), 0, 0)
        self.proto_combo = QComboBox()
        self.proto_combo.setMinimumHeight(34)
        self.proto_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.proto_combo.setMinimumContentsLength(16)
        self.proto_combo.view().setMinimumWidth(580)
        proto_descs = {
            ProtocolId.FAST: "⚡ FAST (~1.8-6.0 kHz — Mặc định cân bằng)",
            ProtocolId.FASTEST: "🚀 FASTEST (~1.8-6.0 kHz — Tốc độ cao)",
            ProtocolId.NORMAL: "🛡️ NORMAL (~1.8-6.0 kHz — Chống ồn mạnh)",
            ProtocolId.ULTRASOUND_FAST: "🔇 ULTRASOUND_FAST (15-19 kHz — Không nghe thấy, tốc độ cao)",
            ProtocolId.ULTRASOUND_FASTEST: "🔇 ULTRASOUND_FASTEST (15-19 kHz — Không nghe thấy, tốc độ tối đa)",
            ProtocolId.ULTRASOUND_NORMAL: "🔇 ULTRASOUND_NORMAL (15-19 kHz — Không nghe thấy, chống ồn)",
            ProtocolId.DTMF: "📞 DTMF (Âm phím điện thoại)",
        }
        proto_tooltips = {
            ProtocolId.FAST: "⚡ FAST (Protocol 1)\n• Dải tần số: 1,873 Hz – 5,959 Hz (Âm thanh nghe được)\n• Tốc độ truyền: ~16 - 32 Bytes/giây\n• Đặc điểm: Chế độ mặc định cân bằng, truyền nhanh và bắt sóng ổn định.",
            ProtocolId.FASTEST: "🚀 FASTEST (Protocol 2)\n• Dải tần số: 1,872 Hz – 5,963 Hz (Âm thanh nghe được)\n• Tốc độ truyền: ~32 - 64 Bytes/giây\n• Đặc điểm: Tốc độ cao nhất cho phòng yên tĩnh hoặc truyền khoảng cách gần.",
            ProtocolId.NORMAL: "🛡️ NORMAL (Protocol 0)\n• Dải tần số: 1,873 Hz – 5,957 Hz (Âm thanh nghe được)\n• Tốc độ truyền: ~8 - 16 Bytes/giây\n• Đặc điểm: Kháng nhiễu cực mạnh, mã hóa sửa lỗi Reed-Solomon dày.",
            ProtocolId.ULTRASOUND_FAST: "🔇 ULTRASOUND_FAST (Protocol 4)\n• Dải tần số: 14,998 Hz – 19,084 Hz (Cận siêu âm)\n• Tốc độ truyền: ~16 - 32 Bytes/giây (BẰNG 100% chế độ FAST)\n• Đặc điểm: Tai người HOÀN TOÀN KHÔNG NGHE THẤY. Phòng yên tĩnh không tiếng ríu rít.",
            ProtocolId.ULTRASOUND_FASTEST: "🔇 ULTRASOUND_FASTEST (Protocol 5)\n• Dải tần số: 14,997 Hz – 19,088 Hz (Cận siêu âm)\n• Tốc độ truyền: ~32 - 64 Bytes/giây (Tốc độ tối đa)\n• Đặc điểm: Cận siêu âm im lặng tuyệt đối, đạt tốc độ truyền cao nhất.",
            ProtocolId.ULTRASOUND_NORMAL: "🔇 ULTRASOUND_NORMAL (Protocol 3)\n• Dải tần số: 14,998 Hz – 19,082 Hz (Cận siêu âm)\n• Tốc độ truyền: ~8 - 16 Bytes/giây\n• Đặc điểm: Cận siêu âm im lặng, chống ồn và sửa lỗi dày.",
            ProtocolId.DTMF: "📞 DTMF (Protocol 6)\n• Dải tần số: Âm phím điện thoại cổ điển\n• Tốc độ truyền: ~2 - 4 Bytes/giây\n• Đặc điểm: Tương thích cao với đường truyền thoại analog.",
        }
        for p in ProtocolId:
            label = proto_descs.get(p, f"{p.name} (Protocol {p.value})")
            tip = proto_tooltips.get(p, label)
            self.proto_combo.addItem(label, p)
            self.proto_combo.setItemData(self.proto_combo.count() - 1, tip, Qt.ItemDataRole.ToolTipRole)
        self.proto_combo.setCurrentIndex(0)  # FAST
        self.proto_combo.currentIndexChanged.connect(self._update_header_config)
        self.proto_combo.currentIndexChanged.connect(self._update_proto_tooltip)
        self._update_proto_tooltip()
        proto_layout.addWidget(self.proto_combo, 0, 1)

        proto_layout.addWidget(QLabel("Speaker Volume:"), 1, 0)
        vol_layout = QHBoxLayout()
        self.vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setRange(10, 100)
        self.vol_slider.setValue(65)
        self.vol_label = QLabel("65%")
        self.vol_label.setFixedWidth(40)
        self.vol_slider.valueChanged.connect(self._on_vol_changed)
        vol_layout.addWidget(self.vol_slider)
        vol_layout.addWidget(self.vol_label)
        proto_layout.addLayout(vol_layout, 1, 1)

        row1_layout.addWidget(proto_group, 1)
        layout.addLayout(row1_layout)

        # Section 3: Hardware Advice / Air-Gap Best Practices
        info_group = QGroupBox("💡 Optimization & Hardware Notes")
        info_layout = QVBoxLayout(info_group)
        info_layout.setContentsMargins(12, 12, 12, 12)

        tip_text = (
            "• <b>Dell G5 5590 Microphone:</b> Driver WASAPI tự động được ưu tiên cho độ trễ thấp và thu âm chính xác.<br>"
            "• <b>Waves MaxxAudio Pro:</b> Đảm bảo đã tắt Audio Enhancements (Noise Reduction) để tín hiệu FSK không bị lọc nhầm.<br>"
            "• <b>Chế độ Cận siêu âm (Ultrasound):</b> Chọn <code>ULTRASOUND_FAST</code> để truyền dữ liệu hoàn toàn im lặng, tai người không nghe thấy.<br>"
            "• <b>Thiết bị di động:</b> Dùng app <b>AcoustiGap Android</b> (hoặc Waver) để trao đổi dữ liệu hai chiều trực tiếp với máy tính."
        )
        lbl_tip = QLabel(tip_text)
        lbl_tip.setStyleSheet("color: #9E9E9E; line-height: 1.4;")
        info_layout.addWidget(lbl_tip)
        layout.addWidget(info_group)

        layout.addStretch()

        self._populate_devices()
        self.tabs.addTab(tab, "⚙️ Configuration")

    def _update_input_tooltip(self):
        tip = self.input_combo.itemData(self.input_combo.currentIndex(), Qt.ItemDataRole.ToolTipRole)
        self.input_combo.setToolTip(tip or self.input_combo.currentText())

    def _update_output_tooltip(self):
        tip = self.output_combo.itemData(self.output_combo.currentIndex(), Qt.ItemDataRole.ToolTipRole)
        self.output_combo.setToolTip(tip or self.output_combo.currentText())

    def _update_proto_tooltip(self):
        tip = self.proto_combo.itemData(self.proto_combo.currentIndex(), Qt.ItemDataRole.ToolTipRole)
        self.proto_combo.setToolTip(tip or self.proto_combo.currentText())

    def _on_vol_changed(self, v: int):
        self.vol_label.setText(f"{v}%")
        self._update_header_config()

    def _update_header_config(self):
        proto_name = self.proto_combo.currentData().name if self.proto_combo.currentData() else "FAST"
        vol = self.vol_slider.value()
        self.header_config_lbl.setText(f"⚡ {proto_name} • 🔊 {vol}%")

    # -------------------------------------------------------------
    # DEVICE POPULATION & EVENTS
    # -------------------------------------------------------------
    def _populate_devices(self):
        self.input_combo.clear()
        inputs = list_input_devices()
        def_in = get_default_input_device()
        for idx, d in enumerate(inputs):
            label = f"[{d.index}] {d.name} ({d.hostapi_name})"
            tip = (
                f"🎙️ Microphone Thiết Bị [{d.index}]\n"
                f"• Tên: {d.name}\n"
                f"• Driver / Host API: {d.hostapi_name}\n"
                f"• Số kênh thu: {d.max_input_channels} In\n"
                f"• Tần số lấy mẫu: {int(d.default_samplerate)} Hz"
            )
            self.input_combo.addItem(label, d.index)
            self.input_combo.setItemData(idx, tip, Qt.ItemDataRole.ToolTipRole)

        if def_in:
            for i in range(self.input_combo.count()):
                if self.input_combo.itemData(i) == def_in.index:
                    self.input_combo.setCurrentIndex(i)
                    break
        self._update_input_tooltip()

        self.output_combo.clear()
        outputs = list_output_devices()
        def_out = get_default_output_device()
        for idx, d in enumerate(outputs):
            label = f"[{d.index}] {d.name} ({d.hostapi_name})"
            tip = (
                f"🔊 Speaker / Loa Thiết Bị [{d.index}]\n"
                f"• Tên: {d.name}\n"
                f"• Driver / Host API: {d.hostapi_name}\n"
                f"• Số kênh phát: {d.max_output_channels} Out\n"
                f"• Tần số lấy mẫu: {int(d.default_samplerate)} Hz"
            )
            self.output_combo.addItem(label, d.index)
            self.output_combo.setItemData(idx, tip, Qt.ItemDataRole.ToolTipRole)

        if def_out:
            for i in range(self.output_combo.count()):
                if self.output_combo.itemData(i) == def_out.index:
                    self.output_combo.setCurrentIndex(i)
                    break
        self._update_output_tooltip()


    def _on_input_device_changed(self):
        new_idx = self.input_combo.currentData()
        if new_idx is not None and self.receiver_stream.device_index != new_idx:
            logger.info(f"Switching input device to {new_idx}")
            self.receiver_stream.stop()
            self.receiver_stream.device_index = new_idx
            try:
                self.receiver_stream.start()
            except Exception as e:
                logger.error(f"Failed to switch device: {e}")

    def _connect_signals(self):
        self.bridge.samples_ready.connect(self.waterfall.push_audio_samples)
        self.bridge.text_decoded.connect(self._on_text_decoded)
        self.bridge.file_progress.connect(self._on_file_progress)
        self.bridge.file_completed.connect(self._on_file_completed)
        self.bridge.send_progress.connect(self._on_send_progress)
        self.bridge.send_finished.connect(self._on_send_finished)
        self.bridge.noise_test_progress.connect(self._on_noise_progress)
        self.bridge.noise_test_result.connect(self._on_noise_result)

    def _start_listening(self):
        def audio_listener(samples: np.ndarray):
            # 1. Update waterfall
            self.bridge.samples_ready.emit(samples)

            # 2. If actively sampling noise floor, collect samples
            with self._noise_lock:
                if self._is_sampling_noise:
                    self._noise_buffer.append(samples.copy())

            # 3. Decode incoming sound
            decoded = self.dsp.decode_samples(samples)
            if decoded is not None:
                now_str = datetime.now().strftime("%H:%M:%S")
                if isinstance(decoded, str):
                    self.bridge.text_decoded.emit(decoded, now_str)
                elif isinstance(decoded, (bytes, bytearray)):
                    pkt = self.active_receiver.feed_packet_data(decoded)
                    if pkt:
                        meta = self.active_receiver.metadata
                        total = meta.total_chunks if meta else 100
                        curr = len(self.active_receiver.received_chunks)
                        name = meta.filename if meta else "incoming.bin"
                        self.bridge.file_progress.emit(curr, total, name)
                        if self.active_receiver.is_complete:
                            hash_short = meta.sha256[:12] if meta else "verified"
                            save_path = os.path.join(self._recv_dir, meta.filename)
                            with open(save_path, "wb") as f:
                                f.write(self.active_receiver.assembled_data)
                            self.bridge.file_completed.emit(meta.filename, len(self.active_receiver.assembled_data), hash_short, save_path)
                            self.active_receiver = TransferSessionReceiver()

        self.receiver_stream.add_listener(audio_listener)
        try:
            self.receiver_stream.start()
        except Exception as e:
            logger.error(f"Failed to start receiver stream: {e}")

    # -------------------------------------------------------------
    # SENDER ACTIONS
    # -------------------------------------------------------------
    def _send_text_message(self):
        text = self.send_text_input.text().strip()
        if not text:
            return
        self.send_text_input.clear()
        proto = self.proto_combo.currentData()
        vol = self.vol_slider.value()
        out_dev = self.output_combo.currentData()
        now_str = datetime.now().strftime("%H:%M:%S")

        self.sender_history_log.append(f"<span style='color: #D4D4D4;'>[{now_str}] <b>Sent:</b> {text}</span>")
        self.status_badge.setText("● TRANSMITTING")
        self.status_badge.setStyleSheet("background-color: #7C2D12; color: #FDBA74; padding: 4px 12px; border-radius: 10px; font-weight: bold;")

        def worker():
            try:
                samples = self.dsp.encode(text, protocol=proto, volume=vol)
                play_audio_samples(samples, device_index=out_dev, sample_rate=self.dsp.sample_rate, blocking=True)
                self.bridge.send_finished.emit(f"Text '{text}' transmitted", True)
            except Exception as e:
                self.bridge.send_finished.emit(f"Send failed: {e}", False)

        threading.Thread(target=worker, daemon=True).start()

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select File to Send Over Air-Gap")
        if path:
            self._target_file_path = path
            size = os.path.getsize(path)
            name = os.path.basename(path)
            approx_chunks = (size // 48) + 2
            self.send_file_info.setText(
                f"<b>File:</b> {name}<br><b>Size:</b> {size:,} bytes | <b>Estimated Chunks:</b> ~{approx_chunks} packets"
            )
            self.send_status_lbl.setText(f"Loaded: {name}")
        else:
            self._target_file_path = None

    def _start_send_file(self):
        if not self._target_file_path or not os.path.exists(self._target_file_path):
            QMessageBox.warning(self, "No File Selected", "Please select a file to transmit first.")
            return

        filepath = self._target_file_path
        proto = self.proto_combo.currentData()
        vol = self.vol_slider.value()
        out_dev = self.output_combo.currentData()

        self.btn_send_file.setEnabled(False)
        self.send_progress.setValue(0)
        self.status_badge.setText("● TRANSMITTING")
        self.status_badge.setStyleSheet("background-color: #7C2D12; color: #FDBA74; padding: 4px 12px; border-radius: 10px; font-weight: bold;")

        def worker():
            try:
                with open(filepath, "rb") as f:
                    content = f.read()

                chunked = FileChunker.chunk_data(
                    content,
                    filename=os.path.basename(filepath),
                    chunk_size=48,
                    compress=True,
                )
                sender = TransferSessionSender(self.dsp, protocol=proto, volume=vol)

                def on_chunk_done(curr, total):
                    self.bridge.send_progress.emit(curr, total)

                sender.send_chunked_file(chunked, output_device_index=out_dev, progress_callback=on_chunk_done)
                self.bridge.send_finished.emit(f"File '{os.path.basename(filepath)}' successfully transmitted!", True)
            except Exception as e:
                self.bridge.send_finished.emit(f"Transmission error: {e}", False)

        threading.Thread(target=worker, daemon=True).start()

    def _on_send_progress(self, curr: int, total: int):
        pct = int((curr / total) * 100)
        self.send_progress.setValue(pct)
        self.send_status_lbl.setText(f"Transmitting packet {curr}/{total} ({pct}%)")

    def _on_send_finished(self, msg: str, success: bool):
        self.btn_send_file.setEnabled(True)
        self.status_badge.setText("● LISTENING")
        self.status_badge.setStyleSheet("background-color: #064E3B; color: #34D399; padding: 4px 12px; border-radius: 10px; font-weight: bold;")
        now_str = datetime.now().strftime("%H:%M:%S")
        color = "#34D399" if success else "#EF4444"
        self.send_file_log.append(f"<span style='color: {color};'>[{now_str}] {msg}</span>")
        if success:
            self.send_status_lbl.setText("Transmission complete!")
        else:
            self.send_status_lbl.setText("Error during transmission.")

    # -------------------------------------------------------------
    # RECEIVER ACTIONS
    # -------------------------------------------------------------
    def _on_text_decoded(self, text: str, timestamp: str):
        self.recv_text_log.append(
            f"<div style='margin-bottom: 4px;'><span style='color: #8E8E8E;'>[{timestamp}]</span> <b style='color: #4ADE80;'>Received:</b> <span style='color: #FFFFFF;'>{text}</span></div>"
        )
        self.status_badge.setText("● RECEIVED TEXT")
        self.status_badge.setStyleSheet("background-color: #065F46; color: #6EE7B7; padding: 4px 12px; border-radius: 10px; font-weight: bold;")

    def _on_file_progress(self, curr: int, total: int, filename: str):
        pct = int((curr / max(1, total)) * 100)
        self.recv_progress.setValue(pct)
        self.recv_status_lbl.setText(f"Receiving '{filename}': {curr}/{total} packets ({pct}%)")
        self.status_badge.setText("● RECEIVING FILE")
        self.status_badge.setStyleSheet("background-color: #1E3A8A; color: #93C5FD; padding: 4px 12px; border-radius: 10px; font-weight: bold;")

    def _on_file_completed(self, filename: str, size: int, hash_str: str, path: str):
        self.recv_progress.setValue(100)
        self.recv_status_lbl.setText(f"✔ Completed '{filename}' ({size:,} bytes) - SHA-256 match!")
        self.status_badge.setText("● LISTENING")
        self.status_badge.setStyleSheet("background-color: #064E3B; color: #34D399; padding: 4px 12px; border-radius: 10px; font-weight: bold;")

        row = self.recv_files_table.rowCount()
        self.recv_files_table.insertRow(row)
        self.recv_files_table.setItem(row, 0, QTableWidgetItem(filename))
        self.recv_files_table.setItem(row, 1, QTableWidgetItem(f"{size:,} B"))
        self.recv_files_table.setItem(row, 2, QTableWidgetItem(f"✔ {hash_str}..."))

    # -------------------------------------------------------------
    # CHANNEL DIAGNOSTICS (Instant & Reliable via Signal)
    # -------------------------------------------------------------
    def _run_noise_test(self):
        self.btn_noise.setEnabled(False)
        self.diag_progress.setVisible(True)
        self.diag_progress.setValue(10)
        self.diag_status_label.setText("Sampling live microphone audio for 1.5 seconds...")
        self.diag_results.setHtml("<p style='color: #B0B0B0;'><i>Collecting ambient sound samples from active stream...</i></p>")

        # Clear sampling buffer and start collecting
        with self._noise_lock:
            self._noise_buffer.clear()
            self._is_sampling_noise = True

        def sampler_worker():
            target_samples = 48000 * 1.5  # 1.5 seconds
            start_t = time.time()

            # Poll until 1.5s of audio is collected or 3s timeout
            while time.time() - start_t < 3.0:
                time.sleep(0.15)
                with self._noise_lock:
                    count = sum(len(c) for c in self._noise_buffer)
                pct = min(90, int((count / target_samples) * 90))
                self.bridge.noise_test_progress.emit(pct, f"Sampling audio: {count}/{int(target_samples)} samples...")
                if count >= target_samples:
                    break

            # Finish collection
            with self._noise_lock:
                self._is_sampling_noise = False
                chunks = list(self._noise_buffer)
                self._noise_buffer.clear()

            if chunks:
                all_audio = np.concatenate(chunks)
            else:
                all_audio = np.zeros(100)

            try:
                prof = analyze_audio_samples(all_audio, sample_rate=48000)
                rms = f"{prof.rms_dbfs:.2f} dBFS"
                peak = f"{prof.peak_dbfs:.2f} dBFS"
                health = prof.status
                rec = prof.recommendation

                html = f"""
                <div style='background-color: #161616; border: 1px solid #2C2C2C; border-radius: 8px; padding: 12px;'>
                    <h3 style='color: #FFFFFF; margin-top: 0;'>Channel Diagnostic Report</h3>
                    <table style='width: 100%; font-size: 13px;'>
                        <tr>
                            <td style='color: #9E9E9E; width: 170px;'><b>RMS Noise Floor:</b></td>
                            <td style='color: #4ADE80; font-weight: bold;'>{rms}</td>
                        </tr>
                        <tr>
                            <td style='color: #9E9E9E;'><b>Peak Noise Level:</b></td>
                            <td style='color: #FBBF24; font-weight: bold;'>{peak}</td>
                        </tr>
                        <tr>
                            <td style='color: #9E9E9E;'><b>Channel Health:</b></td>
                            <td style='color: #E0E0E0; font-weight: bold;'>{health}</td>
                        </tr>
                        <tr>
                            <td style='color: #9E9E9E;'><b>Recommendation:</b></td>
                            <td style='color: #CCCCCC;'>{rec}</td>
                        </tr>
                    </table>
                    <hr style='border: 1px solid #282828; margin: 8px 0;'>
                    <b style='color: #9E9E9E;'>Top Noise Frequencies Detected:</b>
                    <ul style='margin-top: 4px; padding-left: 20px; color: #D0D0D0;'>
                """
                for freq, mag in prof.top_noise_frequencies[:5]:
                    html += f"<li><b>{freq:.1f} Hz:</b> {mag:.2f} dBFS</li>"
                html += "</ul></div>"

                self.bridge.noise_test_progress.emit(100, "Measurement complete!")
                self.bridge.noise_test_result.emit(rms, peak, health, html)
            except Exception as e:
                self.bridge.noise_test_progress.emit(100, "Error during test")
                err_html = f"<p style='color: #EF4444;'>Failed to compute noise profile: {e}</p>"
                self.bridge.noise_test_result.emit("N/A", "N/A", "ERROR", err_html)

        threading.Thread(target=sampler_worker, daemon=True).start()

    def _on_noise_progress(self, pct: int, status_text: str):
        self.diag_progress.setValue(pct)
        self.diag_status_label.setText(status_text)

    def _on_noise_result(self, rms: str, peak: str, health: str, html: str):
        self.btn_noise.setEnabled(True)
        self.diag_progress.setVisible(False)
        self.diag_status_label.setText(f"Status: {health} (RMS: {rms}, Peak: {peak})")
        self.diag_results.setHtml(html)

    def closeEvent(self, event):
        self.receiver_stream.stop()
        self.dsp.close()
        event.accept()


def launch_gui():
    """Launch the AcoustiGap Desktop GUI application."""
    app = QApplication(sys.argv)
    icon_path = get_asset_path("icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    app.setStyleSheet(DARK_STYLESHEET)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    launch_gui()
