"""Pixel-art SVG primitives shared by the art builder and the pond Action.

Standard library only. Everything is drawn as rectangles on a pixel grid and
merged into one path per colour, so the SVGs stay crisp at any size and need
no fonts or embedded images.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from glyphs import FONTS

# The ManishOS palette.
INK = "#05060f"
WINDOW = "#0d1020"
TITLEBAR = "#191d33"
BEVEL_HI = "#2b3152"
BEVEL_LO = "#03040a"
CREAM = "#f2ecdf"
MUTED = "#9d98ab"
DIM = "#5d5a70"
GOLD = "#c59b64"
ORANGE = "#eb5939"
TEAL = "#3fb8a8"


@dataclass
class Canvas:
    """Collects pixel rectangles by colour, then writes them as compact paths."""

    width: int
    height: int
    layers: list[tuple[str, dict[str, list[tuple[int, int, int, int]]]]] = field(default_factory=list)

    def layer(self, css_class: str = "") -> dict[str, list[tuple[int, int, int, int]]]:
        bucket: dict[str, list[tuple[int, int, int, int]]] = defaultdict(list)
        self.layers.append((css_class, bucket))
        return bucket


def rect(bucket, color: str, x: int, y: int, w: int, h: int) -> None:
    if w > 0 and h > 0:
        bucket[color].append((x, y, w, h))


def path_d(rects) -> str:
    return "".join(f"M{x} {y}h{w}v{h}h{-w}z" for x, y, w, h in rects)


def paths(bucket) -> str:
    return "".join(
        f'<path fill="{color}" d="{path_d(rs)}"/>' for color, rs in bucket.items() if rs
    )


def svg(canvas: Canvas, title: str, style: str = "", extra: str = "") -> str:
    groups = []
    for css_class, bucket in canvas.layers:
        inner = paths(bucket)
        if not inner:
            continue
        groups.append(f'<g class="{css_class}">{inner}</g>' if css_class else inner)
    style_block = f"<style>{style}</style>" if style else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas.width}" height="{canvas.height}" '
        f'viewBox="0 0 {canvas.width} {canvas.height}" role="img" aria-label="{escape(title)}" '
        f'shape-rendering="crispEdges"><title>{escape(title)}</title>{style_block}'
        + "".join(groups) + extra + "</svg>\n"
    )


def escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


# ---- text -----------------------------------------------------------------

def measure(font: str, text: str) -> int:
    """Width of text in font pixels (the advance of every glyph)."""
    glyphs = FONTS[font]["glyphs"]
    return sum(glyphs.get(ch, glyphs["?"])[0] for ch in text)


def cap_height(font: str) -> int:
    rows = FONTS[font]["glyphs"]["H"][4]
    return len(rows)


def text(bucket, font: str, s: str, x: int, y: int, scale: int, color: str) -> int:
    """Draw s with its cap tops at y. Returns the drawn width in SVG units."""
    f = FONTS[font]
    top_of_caps = f["glyphs"]["H"][2]
    cx = x
    for ch in s:
        advance, xoff, yoff, width, rows = f["glyphs"].get(ch, f["glyphs"]["?"])
        for r, hexrow in enumerate(rows):
            bits = int(hexrow, 16)
            col = 0
            while bits:
                if bits & 1:
                    run = 0
                    while bits & 1:
                        run += 1
                        bits >>= 1
                    rect(bucket, color,
                         cx + (xoff + col) * scale, y + (yoff - top_of_caps + r) * scale,
                         run * scale, scale)
                    col += run
                else:
                    bits >>= 1
                    col += 1
        cx += advance * scale
    return cx - x


def wrap(font: str, s: str, max_px: int, scale: int) -> list[str]:
    """Greedy word wrap so no line is wider than max_px SVG units."""
    lines: list[str] = []
    line = ""
    for word in s.split():
        trial = f"{line} {word}".strip()
        if measure(font, trial) * scale <= max_px or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


# ---- chrome ---------------------------------------------------------------

def window(bucket, x: int, y: int, w: int, h: int, title: str, u: int = 4,
           title_color: str = MUTED) -> tuple[int, int, int, int]:
    """A ManishOS window: bevelled frame, title bar, three buttons.

    Returns the body rectangle (x, y, w, h) inside the frame.
    """
    rect(bucket, BEVEL_LO, x + u, y + u, w, h)                 # drop shadow
    rect(bucket, BEVEL_HI, x, y, w, h)                         # frame
    rect(bucket, TITLEBAR, x + u, y + u, w - 2 * u, 8 * u)     # title bar
    for i, color in enumerate((ORANGE, GOLD, DIM)):
        rect(bucket, color, x + 3 * u + i * 4 * u, y + 3 * u + u // 2, 2 * u, 2 * u)
    text(bucket, "operator", title, x + 16 * u, y + 3 * u + u // 2 - 1, 2, title_color)
    body = (x + u, y + 9 * u, w - 2 * u, h - 10 * u)
    rect(bucket, WINDOW, *body)
    return body
