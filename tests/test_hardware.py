"""
Unit tests for Sub-Agent 2: Hardware & Audio I/O.
"""

import unittest
from acoustigap.hardware.devices import (
    list_input_devices,
    list_output_devices,
    get_default_input_device,
    get_default_output_device,
)


class TestHardware(unittest.TestCase):
    def test_list_input_devices(self):
        inputs = list_input_devices()
        self.assertIsInstance(inputs, list)
        self.assertGreater(len(inputs), 0)
        for dev in inputs:
            self.assertTrue(dev.is_input)
            self.assertGreater(dev.max_input_channels, 0)

    def test_list_output_devices(self):
        outputs = list_output_devices()
        self.assertIsInstance(outputs, list)
        self.assertGreater(len(outputs), 0)
        for dev in outputs:
            self.assertTrue(dev.is_output)
            self.assertGreater(dev.max_output_channels, 0)

    def test_get_default_devices(self):
        def_in = get_default_input_device()
        self.assertIsNotNone(def_in)
        self.assertTrue(def_in.is_input)

        def_out = get_default_output_device()
        self.assertIsNotNone(def_out)
        self.assertTrue(def_out.is_output)


if __name__ == "__main__":
    unittest.main()
