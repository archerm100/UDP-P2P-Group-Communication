import struct
import uuid
import json

from enum import IntEnum, IntFlag
from dataclasses import dataclass

from config import (
    PROTOCOL_VERSION,
    HEADER_FORMAT,
    HEADER_SIZE,
    MAX_PACKET_SIZE,
    MAX_PAYLOAD_SIZE
)


class MessageType(IntEnum):
    JOIN = 1
    JOIN_REPLY = 2
    HEARTBEAT = 3
    LEAVE = 4
    CHAT = 5
    ACK = 6
    PEER_UPDATE = 7
    FILE_ANNOUNCE = 8
    FILE_LIST_REQUEST = 9
    FILE_LIST_REPLY = 10
    CHUNK_STORE = 11
    CHUNK_REQUEST = 12
    CHUNK_DATA = 13
    CHUNK_CONFIRM = 14
    CHUNK_MAP_UPDATE = 15
    ERROR = 16


class PacketFlag(IntFlag):
    NONE = 0
    RELIABLE = 1
    FINAL_FRAGMENT = 2


@dataclass
class Packet:
    message_type: MessageType
    sender_id: uuid.UUID
    sequence_number: int = 0
    acknowledgment_number: int = 0
    stream_id: int = 0
    flags: int = 0
    payload: bytes = b""
    version: int = PROTOCOL_VERSION


def encode_packet(packet):
    """Convert a Packet object into binary bytes."""

    if packet.version != PROTOCOL_VERSION:
        raise ValueError("Invalid protocol version")

    MessageType(packet.message_type)

    if packet.flags & ~3:
        raise ValueError("Invalid packet flags")

    if len(packet.payload) > MAX_PAYLOAD_SIZE:
        raise ValueError("Payload is too large")

    header = struct.pack(
        HEADER_FORMAT,
        packet.version,
        int(packet.message_type),
        int(packet.flags),
        packet.sender_id.bytes,
        packet.sequence_number,
        packet.acknowledgment_number,
        packet.stream_id,
        len(packet.payload)
    )

    return header + packet.payload


def decode_packet(data):
    """Convert received binary bytes into a Packet."""

    if len(data) < HEADER_SIZE:
        raise ValueError("Packet is too small")

    if len(data) > MAX_PACKET_SIZE:
        raise ValueError("Packet is too large")

    (
        version,
        message_type,
        flags,
        sender_id,
        sequence_number,
        acknowledgment_number,
        stream_id,
        payload_length
    ) = struct.unpack(
        HEADER_FORMAT,
        data[:HEADER_SIZE]
    )

    if version != PROTOCOL_VERSION:
        raise ValueError("Unsupported protocol version")

    if flags & ~3:
        raise ValueError("Invalid packet flags")

    payload = data[HEADER_SIZE:]

    if len(payload) != payload_length:
        raise ValueError("Payload length mismatch")

    return Packet(
        message_type=MessageType(message_type),
        sender_id=uuid.UUID(bytes=sender_id),
        sequence_number=sequence_number,
        acknowledgment_number=acknowledgment_number,
        stream_id=stream_id,
        flags=flags,
        payload=payload,
        version=version
    )


def encode_json(data):
    """Convert Python data into UTF-8 JSON bytes."""
    return json.dumps(
        data,
        separators=(",", ":")
    ).encode("utf-8")


def decode_json(data):
    """Convert UTF-8 JSON bytes into Python data."""
    return json.loads(data.decode("utf-8"))
