"""
AcoustiGap - Audio Streams
Provides non-blocking background microphone capture and speaker playback
using PortAudio/sounddevice.
"""

from __future__ import annotations

import logging
import queue
import threading
from typing import Callable, List, Optional

import numpy as np
import sounddevice as sd

from .devices import get_default_input_device, get_default_output_device

logger = logging.getLogger("acoustigap.stream")


class AudioReceiverStream:
    """
    Non-blocking audio receiver stream wrapping sounddevice.InputStream.
    Reads continuous 48000 Hz mono audio frames and delivers them via queue and callbacks.
    """

    def __init__(
        self,
        device_index: Optional[int] = None,
        sample_rate: int = 48000,
        block_size: int = 1024,
    ):
        self.sample_rate = sample_rate
        self.block_size = block_size

        if device_index is None:
            dev = get_default_input_device()
            self.device_index = dev.index if dev else None
        else:
            self.device_index = device_index

        self._stream: Optional[sd.InputStream] = None
        self._queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=100)
        self._listeners: List[Callable[[np.ndarray], None]] = []
        self._is_running = False
        self._lock = threading.Lock()

    def add_listener(self, listener: Callable[[np.ndarray], None]) -> None:
        """Register a callback that receives incoming audio frames (e.g. for GUI Waterfall)."""
        with self._lock:
            if listener not in self._listeners:
                self._listeners.append(listener)

    def remove_listener(self, listener: Callable[[np.ndarray], None]) -> None:
        """Unregister a listener callback."""
        with self._lock:
            if listener in self._listeners:
                self._listeners.remove(listener)

    def _audio_callback(self, indata, frames, time_info, status):
        """PortAudio real-time audio callback."""
        if status:
            logger.warning(f"Audio stream status: {status}")

        # indata has shape (frames, channels), float32 mono -> 1D array
        samples = indata[:, 0].copy()

        # Enqueue for decoder consumption
        try:
            self._queue.put_nowait(samples)
        except queue.Full:
            # Drop oldest to avoid lag
            try:
                self._queue.get_nowait()
                self._queue.put_nowait(samples)
            except Exception:
                pass

        # Notify visualizer / monitoring listeners
        with self._lock:
            listeners = list(self._listeners)
        for l in listeners:
            try:
                l(samples)
            except Exception as e:
                logger.error(f"Listener error: {e}")

    def start(self) -> None:
        """Start capturing audio."""
        if self._is_running:
            return

        logger.info(f"Starting audio receiver stream on device {self.device_index} @ {self.sample_rate}Hz...")
        self._stream = sd.InputStream(
            device=self.device_index,
            channels=1,
            samplerate=self.sample_rate,
            blocksize=self.block_size,
            dtype="float32",
            callback=self._audio_callback,
        )
        self._stream.start()
        self._is_running = True

    def read_chunk(self, timeout: Optional[float] = 1.0) -> Optional[np.ndarray]:
        """
        Read the next chunk of audio samples from the queue.
        :param timeout: Seconds to wait before returning None
        :return: 1D numpy array of float32 samples or None
        """
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def stop(self) -> None:
        """Stop capturing audio."""
        if not self._is_running:
            return

        self._is_running = False
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                logger.error(f"Error closing stream: {e}")
            self._stream = None
        logger.info("Audio receiver stream stopped.")

    @property
    def is_running(self) -> bool:
        return self._is_running

    def __enter__(self) -> AudioReceiverStream:
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()


def play_audio_samples(
    samples: np.ndarray,
    device_index: Optional[int] = None,
    sample_rate: int = 48000,
    blocking: bool = True,
) -> None:
    """
    Play float32 audio samples through the selected output speaker.
    :param samples: 1D numpy float32 array
    :param device_index: Output device index (None for default)
    :param sample_rate: Audio sample rate in Hz
    :param blocking: If True, waits until playback finishes
    """
    if device_index is None:
        out_dev = get_default_output_device()
        device_index = out_dev.index if out_dev else None

    sd.play(samples, samplerate=sample_rate, device=device_index, blocking=blocking)
