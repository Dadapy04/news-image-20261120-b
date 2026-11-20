"""Sum up 20 November 2026's world news in one image.

Reads a fixed news fixture (news.json) and renders a single editorial poster:
a world-day front page where every story is a band whose width is its share
of the day's coverage weight, plus a headline masthead and a wire strip.

Pure standard library (zlib + struct), so it runs anywhere Python 3 runs:
no fonts to install, no image libraries to fetch. Every glyph is drawn from
an embedded 5x7 bitmap font, so the output is byte-identical on every run.

    python3 main.py            # writes out/2026-11-20.png
    python3 main.py --check    # renders twice, asserts identical bytes
    python3 main.py --stats    # prints fixture stats and canvas size, no file
"""

from __future__ import annotations

import json
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
NEWS_PATH = os.path.join(HERE, "news.json")
OUT_DIR = os.path.join(HERE, "out")
OUT_NAME = "2026-11-20.png"

# ---------------------------------------------------------------------------
# Canvas
# ---------------------------------------------------------------------------

W, H = 1600, 2900
SCALE = 2  # drawn at 1x, emitted at 2x for crisp edges

INK = (13, 15, 18, 255)
PAPER = (243, 239, 230, 255)
DIM = (120, 116, 108, 255)
RULE = (196, 190, 178, 255)
ACCENT = (176, 42, 36, 255)
COOL = (32, 58, 96, 255)

# Band accents, assigned per story by index so the palette is stable.
BAND_COLORS = [
    (176, 42, 36, 255),
    (32, 58, 96, 255),
    (120, 92, 30, 255),
    (58, 78, 62, 255),
    (92, 44, 78, 255),
    (30, 86, 92, 255),
]

# ---------------------------------------------------------------------------
# 5x7 bitmap font — uppercase, digits, and the punctuation the poster needs.
# Each glyph is 7 rows of 5 bits, high bit first, as hex strings.
# ---------------------------------------------------------------------------

_GLYPHS = {
    " ": "0000000000000",
    "A": "0E11111F111111",
    "B": "1E11111E11111E",
    "C": "0E11101010110E",
    "D": "1E11111111111E",
    "E": "1F10101E10101F",
    "F": "1F10101E101010",
    "G": "0E11101711110F",
    "H": "1111111F111111",
    "I": "0E04040404040E",
    "J": "0702020202120C",
    "K": "11121418141211",
    "L": "1010101010101F",
    "M": "111B1515111111",
    "N": "11111915131111",
    "O": "0E11111111110E",
    "P": "1E11111E101010",
    "Q": "0E11111115120D",
    "R": "1E11111E141211",
    "S": "0F10100E01011E",
    "T": "1F040404040404",
    "U": "1111111111110E",
    "V": "11111111110A04",
    "W": "11111115151B11",
    "X": "11110A040A1111",
    "Y": "11110A04040404",
    "Z": "1F01020408101F",
    "0": "0E11131519110E",
    "1": "040C040404040E",
    "2": "0E11010204081F",
    "3": "1F02040201110E",
    "4": "02060A121F0202",
    "5": "1F101E0101110E",
    "6": "0608101E11110E",
    "7": "1F010204080808",
    "8": "0E11110E11110E",
    "9": "0E11110F01020C",
    ".": "00000000000C0C",
    ",": "000000000C0408",
    ":": "000C0C000C0C00",
    ";": "000C0C000C0408",
    "-": "0000001F000000",
    "/": "01010204081010",
    "%": "18190204081303",
    "'": "04040400000000",
    '"': "0A0A0A00000000",
    "(": "02040808080402",
    ")": "08040202020408",
    "!": "04040404040004",
    "?": "0E110102040004",
    "+": "0004041F040400",
    "&": "0C12140815120D",
    "#": "0A0A1F0A1F0A0A",
    "*": "000A041F040A00",
    "@": "0E11171515110E",
    "=": "00001F001F0000",
}

FONT_W, FONT_H = 5, 7


def _glyph(ch: str) -> str:
    return _GLYPHS.get(ch, _GLYPHS["?"])


def _up(s: str) -> str:
    """Poster is all-caps: the bitmap font carries no lowercase."""
    return s.upper()


def text_width(text: str, px: int) -> int:
    """Width in device pixels of `text` at glyph pixel size `px`."""
    text = _up(text)
    if not text:
        return 0
    return len(text) * (FONT_W * px + px) - px


def glyph_rows(ch: str):
    """Yield (row_index, bitmask) for the 7 rows of a glyph."""
    bits = _glyph(ch)
    for r in range(FONT_H):
        row = bits[r * 2: r * 2 + 2]
        yield r, int(row, 16)


# ---------------------------------------------------------------------------
# Canvas primitives
# ---------------------------------------------------------------------------


