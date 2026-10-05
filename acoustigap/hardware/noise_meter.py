"""
AcoustiGap - Noise Floor Analyzer & Audio Profiler
Measures ambient noise floor, RMS dBFS, Peak dBFS, and FFT frequency spectrum.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import List, Optional, Tuple

import numpy as np
from scipy import signal
import sounddevice as sd

from .devices import get_default_input_device

logger = logging.getLogger("acoustigap.noise_meter")


@dataclass
class NoiseProfile:
    rms_dbfs: float
    peak_dbfs: float
    top_noise_frequencies: List[Tuple[float, float]]  # (frequency_hz, magnitude_dbfs)
    sample_rate: int
    duration_seconds: float
    status: str  # "EXCELLENT", "ACCEPTABLE", "HIGH_NOISE"
    recommendation: str

    def summary(self) -> str:
        lines = [
            "============================================================",
            "             AMBIENT ACOUSTIC CHANNEL DIAGNOSTICS           ",
            "============================================================",
            f"- Sample Rate: {self.sample_rate:,} Hz",
            f"- Duration Analyzed: {self.duration_seconds:.1f} s",
            f"- RMS Noise Floor: {self.rms_dbfs:.2f} dBFS",
            f"- Peak Noise Level: {self.peak_dbfs:.2f} dBFS",
            f"- Channel Health: {self.status}",
            f"- Recommendation: {self.recommendation}",
            "",
            "Top Noise Frequencies:",
        ]
        for idx, (freq, mag) in enumerate(self.top_noise_frequencies[:5], 1):
            lines.append(f"  [{idx}] {freq:7.1f} Hz  |  {mag:.2f} dBFS")
        return "\n".join(lines)



def analyze_audio_samples(
    audio: np.ndarray,
    sample_rate: int = 48000,
) -> NoiseProfile:
    """
    Computes RMS, Peak, PSD Welch spectrum and health evaluation on 1D float32 audio.
    """
    if len(audio) == 0:
        raise ValueError("Audio buffer is empty")

    duration_seconds = len(audio) / sample_rate

    # Calculate RMS
    rms = float(np.sqrt(np.mean(np.square(audio))))
    rms_dbfs = float(20 * np.log10(rms + 1e-12))

    # Calculate Peak
    peak = float(np.max(np.abs(audio)))
    peak_dbfs = float(20 * np.log10(peak + 1e-12))

    # Calculate FFT spectrum via Welch's method
    nperseg = min(2048, len(audio))
    f, psd = signal.welch(audio, fs=sample_rate, nperseg=nperseg)
    psd_db = 10 * np.log10(psd + 1e-12)

    # Find dominant peaks
    peak_indices = np.argsort(psd_db)[::-1]
    top_freqs: List[Tuple[float, float]] = []
    seen_bins = set()

    for idx in peak_indices:
        freq = float(f[idx])
        b = int(freq // 100)
        if b not in seen_bins and freq > 20:  # Ignore sub-audible DC drift < 20Hz
            seen_bins.add(b)
            top_freqs.append((freq, float(psd_db[idx])))
            if len(top_freqs) >= 5:
                break

    # Categorize status & recommendation
    if rms_dbfs < -45:
        status = "EXCELLENT (< -45 dBFS - Quiet Room)"
        rec = "Optimal condition! Use FASTEST (or FAST) protocol for maximum throughput."
    elif rms_dbfs < -30:
        status = "ACCEPTABLE (-30 to -45 dBFS - Normal Room / Office)"
        rec = "Good condition. Recommended: FAST protocol with volume 60-75%."
    else:
        status = "HIGH_NOISE (> -30 dBFS - High Noise Environment)"
        rec = "Noisy room. Recommended: NORMAL protocol with volume 80-90% to prevent packet loss."

    return NoiseProfile(
        rms_dbfs=rms_dbfs,
        peak_dbfs=peak_dbfs,
        top_noise_frequencies=top_freqs,
        sample_rate=sample_rate,
        duration_seconds=duration_seconds,
        status=status,
        recommendation=rec,
    )


def measure_noise_floor(
    device_index: Optional[int] = None,
    duration_seconds: float = 2.0,
    sample_rate: int = 48000,
) -> NoiseProfile:
    """
    Records ambient audio for duration_seconds and computes noise floor metrics.
    """
    if device_index is None:
        dev = get_default_input_device()
        device_index = dev.index if dev else None

    num_samples = int(duration_seconds * sample_rate)
    logger.info(f"Recording {duration_seconds}s noise floor on device {device_index}...")

    # Record audio block
    recording = sd.rec(
        frames=num_samples,
        samplerate=sample_rate,
        channels=1,
        dtype="float32",
        device=device_index,
        blocking=True,
    )

    audio = recording[:, 0]
    return analyze_audio_samples(audio, sample_rate=sample_rate)
