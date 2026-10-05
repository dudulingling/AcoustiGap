"""
AcoustiGap - Binary Packet Framing
Defines packet structure, serialization, deserialization, and CRC32 verification.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
import struct
import zlib

MAGIC_HEADER = bytes([0xAC, 0x61])  # 'Aa' in ASCII
PROTOCOL_VERSION = 0x01

# Header format without CRC:
# Magic: 2s (2 bytes)
# Version: B (1 byte)
# Type: B (1 byte)
# SessionID: H (2 bytes, unsigned short)
# ChunkIndex: H (2 bytes, unsigned short)
# TotalChunks: H (2 bytes, unsigned short)
# PayloadLen: B (1 byte, unsigned char)
# Total header pre-CRC: 11 bytes
HEADER_PRE_CRC_FORMAT = "!2sBBHHHB"
HEADER_PRE_CRC_SIZE = struct.calcsize(HEADER_PRE_CRC_FORMAT)  # 11 bytes

# CRC format: I (4 bytes, unsigned int)
# Total header = 15 bytes
HEADER_FORMAT = "!2sBBHHHBI"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)  # 15 bytes


class PacketType(IntEnum):
    START_SESSION = 0x01   # Metadata packet: filename, size, sha256
    DATA_CHUNK = 0x02      # Chunk data payload
    END_SESSION = 0x03     # Transmission complete, final verification
    ACK = 0x04             # Acknowledge packet index
    NACK = 0x05            # Request retransmission of missing chunks
    PING = 0x06            # Link check ping
    PONG = 0x07            # Link check response


class PacketError(Exception):
    pass


class InvalidChecksumError(PacketError):
    pass


@dataclass
class Packet:
    packet_type: PacketType
    session_id: int
    chunk_index: int
    total_chunks: int
    payload: bytes
    crc32: int = 0

    def serialize(self) -> bytes:
        """
        Serialize packet to binary format:
        [Magic 2B][Version 1B][Type 1B][SessionID 2B][ChunkIdx 2B][TotalChunks 2B][PayloadLen 1B][CRC32 4B][Payload NB]
        """
        payload_bytes = bytes(self.payload)
        payload_len = len(payload_bytes)
        if payload_len > 255:
            raise ValueError(f"Payload length {payload_len} exceeds max 255 bytes")

        # 1. Pack header without CRC
        header_pre_crc = struct.pack(
            HEADER_PRE_CRC_FORMAT,
            MAGIC_HEADER,
            PROTOCOL_VERSION,
            int(self.packet_type),
            self.session_id & 0xFFFF,
            self.chunk_index & 0xFFFF,
            self.total_chunks & 0xFFFF,
            payload_len,
        )

        # 2. Compute CRC32 over header_pre_crc + payload
        data_to_crc = header_pre_crc + payload_bytes
        computed_crc = zlib.crc32(data_to_crc) & 0xFFFFFFFF
        self.crc32 = computed_crc

        # 3. Final serialization with CRC
        header = struct.pack(
            HEADER_FORMAT,
            MAGIC_HEADER,
            PROTOCOL_VERSION,
            int(self.packet_type),
            self.session_id & 0xFFFF,
            self.chunk_index & 0xFFFF,
            self.total_chunks & 0xFFFF,
            payload_len,
            computed_crc,
        )
        return header + payload_bytes

    @classmethod
    def deserialize(cls, data: bytes) -> Packet:
        """
        Parse binary data into Packet, verifying magic bytes, version, and CRC32.
        """
        if len(data) < HEADER_SIZE:
            raise PacketError(f"Data length {len(data)} is less than header size {HEADER_SIZE}")

        magic, version, pkt_type_raw, sess_id, chunk_idx, total_chunks, payload_len, packet_crc = struct.unpack_from(
            HEADER_FORMAT, data, 0
        )

        if magic != MAGIC_HEADER:
            raise PacketError(f"Invalid magic header: {magic.hex()} != {MAGIC_HEADER.hex()}")

        if version != PROTOCOL_VERSION:
            raise PacketError(f"Unsupported protocol version: {version}")

        try:
            pkt_type = PacketType(pkt_type_raw)
        except ValueError:
            raise PacketError(f"Unknown packet type: {pkt_type_raw}")

        expected_total_len = HEADER_SIZE + payload_len
        if len(data) < expected_total_len:
            raise PacketError(
                f"Packet incomplete: expected {expected_total_len} bytes, got {len(data)}"
            )

        payload = data[HEADER_SIZE : HEADER_SIZE + payload_len]

        # Verify CRC32
        header_pre_crc = struct.pack(
            HEADER_PRE_CRC_FORMAT,
            magic,
            version,
            pkt_type_raw,
            sess_id,
            chunk_idx,
            total_chunks,
            payload_len,
        )
        expected_crc = zlib.crc32(header_pre_crc + payload) & 0xFFFFFFFF
        if packet_crc != expected_crc:
            raise InvalidChecksumError(
                f"CRC32 mismatch! Got {packet_crc:#010x}, expected {expected_crc:#010x}"
            )

        return cls(
            packet_type=pkt_type,
            session_id=sess_id,
            chunk_index=chunk_idx,
            total_chunks=total_chunks,
            payload=payload,
            crc32=packet_crc,
        )
