import uuid
import unittest

from protocol import (
    Packet,
    MessageType,
    PacketFlag,
    encode_packet,
    decode_packet,
    encode_json,
    decode_json
)


class ProtocolTests(unittest.TestCase):

    def setUp(self):
        self.packet = Packet(
            message_type=MessageType.CHAT,
            sender_id=uuid.uuid4(),
            sequence_number=1,
            stream_id=1,
            flags=PacketFlag.RELIABLE,
            payload=encode_json({
                "message": "Hello everyone"
            })
        )

    def test_packet_roundtrip(self):
        encoded = encode_packet(self.packet)
        decoded = decode_packet(encoded)
        self.assertEqual(self.packet, decoded)

    def test_json(self):
        data = {"message": "Hello everyone"}
        self.assertEqual(
            decode_json(encode_json(data)),
            data
        )

    def test_short_packet(self):
        with self.assertRaises(ValueError):
            decode_packet(b"abc")

    def test_large_payload(self):
        self.packet.payload = b"x" * 2000
        with self.assertRaises(ValueError):
            encode_packet(self.packet)

    def test_invalid_version(self):
        encoded = encode_packet(self.packet)
        invalid = bytes([99]) + encoded[1:]
        with self.assertRaises(ValueError):
            decode_packet(invalid)

    def test_payload_mismatch(self):
        encoded = encode_packet(self.packet)
        with self.assertRaises(ValueError):
            decode_packet(encoded[:-1])

    def test_invalid_message_type(self):
        encoded = bytearray(encode_packet(self.packet))
        encoded[1] = 99
        with self.assertRaises(ValueError):
            decode_packet(bytes(encoded))

    def test_invalid_flags(self):
        self.packet.flags = 8
        with self.assertRaises(ValueError):
            encode_packet(self.packet)


if __name__ == "__main__":
    unittest.main()
