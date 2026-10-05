"""
Unit tests for Sub-Agent 1: DSP Core Engine.
"""

import unittest
from acoustigap.core.dsp import DspEngine, ProtocolId, MAX_RAW_STRING_LEN, MAX_BINARY_PAYLOAD_LEN


class TestDspEngine(unittest.TestCase):
    def setUp(self):
        self.engine = DspEngine()

    def tearDown(self):
        self.engine.close()

    def test_encode_decode_ascii_string(self):
        msg = "AcoustiGap Test"
        samples = self.engine.encode(msg, protocol=ProtocolId.FAST, volume=50)
        self.assertGreater(len(samples), 0)
        decoded = self.engine.decode_samples(samples)
        self.assertEqual(decoded, msg)

    def test_encode_decode_binary_payload(self):
        data = bytes([0x00, 0x11, 0x22, 0x33, 0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF])
        samples = self.engine.encode(data, protocol=ProtocolId.FAST, volume=50)
        decoded = self.engine.decode_samples(samples)
        self.assertEqual(decoded, data)

    def test_all_protocols_roundtrip(self):
        protocols = [
            ProtocolId.NORMAL,
            ProtocolId.FAST,
            ProtocolId.FASTEST,
            ProtocolId.ULTRASOUND_FAST,
        ]
        msg = "MultiProtoTest"
        for proto in protocols:
            with self.subTest(proto=proto.name):
                samples = self.engine.encode(msg, protocol=proto, volume=50)
                decoded = self.engine.decode_samples(samples)
                self.assertEqual(decoded, msg)

    def test_payload_length_limits(self):
        # Exceeding string length
        with self.assertRaises(ValueError):
            self.engine.encode("A" * (MAX_RAW_STRING_LEN + 1))

        # Exceeding binary length
        with self.assertRaises(ValueError):
            self.engine.encode(b"X" * (MAX_BINARY_PAYLOAD_LEN + 1))


if __name__ == "__main__":
    unittest.main()
