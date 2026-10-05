"""
AcoustiGap - Audio Device Management
Discovers, categorizes, and audits microphone and speaker devices.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import List, Optional

import sounddevice as sd

logger = logging.getLogger("acoustigap.devices")


@dataclass
class AudioDeviceInfo:
    index: int
    name: str
    hostapi_name: str
    max_input_channels: int
    max_output_channels: int
    default_samplerate: float

    @property
    def is_input(self) -> bool:
        return self.max_input_channels > 0

    @property
    def is_output(self) -> bool:
        return self.max_output_channels > 0

    def __str__(self) -> str:
        ch = f"{self.max_input_channels} in, {self.max_output_channels} out"
        return f"[{self.index}] {self.name} ({self.hostapi_name}) - {ch} @ {int(self.default_samplerate)}Hz"


def clean_device_name(name: str) -> str:
    """Clean device name by removing newlines, ugly Windows driver paths, and excess spaces."""
    import re
    # Remove newlines and carriage returns
    name = name.replace("\r", " ").replace("\n", " ")
    # Clean driver strings like @System32\drivers\bthhfenum.sys,#2;%1
    name = re.sub(r"@[^;]+;", "", name)
    name = re.sub(r"%[0-9]+", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def get_all_devices() -> List[AudioDeviceInfo]:
    """Return all available audio devices on the system."""
    devices = []
    hostapis = sd.query_hostapis()
    raw_devices = sd.query_devices()

    for idx, d in enumerate(raw_devices):
        hostapi_name = hostapis[d["hostapi"]]["name"] if d["hostapi"] < len(hostapis) else "Unknown"
        info = AudioDeviceInfo(
            index=idx,
            name=clean_device_name(d["name"]),
            hostapi_name=hostapi_name,
            max_input_channels=d["max_input_channels"],
            max_output_channels=d["max_output_channels"],
            default_samplerate=d["default_samplerate"],
        )
        devices.append(info)
    return devices



def list_input_devices() -> List[AudioDeviceInfo]:
    """Return all recording (microphone/input) devices."""
    return [d for d in get_all_devices() if d.is_input]


def list_output_devices() -> List[AudioDeviceInfo]:
    """Return all playback (speaker/output) devices."""
    return [d for d in get_all_devices() if d.is_output]


def get_default_input_device() -> Optional[AudioDeviceInfo]:
    """
    Get the preferred default input device.
    Prioritizes WASAPI Realtek Microphone if available for low-latency & bit-exact audio,
    otherwise falls back to OS default.
    """
    inputs = list_input_devices()
    if not inputs:
        return None

    # Try WASAPI Microphone first (Dell G5 optimal)
    for d in inputs:
        if "wasapi" in d.hostapi_name.lower() and "microphone" in d.name.lower():
            return d

    # Try MME / DirectSound default
    try:
        def_idx = sd.default.device[0]
        if def_idx >= 0:
            for d in inputs:
                if d.index == def_idx:
                    return d
    except Exception:
        pass

    return inputs[0]


def get_default_output_device() -> Optional[AudioDeviceInfo]:
    """
    Get preferred default output device.
    """
    outputs = list_output_devices()
    if not outputs:
        return None

    # Try WASAPI Speakers first
    for d in outputs:
        if "wasapi" in d.hostapi_name.lower() and ("speaker" in d.name.lower() or "headphone" in d.name.lower()):
            return d

    try:
        def_idx = sd.default.device[1]
        if def_idx >= 0:
            for d in outputs:
                if d.index == def_idx:
                    return d
    except Exception:
        pass

    return outputs[0]


def find_device(query: str, is_input: bool = True) -> Optional[AudioDeviceInfo]:
    """Find a device by case-insensitive name substring."""
    candidates = list_input_devices() if is_input else list_output_devices()
    q = query.lower()
    for d in candidates:
        if q in d.name.lower():
            return d
    return None
