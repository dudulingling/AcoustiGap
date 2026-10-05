"""
AcoustiGap - Session Manager
Tracks active send and receive sessions, chunk reception, and integrity verification.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import logging
import time
from typing import Callable, Dict, List, Optional, Set, Tuple
import zlib

import numpy as np

from ..core.dsp import DspEngine, ProtocolId
from ..hardware.audio_stream import play_audio_samples
from .chunker import ChunkedFile, FileMetadata
from .packet import InvalidChecksumError, Packet, PacketError, PacketType

logger = logging.getLogger("acoustigap.session")


class TransferSessionReceiver:
    """
    State machine that processes received packets, tracks missing chunks,
    and reassembles the complete file with SHA-256 integrity verification.
    """

    def __init__(self):
        self.session_id: Optional[int] = None
        self.metadata: Optional[FileMetadata] = None
        self.received_chunks: Dict[int, bytes] = {}
        self.end_received: bool = False
        self.assembled_data: Optional[bytes] = None
        self.is_verified: bool = False
        self.errors_count: int = 0
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

    def feed_packet_data(self, raw_bytes: bytes) -> Optional[Packet]:
        """
        Feed deserialized raw binary data from DspEngine.
        Returns parsed Packet if valid, or None if corrupted/invalid.
        """
        try:
            packet = Packet.deserialize(raw_bytes)
        except InvalidChecksumError as e:
            logger.warning(f"Packet CRC error: {e}")
            self.errors_count += 1
            return None
        except PacketError as e:
            logger.warning(f"Invalid packet framing: {e}")
            self.errors_count += 1
            return None

        self._process_packet(packet)
        return packet

    def _process_packet(self, packet: Packet) -> None:
        if self.start_time is None:
            self.start_time = time.time()

        if self.session_id is None:
            self.session_id = packet.session_id
        elif packet.session_id != self.session_id:
            # Different session, ignore or log
            logger.warning(f"Ignored packet for session {packet.session_id} (active: {self.session_id})")
            return

        if packet.packet_type == PacketType.START_SESSION:
            try:
                self.metadata = FileMetadata.deserialize(packet.payload)
                logger.info(f"Session {self.session_id} started for file: {self.metadata.filename} ({self.metadata.file_size} bytes, {self.metadata.total_chunks} chunks)")
            except Exception as e:
                logger.error(f"Failed to parse START_SESSION metadata: {e}")

        elif packet.packet_type == PacketType.DATA_CHUNK:
            self.received_chunks[packet.chunk_index] = packet.payload
            logger.debug(f"Received chunk {packet.chunk_index + 1}/{packet.total_chunks}")

        elif packet.packet_type == PacketType.END_SESSION:
            self.end_received = True
            self.end_time = time.time()
            logger.info(f"Received END_SESSION for session {self.session_id}")

        self._try_assemble()

    def _try_assemble(self) -> bool:
        """Attempts to reassemble and verify full file if all chunks are present."""
        if not self.metadata:
            return False

        if len(self.received_chunks) < self.metadata.total_chunks:
            return False

        # All chunks present! Assemble in order
        ordered_payloads = [
            self.received_chunks[i] for i in range(self.metadata.total_chunks)
        ]
        combined = b"".join(ordered_payloads)

        # Decompress if needed
        if self.metadata.compressed:
            try:
                data = zlib.decompress(combined)
            except Exception as e:
                logger.error(f"Decompression failed: {e}")
                return False
        else:
            data = combined

        # Check SHA-256
        computed_hash = hashlib.sha256(data).hexdigest()
        if computed_hash == self.metadata.sha256:
            self.assembled_data = data
            self.is_verified = True
            logger.info(f"File {self.metadata.filename} successfully assembled & SHA-256 verified!")
            return True
        else:
            logger.error(f"SHA-256 mismatch! Got {computed_hash}, expected {self.metadata.sha256}")
            return False

    @property
    def progress_percent(self) -> float:
        if not self.metadata or self.metadata.total_chunks == 0:
            return 0.0
        return (len(self.received_chunks) / self.metadata.total_chunks) * 100.0

    @property
    def is_complete(self) -> bool:
        return self.is_verified and self.assembled_data is not None

    def missing_chunk_indices(self) -> List[int]:
        if not self.metadata:
            return []
        return [i for i in range(self.metadata.total_chunks) if i not in self.received_chunks]


class TransferSessionSender:
    """
    Manages transmitting a file packet by packet over acoustic channel.
    """

    def __init__(
        self,
        dsp_engine: DspEngine,
        protocol: ProtocolId = ProtocolId.FAST,
        volume: int = 50,
        inter_packet_delay: float = 0.08,  # 80ms guard interval for acoustic reverberation decay
    ):
        self.dsp = dsp_engine
        self.protocol = protocol
        self.volume = volume
        self.inter_packet_delay = inter_packet_delay

    def send_chunked_file(
        self,
        chunked: ChunkedFile,
        output_device_index: Optional[int] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> None:
        """
        Encodes and plays all packets sequentially through speaker.
        """
        total_packets = len(chunked.packets)
        logger.info(f"Starting transmission: {total_packets} packets for '{chunked.metadata.filename}'...")

        for idx, packet in enumerate(chunked.packets):
            serialized = packet.serialize()
            audio_samples = self.dsp.encode(
                serialized,
                protocol=self.protocol,
                volume=self.volume,
            )

            # Play audio through speakers
            play_audio_samples(
                audio_samples,
                device_index=output_device_index,
                sample_rate=self.dsp.sample_rate,
                blocking=True,
            )

            if progress_callback:
                progress_callback(idx + 1, total_packets)

            # Inter-packet guard interval
            if idx < total_packets - 1 and self.inter_packet_delay > 0:
                time.sleep(self.inter_packet_delay)

        logger.info("Transmission completed.")