class Canvas:
    def __init__(self, w: int, h: int, fill):
        self.w = w
        self.h = h
        self.px = bytearray()
        r, g, b, a = fill
        row = bytes((r, g, b, a)) * w
        for _ in range(h):
            self.px.extend(row)

    def blend(self, x: int, y: int, color) -> None:
        if x < 0 or y < 0 or x >= self.w or y >= self.h:
            return
        i = (y * self.w + x) * 4
        cr, cg, cb, ca = color
        if ca == 255:
            self.px[i] = cr
            self.px[i + 1] = cg
            self.px[i + 2] = cb
            self.px[i + 3] = 255
            return
        if ca == 0:
            return
        a = ca / 255.0
        ia = 1.0 - a
        self.px[i] = int(cr * a + self.px[i] * ia)
        self.px[i + 1] = int(cg * a + self.px[i + 1] * ia)
        self.px[i + 2] = int(cb * a + self.px[i + 2] * ia)
        self.px[i + 3] = 255

    def rect(self, x: int, y: int, w: int, h: int, color) -> None:
        for yy in range(y, y + h):
            self.blend(x, yy, color)  # bounds check once per row

    def fill_rect(self, x: int, y: int, w: int, h: int, color) -> None:
        for yy in range(y, y + h):
            if yy < 0 or yy >= self.h:
                continue
            for xx in range(x, x + w):
                self.blend(xx, yy, color)

    def hline(self, x: int, y: int, length: int, color, thickness: int = 1) -> None:
        for t in range(thickness):
            self.fill_rect(x, y + t, length, 1, color)

    def text(self, x: int, y: int, s: str, px: int, color) -> int:
        """Draw `s`; return the x after the last glyph."""
        s = _up(s)
        cx = x
        step = FONT_W * px + px
        for ch in s:
            if ch != " ":
                for r, mask in glyph_rows(ch):
                    if not mask:
                        continue
                    for c in range(FONT_W):
                        if mask & (1 << (FONT_W - 1 - c)):
                            self.fill_rect(
                                cx + c * px, y + r * px, px, px, color
                            )
            cx += step
        return cx

    def text_center(self, cx: int, y: int, s: str, px: int, color) -> None:
        self.text(cx - text_width(s, px) // 2, y, s, px, color)

    def text_wrap(self, x: int, y: int, s: str, px: int, color,
                  max_w: int, line_gap: int = None) -> int:
        """Word-wrap `s` to `max_w`; return the y after the last line."""
        if line_gap is None:
            line_gap = px * (FONT_H + 3)
        words = _up(s).split()
        line = ""
        cy = y
        for word in words:
            probe = word if not line else line + " " + word
            if text_width(probe, px) <= max_w or not line:
                line = probe
            else:
                self.text(x, cy, line, px, color)
                cy += line_gap
                line = word
        if line:
            self.text(x, cy, line, px, color)
            cy += line_gap
        return cy

    def to_png(self, path: str) -> None:
        raw = bytearray()
        stride = self.w * 4
        for y in range(self.h):
            raw.append(0)  # filter type 0
            raw.extend(self.px[y * stride:(y + 1) * stride])

        def chunk(tag: bytes, data: bytes) -> bytes:
            return (
                struct.pack(">I", len(data))
                + tag
                + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
            )

        ihdr = struct.pack(">IIBBBBB", self.w, self.h, 8, 6, 0, 0, 0)
        png = (
            b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b"")
        )
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(png)


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

MARGIN = 70
CONTENT_W = W - 2 * MARGIN


