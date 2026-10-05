"""
AcoustiGap - Real-Time Audio Waterfall & Spectrogram Visualizer
Renders rolling FFT frequency spectrum (waterfall) in PySide6.
"""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import QPoint, QRect, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen
from PySide6.QtWidgets import QWidget

# Modern High-Contrast Audio Spectrogram Palette for Black & Grey theme
COLOR_PALETTE = []
for i in range(256):
    norm = i / 255.0
    if norm < 0.20:
        # Dark charcoal floor
        val = int(18 + 25 * (norm / 0.20))
        r, g, b = val, val, val
    elif norm < 0.50:
        # Subtle slate cyan-grey
        frac = (norm - 0.20) / 0.30
        r = int(35 + 20 * frac)
        g = int(45 + 85 * frac)
        b = int(55 + 130 * frac)
    elif norm < 0.80:
        # Bright cyber cyan-silver
        frac = (norm - 0.50) / 0.30
        r = int(55 + 140 * frac)
        g = int(130 + 90 * frac)
        b = int(185 + 50 * frac)
    else:
        # Peak white-silver hot
        frac = (norm - 0.80) / 0.20
        r = int(195 + 60 * frac)
        g = int(220 + 35 * frac)
        b = int(235 + 20 * frac)
    COLOR_PALETTE.append((min(255, r), min(255, g), min(255, b)))


class SpectrogramWaterfallWidget(QWidget):
    """
    Real-time FFT audio waterfall widget with rolling historical spectrogram.
    """

    def __init__(self, width: int = 600, height: int = 240, sample_rate: int = 48000, parent=None):
        super().__init__(parent)
        self.wf_width = width
        self.wf_height = height
        self.sample_rate = sample_rate
        self.setMinimumSize(width, height)

        # Image buffer for waterfall history (ARGB32) - True black background
        self.image = QImage(self.wf_width, self.wf_height, QImage.Format.Format_ARGB32)
        self.image.fill(QColor(18, 18, 18))

        # Recent FFT spectrum line (for instantaneous peak display)
        self.latest_fft = np.zeros(self.wf_width, dtype=np.float32)


        # Refresh timer (30 FPS)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(33)

    def push_audio_samples(self, samples: np.ndarray) -> None:
        """Process incoming 1D float32 audio chunk and push a new line to waterfall."""
        if len(samples) < 256:
            return

        # Apply Hanning window
        window = np.hanning(len(samples))
        windowed = samples * window

        # Compute FFT magnitude
        fft_vals = np.abs(np.fft.rfft(windowed))
        # Logarithmic scale (dB)
        db_vals = 20 * np.log10(fft_vals + 1e-6)

        # Normalize dB range (approx -80 dBFS to 0 dBFS -> 0..255)
        min_db = -70.0
        max_db = -5.0
        norm_vals = np.clip((db_vals - min_db) / (max_db - min_db), 0.0, 1.0)

        # Resample FFT bins to fit widget width
        src_indices = np.linspace(0, len(norm_vals) - 1, self.wf_width).astype(int)
        line_data = norm_vals[src_indices]
        self.latest_fft = line_data

        # Scroll image down by 1 pixel
        # Copy rows 0..H-2 to rows 1..H-1
        bytes_per_line = self.image.bytesPerLine()
        ptr = self.image.bits()
        # Direct buffer shift for maximum speed
        ptr_array = np.frombuffer(ptr, dtype=np.uint8, count=self.wf_height * bytes_per_line)
        ptr_array[bytes_per_line:] = ptr_array[:-bytes_per_line]

        # Draw new top row
        row_colors = [COLOR_PALETTE[int(val * 255)] for val in line_data]
        top_row_bgra = np.zeros((self.wf_width, 4), dtype=np.uint8)
        for x, (r, g, b) in enumerate(row_colors):
            top_row_bgra[x, 0] = b  # Blue
            top_row_bgra[x, 1] = g  # Green
            top_row_bgra[x, 2] = r  # Red
            top_row_bgra[x, 3] = 255  # Alpha

        ptr_array[: self.wf_width * 4] = top_row_bgra.flatten()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw scaled waterfall image
        target_rect = QRect(0, 0, self.width(), self.height())
        painter.drawImage(target_rect, self.image)

        # Draw frequency markers overlay
        painter.setPen(QPen(QColor(180, 200, 220, 120), 1, Qt.PenStyle.DashLine))
        painter.setFont(QFont("Segoe UI", 8))

        freq_markers = [1000, 2000, 4000, 8000, 12000, 16000, 20000]
        max_freq = self.sample_rate / 2

        for f in freq_markers:
            if f < max_freq:
                x = int((f / max_freq) * self.width())
                painter.drawLine(x, 0, x, self.height())
                painter.drawText(x + 4, self.height() - 6, f"{f // 1000}k")

        # Draw subtle border
        painter.setPen(QPen(QColor(60, 60, 60), 1))
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)
        painter.end()
