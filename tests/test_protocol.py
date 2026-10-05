"""
Unit tests for Sub-Agent 3: Framing & Transfer Protocol.
"""

import unittest
from acoustigap.protocol.packet import (
    Packet,
    PacketType,
    PacketError,
    InvalidChecksumError,
    MAGIC_HEADER,
    PROTOCOL_VERSION,
)
from acoustigap.protocol.chunker import FileChunker, FileMetadata
from acoustigap.protocol.session import TransferSessionReceiver


class TestProtocol(unittest.TestCase):
    def test_packet_serialization_roundtrip(self):
        payload = b"Hello Acoustic Packet World"
        pkt = Packet(
            packet_type=PacketType.DATA_CHUNK,
            session_id=101,
            chunk_index=2,
            total_chunks=5,
            payload=payload,
        )
        serialized = pkt.serialize()
        self.assertGreater(len(serialized), 15)

        deserialized = Packet.deserialize(serialized)
        self.assertEqual(deserialized.packet_type, PacketType.DATA_CHUNK)
        self.assertEqual(deserialized.session_id, 101)
        self.assertEqual(deserialized.chunk_index, 2)
        self.assertEqual(deserialized.total_chunks, 5)
        self.assertEqual(deserialized.payload, payload)
        self.assertEqual(deserialized.crc32, pkt.crc32)

    def test_corrupted_crc_detection(self):
        pkt = Packet(
            packet_type=PacketType.DATA_CHUNK,
            session_id=1,
            chunk_index=0,
            total_chunks=1,
            payload=b"Authentic Data",
        )
        serialized = bytearray(pkt.serialize())
        # Corrupt one bit in payload
        serialized[-1] ^= 0x01

        with self.assertRaises(InvalidChecksumError):
            Packet.deserialize(bytes(serialized))

    def test_invalid_magic_header(self):
        bad_data = b"\x00\x00" + b"\x01" * 20
        with self.assertRaises(PacketError):
            Packet.deserialize(bad_data)

    def test_file_metadata_serialization(self):
        meta = FileMetadata(
            filename="document.pdf",
            file_size=1024,
            total_chunks=16,
            sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            compressed=True,
        )
        raw = meta.serialize()
        restored = FileMetadata.deserialize(raw)
        self.assertEqual(restored.filename, meta.filename)
        self.assertEqual(restored.file_size, meta.file_size)
        self.assertEqual(restored.total_chunks, meta.total_chunks)
        self.assertEqual(restored.sha256, meta.sha256)
        self.assertEqual(restored.compressed, meta.compressed)

    def test_file_chunking(self):
        test_data = b"Testing AcoustiGap file chunker " * 50
        chunked = FileChunker.chunk_data(test_data, filename="test.txt", chunk_size=32)
        self.assertGreater(chunked.metadata.total_chunks, 1)
        # Verify first is START_SESSION, middle are DATA_CHUNK, last is END_SESSION
        self.assertEqual(chunked.packets[0].packet_type, PacketType.START_SESSION)
        for p in chunked.packets[1:-1]:
            self.assertEqual(p.packet_type, PacketType.DATA_CHUNK)
        self.assertEqual(chunked.packets[-1].packet_type, PacketType.END_SESSION)


if __name__ == "__main__":
    unittest.main()
