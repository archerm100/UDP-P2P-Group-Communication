# RPGP - Reliable Peer Group Protocol

# Network settings
HOST = "127.0.0.1"
DEFAULT_PORT = 5001

# Protocol settings
PROTOCOL_VERSION = 1
HEADER_FORMAT = "!BBH16sIIIH"
HEADER_SIZE = 34
MAX_PACKET_SIZE = 1200
MAX_PAYLOAD_SIZE = MAX_PACKET_SIZE - HEADER_SIZE

# Reliability settings
WINDOW_SIZE = 32
RETRANSMISSION_TIMEOUT = 0.5
MAX_RETRIES = 20

# Membership settings
HEARTBEAT_INTERVAL = 2
PEER_TIMEOUT = 6

# Distributed file storage settings
CHUNK_SIZE = 256 * 1024
REPLICATION_FACTOR = 2
MIN_PEERS = 4

# Directory settings
STORAGE_DIR = "storage"
DOWNLOAD_DIR = "downloads"
SHARED_DIR = "shared"
RESULTS_DIR = "results"

# Packet loss simulation
PACKET_LOSS_RATE = 0.0
