"""Binary-Protokoll v1. struct, kein FlatBuffers.

Frame = Header + Payload. Der Master-Tick steht in JEDEM Frame-Header –
der Client interpoliert gegen diesen Zähler, nie gegen seine Uhr.

Header (16 Byte, network byte order):
  !4s B B H I I Q
  magic(4) | frame_type(1) | flags(1) | reserved(2) | tick(4)
  | payload_len(4) | session(8)

Frame-Typen:
  0x01 KEYFRAME  quantisierter Chunk-Zustand (Phase 2)
  0x02 EVENT     diskretes Ereignis (Phase 2)
  0x03 CHECKSUM  Chunk-Hash zur Drift-Korrektur (Phase 2)
  0x04 COMMAND   Client -> Server (Befehl, nie Zustand)
  0x10 RAW_FIELD Vollbild uint8-Quantisierung – nur Phase 1 (Verifikation)
"""
from __future__ import annotations
import struct
from dataclasses import dataclass

MAGIC = b"SMF1"
HEADER = struct.Struct("!4sBBHIIQ")
HEADER_LEN = HEADER.size  # 24

FRAME_KEYFRAME = 0x01
FRAME_EVENT = 0x02
FRAME_CHECKSUM = 0x03
FRAME_COMMAND = 0x04
FRAME_RAW_FIELD = 0x10

@dataclass
class Frame:
    frame_type: int
    flags: int
    tick: int
    session: int
    payload: bytes

    def pack(self) -> bytes:
        return HEADER.pack(MAGIC, self.frame_type, self.flags, 0,
                           self.tick, len(self.payload), self.session) + self.payload

def unpack(data: bytes) -> Frame:
    magic, ftype, flags, _, tick, plen, session = HEADER.unpack_from(data)
    if magic != MAGIC:
        raise ValueError("bad magic")
    payload = data[HEADER_LEN:HEADER_LEN + plen]
    return Frame(ftype, flags, tick, session, payload)

def quantize_field_u8(field, fixed_max) -> bytes:
    """int32 Fixed-Point -> uint8-Rohbild für Frame 0x10."""
    import numpy as np
    norm = np.clip(field.astype(np.float64) / fixed_max, 0.0, 1.0)
    return (norm * 255).astype(np.uint8).tobytes()