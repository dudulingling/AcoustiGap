"""
AcoustiGap - File Chunker & Reassembly
Segments files into MTU chunks, compresses payloads (zlib), and computes SHA-256 integrity hashes.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import logging
import struct
from typing import Dict, List, Optional
import zlib

from .packet import Packet, PacketType

logger = logging.getLogger("acoustigap.chunker")

DEFAULT_CHUNK_SIZE = 64  # Optimal for ggwave packet sizing


@dataclass
class FileMetadata:
    filename: str
    file_size: int
    total_chunks: int
    sha256: str
    compressed: bool

    def serialize(self) -> bytes:
        # Binary compact format:
        # [raw sha256: 32B][size: 4B uint][chunks: 2B uint][compressed: 1B][name_len: 1B][filename: NB]
        raw_hash = bytes.fromhex(self.sha256)
        name_bytes = self.filename.encode("utf-8")[:32]
        return struct.pack("!32sIHBB", raw_hash, self.file_size, self.total_chunks, 1 if self.compressed else 0, len(name_bytes)) + name_bytes

    @classmethod
    def deserialize(cls, data: bytes) -> FileMetadata:
        raw_hash, file_size, total_chunks, compressed, name_len = struct.unpack_from("!32sIHBB", data, 0)
        filename = data[40 : 40 + name_len].decode("utf-8", errors="replace")
        return cls(
            filename=filename,
            file_size=file_size,
            total_chunks=total_chunks,
            sha256=raw_hash.hex(),
            compressed=bool(compressed),
        )



@dataclass
class ChunkedFile:
    metadata: FileMetadata
    packets: List[Packet]


class FileChunker:
    """Chunks arbitrary data or files into a sequence of verified Packets."""

    @staticmethod
    def chunk_data(
        data: bytes,
        filename: str = "payload.bin",
        session_id: int = 1,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        compress: bool = True,
    ) -> ChunkedFile:
        raw_size = len(data)
        sha256_hash = hashlib.sha256(data).hexdigest()

        # Optional zlib compression
        if compress and raw_size > 32:
            compressed_data = zlib.compress(data, level=9)
            if len(compressed_data) < raw_size:
                data_to_send = compressed_data
                is_compressed = True
            else:
                data_to_send = data
                is_compressed = False
        else:
            data_to_send = data
            is_compressed = False

        # Split data into chunks
        raw_chunks = [
            data_to_send[i : i + chunk_size]
            for i in range(0, len(data_to_send), chunk_size)
        ]
        total_chunks = len(raw_chunks)
        if total_chunks == 0:
            total_chunks = 1
            raw_chunks = [b""]

        metadata = FileMetadata(
            filename=filename,
            file_size=raw_size,
            total_chunks=total_chunks,
            sha256=sha256_hash,
            compressed=is_compressed,
        )

        packets = []
        # Packet 0: Metadata / START_SESSION
        start_packet = Packet(
            packet_type=PacketType.START_SESSION,
            session_id=session_id,
            chunk_index=0,
            total_chunks=total_chunks,
            payload=metadata.serialize(),
        )
        packets.append(start_packet)

        # Packets 1..N: DATA_CHUNK
        for idx, chunk_payload in enumerate(raw_chunks):
            p = Packet(
                packet_type=PacketType.DATA_CHUNK,
                session_id=session_id,
                chunk_index=idx,
                total_chunks=total_chunks,
                payload=chunk_payload,
            )
            packets.append(p)

        # Final packet: END_SESSION
        end_packet = Packet(
            packet_type=PacketType.END_SESSION,
            session_id=session_id,
            chunk_index=total_chunks,
            total_chunks=total_chunks,
            payload=sha256_hash[:16].encode("ascii"),
        )
        packets.append(end_packet)

        return ChunkedFile(metadata=metadata, packets=packets)
