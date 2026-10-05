"""
AcoustiGap - DSP Core Engine
Wraps ggwave C++ core with clean Python typing, Base85 binary bridge,
and robust audio sample buffering.
"""

from __future__ import annotations

import base64
from enum import IntEnum
import logging
from typing import Optional, Union

import ggwave
import numpy as np

logger = logging.getLogger("acoustigap.dsp")

# Protocol IDs supported by ggwave
class ProtocolId(IntEnum):
    NORMAL = 0              # Audible FSK, ~8-16 B/s, most robust in noisy rooms
    FAST = 1                # Audible FSK, ~16-32 B/s, default balanced mode
    FASTEST = 2             # Audible FSK, ~32-64 B/s, high throughput
    ULTRASOUND_NORMAL = 3   # 15-20 kHz inaudible FSK, short range
    ULTRASOUND_FAST = 4     # 15-20 kHz inaudible FSK, medium speed
    ULTRASOUND_FASTEST = 5  # 15-20 kHz inaudible FSK, highest inaudible speed
    DTMF = 6                # DTMF tones, very low speed, high compatibility

# Marker used to designate Base85 encoded binary frames
B85_PREFIX = "!B85:"
MAX_RAW_STRING_LEN = 140
MAX_BINARY_PAYLOAD_LEN = 96  # 96 raw bytes -> 120 b85 chars + 5 char prefix = 125 chars (well within 140 limit)


class DspEngine:
    """
    Core DSP engine wrapping ggwave for acoustic modulation and demodulation.
    """

    def __init__(self, sample_rate: int = 48000, operating_mode: int = 6):
        """
        Initialize ggwave engine instance.
        :param sample_rate: Audio sample rate in Hz (default: 48000)
        :param operating_mode: ggwave operating mode bitmask (rx=2, tx=4, rx_and_tx=6)
        """
        self.sample_rate = sample_rate
        self.operating_mode = operating_mode
        self._instance = ggwave.init()
        self._is_closed = False
        logger.debug(f"DspEngine initialized with instance id: {self._instance}")

    def encode(
        self,
        payload: Union[str, bytes],
        protocol: ProtocolId = ProtocolId.FAST,
        volume: int = 50,
    ) -> np.ndarray:
        """
        Modulates a text or binary payload into float32 PCM audio samples at 48000 Hz.

        :param payload: Text (str) or binary (bytes) payload to transmit
        :param protocol: Modulation protocol (default ProtocolId.FAST)
        :param volume: Transmission volume (0 - 100)
        :return: 1D numpy array of float32 audio samples
        """
        if self._is_closed:
            raise RuntimeError("Cannot encode with a closed DspEngine instance.")

        if isinstance(payload, bytes):
            if len(payload) > MAX_BINARY_PAYLOAD_LEN:
                raise ValueError(
                    f"Binary payload length {len(payload)} exceeds max recommended {MAX_BINARY_PAYLOAD_LEN} bytes per packet."
                )
            b85_encoded = base64.b85encode(payload).decode("ascii")
            text_to_encode = f"{B85_PREFIX}{b85_encoded}"
        elif isinstance(payload, str):
            if len(payload) > MAX_RAW_STRING_LEN:
                raise ValueError(
                    f"Text payload length {len(payload)} exceeds max recommended {MAX_RAW_STRING_LEN} chars per packet."
                )
            text_to_encode = payload
        else:
            raise TypeError(f"Payload must be str or bytes, got {type(payload)}")

        # Call ggwave C++ core
        raw_pcm_bytes = ggwave.encode(text_to_encode, protocolId=int(protocol), volume=int(volume))
        if not raw_pcm_bytes:
            raise RuntimeError("ggwave failed to encode payload")

        # Convert to numpy float32 array
        samples = np.frombuffer(raw_pcm_bytes, dtype=np.float32)
        return samples

    def decode_samples(self, samples: Union[np.ndarray, bytes]) -> Optional[Union[str, bytes]]:
        """
        Feed audio samples into decoder. If a complete packet is received and verified,
        returns the decoded payload (bytes if was Base85 binary, str if was text).

        :param samples: Audio samples (either 1D np.float32 or raw bytes)
        :return: Decoded payload or None if still receiving/no packet found
        """
        if self._is_closed:
            raise RuntimeError("Cannot decode with a closed DspEngine instance.")

        if isinstance(samples, np.ndarray):
            if samples.dtype != np.float32:
                samples = samples.astype(np.float32)
            raw_bytes = samples.tobytes()
        elif isinstance(samples, (bytes, bytearray)):
            raw_bytes = bytes(samples)
        else:
            raise TypeError("Samples must be numpy.ndarray or bytes")

        result_bytes = ggwave.decode(self._instance, raw_bytes)
        if result_bytes:
            # Check if this was a Base85 encoded binary payload
            try:
                decoded_str = result_bytes.decode("utf-8")
                if decoded_str.startswith(B85_PREFIX):
                    raw_b85 = decoded_str[len(B85_PREFIX):]
                    return base64.b85decode(raw_b85)
                return decoded_str
            except UnicodeDecodeError:
                # Direct raw bytes returned
                return result_bytes

        return None

    def reset(self) -> None:
        """Reset internal receiver state while keeping instance active."""
        if not self._is_closed:
            # Reinitializing instance clears any stuck partial frame buffers
            self.close()
            self._instance = ggwave.init()
            self._is_closed = False

    def close(self) -> None:
        """Release underlying ggwave resources."""
        if not self._is_closed:
            try:
                # If ggwave has a free/cleanup function
                if hasattr(ggwave, "free"):
                    ggwave.free(self._instance)
            except Exception:
                pass
            self._is_closed = True

    def __enter__(self) -> DspEngine:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
