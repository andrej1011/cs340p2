import struct
import hashlib
import random

HEADER_SIZE = 6
HASH_SIZE = 16
fmt = '<c?I'
s = struct.Struct(fmt)

def pack(type, flag, sequence, data: bytes):
    if isinstance(data, str):
        data = data.encode()
    header = s.pack(type, flag, sequence)
    testmd5 = header + data
    md5 = hashlib.md5(testmd5).digest()
    packed = header + md5 + data
    return packed

def unpack(packed: bytes):
    header = packed[:HEADER_SIZE]
    try:
        type, flag, sequence = s.unpack(header)
    except struct.error:
        print("💥 ERROR: Could not unpack header.")
        return None, None, None, None

    received_hash = packed[HEADER_SIZE:HEADER_SIZE + HASH_SIZE]
    data = packed[HEADER_SIZE + HASH_SIZE:]
    testmd5 = header + data
    calculated_hash = hashlib.md5(testmd5).digest()

    if calculated_hash != received_hash:
        print("❌ HASH ERROR! DATA IS CORRUPTED!")
    else:
        print("✅ Hash check passed.")

    return type, flag, sequence, data

# === CORRUPTION FUNCTIONS ===

def corrupt_all_but_hash(packet: bytes) -> bytes:
    b = bytearray(packet)

    # Preserve hash
    preserved_hash = b[HEADER_SIZE:HEADER_SIZE + HASH_SIZE]

    # Corrupt header and data
    for i in range(len(b)):
        if i < HEADER_SIZE or i >= HEADER_SIZE + HASH_SIZE:
            b[i] = random.randint(0, 255)

    # Restore the original hash
    b[HEADER_SIZE:HEADER_SIZE + HASH_SIZE] = preserved_hash
    return bytes(b)

def corrupt_only_hash(packet: bytes) -> bytes:
    b = bytearray(packet)
    for i in range(HEADER_SIZE, HEADER_SIZE + HASH_SIZE):
        b[i] = random.randint(0, 255)
    return bytes(b)

# === MAIN ===

if __name__ == '__main__':
    print("=== Original Packet ===")
    original_packet = pack(b'A', True, 12, b'')
    unpack(original_packet)

    print("\n=== Corrupt Everything Except Hash ===")
    corrupted_packet1 = corrupt_all_but_hash(original_packet)
    unpack(corrupted_packet1)

    print("\n=== Corrupt Only the Hash ===")
    corrupted_packet2 = corrupt_only_hash(original_packet)
    unpack(corrupted_packet2)