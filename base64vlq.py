"""Decode and encode Base64 VLQ encoded sequences

Base64 VLQ is used in source maps.

VLQ values consist of 6 bits (matching the 64 characters of the Base64
alphabet), with the most significant bit a *continuation* flag. If the
flag is set, then the next character in the input is part of the same
integer value. Multiple VLQ character sequences so form an unbounded
integer value, in little-endian order.

The *first* VLQ value consists of a continuation flag, 4 bits for the
value, and the last bit the *sign* of the integer:

  +-----+-----+-----+-----+-----+-----+
  |  c  |  b3 |  b2 |  b1 |  b0 |  s  |
  +-----+-----+-----+-----+-----+-----+

while subsequent VLQ characters contain 5 bits of value:

  +-----+-----+-----+-----+-----+-----+
  |  c  |  b4 |  b3 |  b2 |  b1 |  b0 |
  +-----+-----+-----+-----+-----+-----+

For source maps, Base64 VLQ sequences can contain 1, 4 or 5 elements.

"""

from typing import Tuple

_b64chars = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
_b64table = [None] * (max(_b64chars) + 1)
for i, b in enumerate(_b64chars):
    _b64table[b] = i

_encode = _b64chars.decode().__getitem__
_shiftsize, _flag, _mask = 5, 1 << 5, (1 << 5) - 1


def base64vlq_decode(vlqval: str) -> Tuple[int]:
    """Decode Base64 VLQ value"""
    results = []
    add = results.append
    shiftsize, flag, mask = _shiftsize, _flag, _mask
    shift = value = 0
    # use byte values and a table to go from base64 characters to integers
    for v in map(_b64table.__getitem__, vlqval.encode("ascii")):
        value += (v & mask) << shift
        if v & flag:
            shift += shiftsize
            continue
        # determine sign and add to results
        add((value >> 1) * (-1 if value & 1 else 1))
        shift = value = 0
    return results


def base64vlq_encode(*values: int) -> str:
    """Encode integers to a VLQ value"""
    results = []
    add = results.append
    shiftsize, flag, mask = _shiftsize, _flag, _mask
    for v in values:
        # add sign bit
        v = (abs(v) << 1) | int(v < 0)
        while True:
            toencode, v = v & mask, v >> shiftsize
            add(toencode | (v and flag))
            if not v:
                break
    return bytes(map(_b64chars.__getitem__, results)).decode()
