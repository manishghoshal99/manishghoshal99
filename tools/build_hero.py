#!/usr/bin/env python3
"""Build assets/hero.svg, the banner at the top of the profile README.

The text is set in Jost (SIL Open Font License 1.1,
https://github.com/indestructible-type/Jost) and outlined to paths, because
GitHub's image proxy forbids fonts inside SVGs. The pixel ECG trace along the
bottom is generated here as well, so the whole banner is reproducible.

    python tools/build_hero.py --font "Jost[wght].ttf" --out assets/hero.svg

Needs fonttools and uharfbuzz.
"""

from __future__ import annotations

import argparse
import io
from dataclasses import dataclass

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

WIDTH, HEIGHT = 880, 330
RADIUS = 18

INK = "#05060f"       # the ManishOS ground
BAND = "#0b0d18"      # one tone step up, under the trace
CREAM = "#f2ecdf"     # the name
MUTED = "#b4ac9b"     # the two supporting lines
GOLD = "#c59b64"      # the trace (and the koi's body colour)
DIM = "#5b4b35"       # the stretch of noise the trace flags

PX = 4                # one trace pixel, in SVG units
BASE_Y = 284          # bottom edge of the trace baseline row
BEAT_COLS = 56        # columns per heartbeat
BEATS_PER_CYCLE = 4   # the sweep repeats every four beats
SWEEP_SECONDS = 7

NAME = "Manish Ghoshal"
LINES = (
    "Data scientist and AI engineer in Melbourne.",
    "Health signals, NLP and evaluation that holds up.",
)


@dataclass(frozen=True)
class Glyph:
    gid: int
    x: float
    y: float


def static_instance(variable_font: str, weight: int) -> bytes:
    """Instance the variable font at one weight and return it as TTF bytes."""
    font = TTFont(variable_font)
    inst = instancer.instantiateVariableFont(font, {"wght": weight})
    buf = io.BytesIO()
    inst.save(buf)
    return buf.getvalue()


def shape(ttf: bytes, text: str, size: float, tracking_em: float) -> tuple[list[Glyph], float]:
    """Lay out text with HarfBuzz (kerning on) and return glyph positions in SVG units."""
    face = hb.Face(ttf)
    font = hb.Font(face)
    scale = size / face.upem
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(font, buf, {"kern": True, "liga": True})
    glyphs: list[Glyph] = []
    x = 0.0
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        glyphs.append(Glyph(info.codepoint, x + pos.x_offset * scale, pos.y_offset * scale))
        x += pos.x_advance * scale + tracking_em * size
    return glyphs, x - tracking_em * size


def outline(ttf: bytes, glyphs: list[Glyph], size: float, x0: float, y0: float) -> str:
    """Turn positioned glyphs into one SVG path, y flipped into screen space."""
    font = TTFont(io.BytesIO(ttf))
    glyph_set = font.getGlyphSet()
    order = font.getGlyphOrder()
    s = size / font["head"].unitsPerEm
    parts = []
    for g in glyphs:
        pen = SVGPathPen(glyph_set, ntos=lambda v: f"{v:.2f}".rstrip("0").rstrip("."))
        glyph_set[order[g.gid]].draw(TransformPen(pen, (s, 0, 0, -s, x0 + g.x, y0 - g.y)))
        commands = pen.getCommands()
        if commands:
            parts.append(commands)
    return " ".join(parts)


def beat() -> list[int]:
    """One heartbeat in trace pixels above (+) or below (-) the baseline."""
    v = [0] * BEAT_COLS
    v[8:16] = [0, 1, 1, 2, 2, 1, 1, 0]          # P wave
    v[20:26] = [-1, 7, 12, 3, -3, -1]            # QRS complex
    v[30:39] = [1, 2, 3, 4, 4, 4, 3, 2, 1]       # T wave
    return v


NOISE = [1, -1, 2, -2, 1, 0, -1, 2, -1, 1, -2, 1, 0, -1, 1, -1, 2, -2, 1, -1, 0, 1, -1, 1]


def trace() -> tuple[list[int], set[int]]:
    """Two full cycles of beats; the third beat of each cycle carries a noise burst."""
    values: list[int] = []
    for _ in range(2 * BEATS_PER_CYCLE):
        values.extend(beat())
    noisy: set[int] = set()
    for cycle in range(2):
        start = (cycle * BEATS_PER_CYCLE + 2) * BEAT_COLS + 40
        for k, n in enumerate(NOISE):
            values[start + k] += n
            noisy.add(start + k)
    return values, noisy


def cells(values: list[int]) -> list[tuple[int, int]]:
    """Fill every pixel between consecutive samples so the line stays connected."""
    out = []
    prev = values[0]
    for col, v in enumerate(values):
        lo, hi = sorted((prev, v))
        out.extend((col, row) for row in range(lo, hi + 1))
        prev = v
    return out


def pixel_path(pixels: list[tuple[int, int]]) -> str:
    return "".join(f"M{c * PX} {BASE_Y - (r + 1) * PX}h{PX}v{PX}h-{PX}z" for c, r in pixels)


def build(variable_font: str) -> str:
    semibold = static_instance(variable_font, 600)
    regular = static_instance(variable_font, 400)

    name_glyphs, name_width = shape(semibold, NAME, 76, -0.02)
    assert name_width < 700, f"name too wide: {name_width:.0f}"
    name_path = outline(semibold, name_glyphs, 76, 64, 124)

    line_paths = []
    for i, line in enumerate(LINES):
        glyphs, width = shape(regular, line, 24, 0.0)
        assert width < 760, f"line too wide: {width:.0f}"
        line_paths.append(outline(regular, glyphs, 24, 64, 180 + i * 34))

    values, noisy = trace()
    clean = [p for p in cells(values) if p[0] not in noisy]
    noise = [p for p in cells(values) if p[0] in noisy]
    cycle_px = BEATS_PER_CYCLE * BEAT_COLS * PX

    alt = f"{NAME}. {LINES[0]} {LINES[1]}"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="t">
<title id="t">{alt}</title>
<style>
.sweep {{ animation: sweep {SWEEP_SECONDS}s linear infinite; }}
@keyframes sweep {{ from {{ transform: translateX(0); }} to {{ transform: translateX(-{cycle_px}px); }} }}
@media (prefers-reduced-motion: reduce) {{ .sweep {{ animation: none; }} }}
</style>
<defs><clipPath id="frame"><rect width="{WIDTH}" height="{HEIGHT}" rx="{RADIUS}"/></clipPath></defs>
<g clip-path="url(#frame)">
<rect width="{WIDTH}" height="{HEIGHT}" fill="{INK}"/>
<rect y="226" width="{WIDTH}" height="{HEIGHT - 226}" fill="{BAND}"/>
<g class="sweep" shape-rendering="crispEdges">
<path fill="{GOLD}" d="{pixel_path(clean)}"/>
<path fill="{DIM}" d="{pixel_path(noise)}"/>
</g>
<path fill="{CREAM}" d="{name_path}"/>
<path fill="{MUTED}" d="{line_paths[0]}"/>
<path fill="{MUTED}" d="{line_paths[1]}"/>
</g>
</svg>
"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--font", required=True, help="path to Jost[wght].ttf")
    ap.add_argument("--out", default="assets/hero.svg")
    args = ap.parse_args()
    svg = build(args.font)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote {args.out} ({len(svg.encode()) / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
