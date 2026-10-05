"""
End-to-End integration test: Full file transmission over DSP acoustic loopback.
"""

import unittest
from acoustigap.core.dsp import DspEngine, ProtocolId
from acoustigap.protocol.chunker import FileChunker
from acoustigap.protocol.session import TransferSessionReceiver


class TestE2ETransfer(unittest.TestCase):
    def test_full_file_loopback_transfer(self):
        # 500 bytes of diverse binary and text payload
        test_payload = (
            b"--- ACOUSTIGAP TOP SECRET CONFIG ---\n"
            b"NodeID: PC-DELL-G5\n"
            b"Target: PHONE-LG-G8\n"
            b"Modulation: FSK-GGWAVE-FAST\n"
            b"CRC32: ENABLED\n"
            b"SHA256: ENABLED\n"
            + bytes(range(128)) * 2
        )

        chunked = FileChunker.chunk_data(
            test_payload,
            filename="config.bin",
            session_id=55,
            chunk_size=40,
            compress=True,
        )

        receiver = TransferSessionReceiver()
        dsp = DspEngine()

        for pkt in chunked.packets:
            wire_bytes = pkt.serialize()
            # Encode to acoustic audio samples
            audio_samples = dsp.encode(wire_bytes, protocol=ProtocolId.FAST)
            # Demodulate from audio samples
            decoded_bytes = dsp.decode_samples(audio_samples)
            self.assertIsNotNone(decoded_bytes)
            # Feed to receiver
            parsed_pkt = receiver.feed_packet_data(decoded_bytes)
            self.assertIsNotNone(parsed_pkt)

        # Check full file reassembly and SHA-256 match
        self.assertTrue(receiver.is_complete)
        self.assertEqual(receiver.assembled_data, test_payload)
        dsp.close()


if __name__ == "__main__":
    unittest.main()
