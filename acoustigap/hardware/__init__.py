"""
Hardware & Audio I/O layer for AcoustiGap.
"""

from .devices import (
    AudioDeviceInfo,
    list_input_devices,
    list_output_devices,
    get_default_input_device,
    get_default_output_device,
    find_device,
)
from .audio_stream import AudioReceiverStream, play_audio_samples
from .noise_meter import NoiseProfile, measure_noise_floor, analyze_audio_samples

__all__ = [
    "AudioDeviceInfo",
    "list_input_devices",
    "list_output_devices",
    "get_default_input_device",
    "get_default_output_device",
    "find_device",
    "AudioReceiverStream",
    "play_audio_samples",
    "NoiseProfile",
    "measure_noise_floor",
    "analyze_audio_samples",
]

