# Reliable Peer Group Protocol (RPGP)

## 1. Introduction

RPGP is a decentralized application-layer protocol built on UDP that enables reliable group communication and distributed file sharing without a central server.

Every peer acts as both a client and a server.

## 2. Protocol Parameters

- Protocol version: 1
- Transport protocol: UDP
- Byte order: Big-endian
- Fixed header size: 34 bytes
- Maximum UDP payload: 1200 bytes
- Maximum application payload: 1166 bytes
- File chunk size: 262144 bytes (256 KiB)
- Replication factor: 2
- Heartbeat interval: 2 seconds
- Peer failure timeout: 6 seconds
- Initial retransmission timeout: 500 milliseconds
- Sliding window size: 32 packets
- File integrity algorithm: SHA-256

## 3. Packet Header Format

| Field | Size |
|---|---|
| Version | 1 byte |
| Message Type | 1 byte |
| Flags | 2 bytes |
| Sender Peer ID | 16 bytes |
| Sequence Number | 4 bytes |
| Acknowledgment Number | 4 bytes |
| Stream ID | 4 bytes |
| Payload Length | 2 bytes |

Total header size: 34 bytes.

All integer fields use unsigned big-endian representation.

Peer identifiers are represented using 128-bit UUIDs.

## 4. Message Types

| ID | Message |
|---|---|
| 1 | JOIN |
| 2 | JOIN_REPLY |
| 3 | HEARTBEAT |
| 4 | LEAVE |
| 5 | CHAT |
| 6 | ACK |
| 7 | PEER_UPDATE |
| 8 | FILE_ANNOUNCE |
| 9 | FILE_LIST_REQUEST |
| 10 | FILE_LIST_REPLY |
| 11 | CHUNK_STORE |
| 12 | CHUNK_REQUEST |
| 13 | CHUNK_DATA |
| 14 | CHUNK_CONFIRM |
| 15 | CHUNK_MAP_UPDATE |
| 16 | ERROR |

## 5. Reliability

RPGP uses sequence numbers, acknowledgments, retransmission timers, duplicate detection and selective-repeat sliding windows.

Independent stream identifiers allow multiple transfers to operate concurrently.

## 6. Peer Discovery

A new peer contacts any active bootstrap peer using a JOIN message.

The bootstrap peer provides the membership information through JOIN_REPLY.

After joining, the new peer communicates directly with other peers.

## 7. Group Chat

Each sender maintains an increasing chat message sequence number.

Receivers buffer out-of-order messages and discard duplicate messages.

Messages are delivered in sender-specific order.

## 8. Distributed File Storage

Each shared file is divided into fixed-size chunks, except the final chunk which may be smaller.

Each chunk is stored on at least two distinct peers when sufficient peers are available.

Replica placement must prevent a single storage peer from holding all chunks of a file.

SHA-256 hashes are used to verify file and chunk integrity.

## 9. Multi-Source Download

The downloading peer requests different chunks from multiple available peers concurrently.

If a source fails, unfinished chunks are requested from alternative replicas.

## 10. Fault Tolerance

Peers periodically exchange heartbeat messages.

A peer is considered inactive when no valid communication is received within the failure timeout.

Available replicas are used to recover interrupted downloads.

## 11. Protocol Specification Status

This document defines the initial protocol design. Exact payload schemas, flag semantics, fragmentation rules, acknowledgment behavior and operation state machines must be finalized before implementing their corresponding modules.

## 12. Packet Encoding and Validation

Header format: !BBH16sIIIH

Header byte offsets:

0       Version (1 byte)
1       Message type (1 byte)
2-3     Flags (2 bytes)
4-19    Sender UUID (16 bytes)
20-23   Sequence number (4 bytes)
24-27   Acknowledgment number (4 bytes)
28-31   Stream ID (4 bytes)
32-33   Payload length (2 bytes)
34+     Payload

## 13. Packet Flags

0x0000: No flags
0x0001: Reliable packet
0x0002: Final fragment

All other flag bits are reserved and must be zero.

## 14. Validation Rules

- Protocol version must be 1.
- Message type must be between 1 and 16.
- Minimum packet size is 34 bytes.
- Maximum packet size is 1200 bytes.
- Payload length must match the actual payload.
- Unknown flag bits are rejected.
- Invalid packets are discarded by the receiver.
- JSON payloads use UTF-8 encoding.
- Binary file data is transmitted as raw bytes.

Detailed transport and message payload rules will be
specified before implementing their respective modules.

## 15. Membership Protocol

Each peer generates a unique UUID at startup
and binds to its own UDP port.

Membership messages use UTF-8 JSON objects.

JOIN:
{"name":"peer2"}

JOIN_REPLY:
{"peer_id":"UUID","name":"peer1","host":"127.0.0.1","port":5001}

PEER_UPDATE:
Same payload format as JOIN_REPLY.

HEARTBEAT:
{"name":"peer2"}

LEAVE:
{"name":"peer2"}

JOIN_REPLY and PEER_UPDATE carry one peer
record per datagram.

The sender UUID in the header identifies
the actual sender of the datagram.

Membership messages use flags, sequence number,
acknowledgment number and stream ID set to zero.

A joining peer sends JOIN to a bootstrap peer.
The bootstrap peer responds with JOIN_REPLY
records and informs existing peers using
PEER_UPDATE.

Discovered addresses are contacted directly.
A peer becomes active after direct communication.

Every peer sends HEARTBEAT messages every
2 seconds and periodically exchanges known
active peer records.

Peers with no direct communication for
6 seconds are removed from the active list.

A graceful departure sends LEAVE to all
known active peers.

JOIN is retried until a peer is discovered.
Periodic membership exchanges recover lost
membership announcements.
