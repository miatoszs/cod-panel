"""IWI (Infinity Ward Image) dekóder - külső függőség nélkül.

A CoD .iwd csomagokban a textúrák .iwi fájlok: egy rövid fejléc, majd DXT1/3/5
tömörített (vagy tömörítetlen) képadat. A fájlban a mip szintek a legkisebbtől a
legnagyobbig követik egymást, ezért a teljes felbontású kép a fájl VÉGÉN van.

Bélyegképhez minden 4x4-es DXT blokkot egyetlen átlagszínre bontunk: ez egyben
negyedére kicsinyít, és 16-szor kevesebb munka, mint a teljes dekódolás.
"""
from __future__ import annotations

import struct
import zlib

MAGIC = b"IWi"

FMT_ARGB32 = 1
FMT_RGB24 = 2
FMT_GA16 = 3
FMT_A8 = 4
FMT_DXT1 = 11
FMT_DXT3 = 12
FMT_DXT5 = 13

BLOCK_BYTES = {FMT_DXT1: 8, FMT_DXT3: 16, FMT_DXT5: 16}
PIXEL_BYTES = {FMT_ARGB32: 4, FMT_RGB24: 3, FMT_GA16: 2, FMT_A8: 1}


class IwiError(Exception):
    pass


def parse_header(raw: bytes) -> tuple[int, int, int, int]:
    """-> (format, width, height, header_size)"""
    if len(raw) < 32 or raw[:3] != MAGIC:
        raise IwiError("nem IWI fájl")
    version = raw[3]
    if version not in (5, 6, 8):
        raise IwiError(f"ismeretlen IWI verzió: {version}")
    if version == 8:                       # Black Ops: 4 bájttal hosszabb fejléc
        fmt = raw[8]
        width, height = struct.unpack_from("<HH", raw, 10)
        header = 36
    else:
        fmt = raw[4]
        width, height = struct.unpack_from("<HH", raw, 6)
        header = 28
    if not (0 < width <= 8192 and 0 < height <= 8192):
        raise IwiError(f"értelmetlen méret: {width}x{height}")
    return fmt, width, height, header


def _top_mip_size(fmt: int, width: int, height: int) -> int:
    if fmt in BLOCK_BYTES:
        return max(1, (width + 3) // 4) * max(1, (height + 3) // 4) * BLOCK_BYTES[fmt]
    if fmt in PIXEL_BYTES:
        return width * height * PIXEL_BYTES[fmt]
    raise IwiError(f"nem támogatott pixelformátum: {fmt}")


def _rgb565(value: int) -> tuple[int, int, int]:
    r = (value >> 11) & 0x1F
    g = (value >> 5) & 0x3F
    b = value & 0x1F
    return (r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2)


def _dxt_block_average(block: bytes, offset: int) -> tuple[int, int, int]:
    """Egy 4x4-es DXT színblokk átlagszíne (ez lesz a bélyegkép egy pixele)."""
    c0, c1, bits = struct.unpack_from("<HHI", block, offset)
    r0, g0, b0 = _rgb565(c0)
    r1, g1, b1 = _rgb565(c1)
    if c0 > c1:
        palette = (
            (r0, g0, b0), (r1, g1, b1),
            ((2 * r0 + r1) // 3, (2 * g0 + g1) // 3, (2 * b0 + b1) // 3),
            ((r0 + 2 * r1) // 3, (g0 + 2 * g1) // 3, (b0 + 2 * b1) // 3),
        )
    else:
        palette = (
            (r0, g0, b0), (r1, g1, b1),
            ((r0 + r1) // 2, (g0 + g1) // 2, (b0 + b1) // 2),
            (0, 0, 0),
        )
    rs = gs = bs = 0
    for i in range(16):
        r, g, b = palette[(bits >> (2 * i)) & 3]
        rs += r
        gs += g
        bs += b
    return rs // 16, gs // 16, bs // 16


def decode_thumbnail(raw: bytes) -> tuple[int, int, bytearray]:
    """-> (szélesség, magasság, RGB bájtok). DXT-nél negyedelt méret."""
    fmt, width, height, header = parse_header(raw)
    need = _top_mip_size(fmt, width, height)
    if len(raw) < header + need:
        raise IwiError("csonka IWI fájl")
    data = raw[-need:]                      # a legnagyobb mip a fájl végén van

    if fmt in BLOCK_BYTES:
        step = BLOCK_BYTES[fmt]
        color_offset = 8 if step == 16 else 0   # DXT3/5: előbb az alfa blokk
        bw, bh = max(1, width // 4), max(1, height // 4)
        out = bytearray(bw * bh * 3)
        pos = 0
        for by in range(bh):
            row = by * bw * 3
            for bx in range(bw):
                r, g, b = _dxt_block_average(data, by * ((width + 3) // 4) * step
                                             + bx * step + color_offset)
                i = row + bx * 3
                out[i] = r
                out[i + 1] = g
                out[i + 2] = b
            pos += 1
        return bw, bh, out

    # tömörítetlen formátumok: minden 4. pixel (olcsó kicsinyítés)
    px = PIXEL_BYTES[fmt]
    bw, bh = max(1, width // 4), max(1, height // 4)
    out = bytearray(bw * bh * 3)
    for y in range(bh):
        src_row = y * 4 * width * px
        for x in range(bw):
            i = src_row + x * 4 * px
            o = (y * bw + x) * 3
            if fmt == FMT_ARGB32:            # BGRA sorrend
                out[o], out[o + 1], out[o + 2] = data[i + 2], data[i + 1], data[i]
            elif fmt == FMT_RGB24:
                out[o], out[o + 1], out[o + 2] = data[i + 2], data[i + 1], data[i]
            else:                            # GA16 / A8: szürkeárnyalat
                v = data[i]
                out[o] = out[o + 1] = out[o + 2] = v
    return bw, bh, out


def to_png(width: int, height: int, rgb: bytes) -> bytes:
    """Minimális PNG író (8 bites RGB), csak a stdlib zlib kell hozzá."""
    raw = bytearray()
    stride = width * 3
    for y in range(height):
        raw.append(0)                        # filter: None
        raw += rgb[y * stride:(y + 1) * stride]

    def chunk(tag: bytes, payload: bytes) -> bytes:
        return (struct.pack(">I", len(payload)) + tag + payload
                + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF))

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(raw), 6))
            + chunk(b"IEND", b""))


def iwi_to_png(raw: bytes) -> bytes:
    width, height, rgb = decode_thumbnail(raw)
    return to_png(width, height, rgb)
