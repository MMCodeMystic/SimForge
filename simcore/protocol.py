"""Binary-Protokoll v1. struct, kein FlatBuffers.

Header (24 Byte, network byte order): !4sBBHIIQ
  magic(4) | frame_type(1) | flags(1) | reserved(2)
  | tick(4) | payload_len(4) | session(8)

Frames:
  0x01 KEYFRAME  Payload: u8 cx, u8 cy, u8[64*64] quantisierte Zellen
  0x02 EVENT     Payload: u8 ev_type, u16 x, u16 y, u32 amount
  0x03 CHECKSUM  Payload: u16 count, dann pro Eintrag: u8 cx, u8 cy, u32 hash
  0x04 COMMAND   Client -> Server (s.u.)
  0x10 RAW_FIELD veraltet (Phase 1), wird nicht mehr gesendet

Commands (Payload[0] = Code):
  0x01 SUBSCRIBE_AOI  u16 x0, u16 y0, u16 x1, u16 y1
  0x02 REQ_KEYFRAME   u8 count, dann count × (u8 cx, u8 cy)
  0x03 PLACE_FOOD     u16 x, u16 y

Events (Payload[0] = Code):
  0x01 EV_FOOD        Futter platziert bei x,y mit amount
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
FRAME_RAW_FIELD = 0x10  # deprecated

CMD_SUBSCRIBE_AOI = 0x01
CMD_REQ_KEYFRAME = 0x02
CMD_PLACE_FOOD = 0x03

EV_FOOD = 0x01

_EV = struct.Struct("!BHHI")
_CS_ENTRY = struct.Struct("!BBI")

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
    return Frame(ftype, flags, tick, session, data[HEADER_LEN:HEADER_LEN + plen])

def pack_keyframe(cx: int, cy: int, chunk_data: bytes) -> bytes:
    return struct.pack("!BB", cx, cy) + chunk_data

def pack_checksums(entries: list[tuple[int, int, int]]) -> bytes:
    b = struct.pack("!H", len(entries))
    for cx, cy, h in entries:
        b += _CS_ENTRY.pack(cx, cy, h)
    return b

def pack_event(ev_type: int, x: int, y: int, amount: int) -> bytes:
    return _EV.pack(ev_type, x, y, amount)