def draw_masthead(cv: Canvas, news: dict) -> int:
    y = MARGIN
    cv.fill_rect(MARGIN, y, CONTENT_W, 6, INK)
    y += 26

    cv.text(MARGIN, y, news["edition"], 3, ACCENT)
    right = f"NO. {news['issue']}"
    cv.text(W - MARGIN - text_width(right, 3), y, right, 3, DIM)
    y += 34

    cv.text_center(W // 2, y, "THE WORLD", 11, INK)
    y += 11 * FONT_H + 20
    cv.text_center(W // 2, y, "IN ONE IMAGE", 7, INK)
    y += 7 * FONT_H + 26

    cv.hline(MARGIN, y, CONTENT_W, INK, 3)
    y += 12
    cv.text_center(W // 2, y, news["dateline"], 4, ACCENT)
    y += 4 * FONT_H + 16
    cv.hline(MARGIN, y, CONTENT_W, RULE, 1)
    y += 24
    return y


def draw_lede(cv: Canvas, news: dict, y: int) -> int:
    """The day's single dominant story, full width."""
    top = news["stories"][0]
    cv.text(MARGIN, y, "THE DAY", 3, DIM)
    y += 3 * FONT_H + 12

    cv.fill_rect(MARGIN, y, 10, 8 * FONT_H + 30, ACCENT)
    y_text = y + 4
    y_text = cv.text_wrap(MARGIN + 30, y_text, top["headline"], 6, INK, CONTENT_W - 40)
    y = max(y_text + 10, y + 8 * FONT_H + 34)

    y = cv.text_wrap(MARGIN, y, top["summary"], 4, DIM, CONTENT_W, 4 * (FONT_H + 4))
    y += 14
    src = "SOURCE: " + " / ".join(top["sources"])
    cv.text(MARGIN, y, src, 2, RULE)
    y += 2 * FONT_H + 24
    cv.hline(MARGIN, y, CONTENT_W, RULE, 2)
    y += 26
    return y


def draw_bands(cv: Canvas, news: dict, y: int) -> int:
    """Every other story as a proportional band: width = coverage weight."""
    stories = news["stories"][1:]
    total = sum(s["weight"] for s in stories) or 1

    cv.text(MARGIN, y, "THE REST OF THE DAY", 3, DIM)
    y += 3 * FONT_H + 16

    bar_y = y
    bar_h = 26
    # Accumulate in floats and round the running edge, so no rounding drift.
    x = MARGIN
    acc = 0.0
    for i, story in enumerate(stories):
        acc += story["weight"]
        edge = MARGIN + int(round(CONTENT_W * acc / total))
        if i == len(stories) - 1:
            edge = MARGIN + CONTENT_W
        seg = edge - x
        cv.fill_rect(x, bar_y, max(seg - 4, 2), bar_h, BAND_COLORS[i % len(BAND_COLORS)])
        x = edge
    y = bar_y + bar_h + 30

    for i, story in enumerate(stories):
        color = BAND_COLORS[i % len(BAND_COLORS)]
        cv.fill_rect(MARGIN, y + 6, 14, 14, color)
        cv.text(MARGIN + 30, y, story["kicker"], 3, color)
        y += 3 * FONT_H + 12
        y = cv.text_wrap(MARGIN + 30, y, story["headline"], 4, INK, CONTENT_W - 40,
                         4 * (FONT_H + 3))
        y = cv.text_wrap(MARGIN + 30, y, story["summary"], 3, DIM, CONTENT_W - 40,
                         3 * (FONT_H + 4))
        y += 8
        cv.text(MARGIN + 30, y, "SOURCE: " + " / ".join(story["sources"]), 2, RULE)
        y += 2 * FONT_H + 22
        if i < len(stories) - 1:
            cv.hline(MARGIN, y, CONTENT_W, RULE, 1)
            y += 24
    return y


def draw_wire(cv: Canvas, news: dict, y: int) -> int:
    y += 10
    cv.hline(MARGIN, y, CONTENT_W, INK, 3)
    y += 22
    cv.text(MARGIN, y, "ALSO ON THE WIRE", 3, DIM)
    y += 3 * FONT_H + 14
    for item in news["wire"]:
        y = cv.text_wrap(MARGIN, y, "- " + item, 3, INK, CONTENT_W, 3 * (FONT_H + 4))
        y += 6
    return y


def draw_footer(cv: Canvas, news: dict, y: int) -> int:
    y += 16
    cv.hline(MARGIN, y, CONTENT_W, RULE, 1)
    y += 18
    cv.text(MARGIN, y, news["colophon"], 2, RULE)
    # Dateline and issue number set flush right on the same baseline, so the
    # front page always states which edition of the day this poster is.
    right = "%s - NO. %s" % (news["dateline"], news["issue"])
    cv.text(W - MARGIN - text_width(right, 2), y, right, 2, DIM)
    return y


def render(news: dict) -> Canvas:
    """Draw on a tall canvas, then crop to the last painted row.

    Height is computed, not guessed: the tall buffer guarantees no story is
    ever cut, and the trailing paper rows are trimmed off afterwards.
    """
    tall = Canvas(W, H, PAPER)
    y = draw_masthead(tall, news)
    y = draw_lede(tall, news, y)
    y = draw_bands(tall, news, y)
    y = draw_wire(tall, news, y)
    y = draw_footer(tall, news, y)

    bottom = min(max(y + MARGIN, 400), H)
    if y + MARGIN > H:
        raise SystemExit(
            "content needs %d px, canvas holds %d - shorten a summary" % (y + MARGIN, H)
        )

    out = Canvas(W, bottom, PAPER)
    stride = W * 4
    out.px = tall.px[: bottom * stride]
    out.h = bottom
    return out


def print_stats(news: dict) -> None:
    """Report the fixture and the geometry it renders to, without writing a file."""
    stories = news["stories"]
    cv = render(news)
    print("stories: %d" % len(stories))
    print("total weight: %d" % sum(s["weight"] for s in stories))
    print("canvas: %dx%d" % (cv.w, cv.h))


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    with open(NEWS_PATH, "r", encoding="utf-8") as fh:
        news = json.load(fh)

    if "--stats" in argv:
        print_stats(news)
        return 0

    out_path = os.path.join(OUT_DIR, OUT_NAME)
    render(news).to_png(out_path)

    if "--check" in argv:
        with open(out_path, "rb") as fh:
            first = fh.read()
        render(news).to_png(out_path)
        with open(out_path, "rb") as fh:
            second = fh.read()
        if first != second:
            print("FAIL: non-deterministic output", file=sys.stderr)
            return 1
        print("OK deterministic, %d bytes" % len(first))
        return 0

    print("wrote %s" % out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
