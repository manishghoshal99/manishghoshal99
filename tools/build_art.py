#!/usr/bin/env python3
"""Draw the static pixel art for the profile README into assets/art/.

    python tools/build_art.py        (needs Pillow, only to read the sprites)

The Bytekin creatures come from MG Quest, Manish Ghoshal's commissioned art
(all rights reserved, see ASSETS.md). Each sprite is flattened onto the colour
it sits on, reduced to a small palette and written as vector pixels, so the
SVGs stay crisp and need no embedded images. The live pond pieces are drawn
by tools/pond.py instead.
"""

from __future__ import annotations

import pathlib

from PIL import Image

import pix
from pix import (BEVEL_HI, BEVEL_LO, CREAM, DIM, GOLD, INK, MUTED, TEAL, TITLEBAR,
                 WINDOW, Canvas, rect, text)

ROOT = pathlib.Path(__file__).resolve().parent.parent
SPRITES = ROOT / "tools" / "artsrc" / "bytekin"
OUT = ROOT / "assets" / "art"

# Category colours from MG Quest's design tokens (--mg-cat-*).
SIGNAL, VECTOR, PIPELINE, LOGIC = "#b05a4a", "#4a3fa8", "#7a4f8c", "#557a2f"
REDUCED = "@media (prefers-reduced-motion:reduce){.bob,.hop,.tw,.sp{animation:none!important}.cv{display:none}}"
BOB = ".bob{animation:bob 1.6s step-end infinite}@keyframes bob{0%{transform:translateY(0)}50%{transform:translateY(-4px)}}"


# ---- sprites ------------------------------------------------------------

def sprite(name: str, bg: str, colors: int = 28) -> tuple[list[tuple[int, int, int, str]], tuple]:
    """Frame 0 of a Bytekin strip as runs of (x, y, length, colour), plus its bbox."""
    strip = Image.open(SPRITES / f"{name}.png").convert("RGBA")
    frame = strip.crop((0, 0, 32, 32))
    alpha = frame.getchannel("A").point(lambda a: 255 if a >= 110 else 0)
    flat = Image.new("RGBA", frame.size, bg)
    flat.alpha_composite(frame)
    flat = flat.convert("RGB").quantize(colors, method=Image.Quantize.MEDIANCUT).convert("RGB")
    px, mask = flat.load(), alpha.load()
    runs = []
    for y in range(32):
        x = 0
        while x < 32:
            if not mask[x, y]:
                x += 1
                continue
            color = px[x, y]
            n = 1
            while x + n < 32 and mask[x + n, y] and px[x + n, y] == color:
                n += 1
            runs.append((x, y, n, "#%02x%02x%02x" % color))
            x += n
    return runs, alpha.getbbox()


def draw_sprite(bucket, runs, x: int, y: int, s: int) -> None:
    for rx, ry, n, color in runs:
        rect(bucket, color, x + rx * s, y + ry * s, n * s, s)


def notched(bucket, x: int, y: int, w: int, h: int, color: str, n: int = 4) -> None:
    """A panel with pixel-cut corners."""
    rect(bucket, color, x + n, y, w - 2 * n, h)
    rect(bucket, color, x, y + n, w, h - 2 * n)


def centred(font: str, s: str, scale: int, cx: int) -> int:
    return cx - pix.measure(font, s) * scale // 2


def fits(font: str, s: str, scale: int, max_px: int) -> str:
    width = pix.measure(font, s) * scale
    assert width <= max_px, f"{s!r} is {width}px, {max_px}px available"
    return s


def write(name: str, svg: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(svg, encoding="utf-8")
    print(f"assets/art/{name}  {len(svg.encode()) / 1024:.1f} KB")


# ---- hero: a terminal that types ------------------------------------------

LINES = (
    ("cmd", "whoami"),
    ("out", "a data scientist and AI engineer in Melbourne"),
    ("cmd", "cat focus.txt"),
    ("out", "health signals, NLP, and evaluation that holds up"),
    ("cmd", "./status --now"),
    ("out", "Master of Data Science at UniMelb, open to internships"),
    ("cmd", "./koi"),
    ("hot", "a koi lives just below this terminal. go feed it."),
    ("end", ""),
)
CYCLE = 16.0
PROMPT = "~$ "


def pct(t: float) -> str:
    return f"{100 * t / CYCLE:.3f}%"


def keyframes(name: str, prop: str, steps: list[tuple[float, str]], reset: str) -> str:
    frames = [f"0%{{{prop}:{reset}}}"] + [f"{pct(t)}{{{prop}:{v}}}" for t, v in steps]
    frames += [f"{pct(CYCLE - 0.4)}{{{prop}:{reset}}}"]
    return f"@keyframes {name}{{{''.join(frames)}}}"


def typing(x0: int, y0: int, pitch: int, body: tuple[int, int, int, int]) -> tuple[str, str]:
    """Covers that slide off each line in turn, with a block cursor. Returns (svg, css)."""
    bx, by, bw, bh = body
    t, svg, css = 0.5, [], []
    prompt_px = pix.measure("operator", PROMPT) * 2
    for i, (kind, s) in enumerate(LINES):
        y = y0 + i * pitch
        moves, cursor = [], []
        if kind == "cmd":
            moves.append((t, prompt_px))
            cursor.append((t, "1"))
            t += 0.35
            for k in range(1, len(s) + 1):
                moves.append((t, prompt_px + pix.measure("operator", s[:k]) * 2 + 2))
                t += 0.07
            t += 0.3
            cursor.append((t, "0"))
        elif kind == "end":
            moves.append((t, prompt_px))
            on = True
            while t < CYCLE - 0.6:
                cursor.append((t, "1" if on else "0"))
                on = not on
                t += 0.5
        else:
            moves.append((t, bw))
            t += 0.45
        css.append(keyframes(f"k{i}", "transform", [(a, f"translateX({b}px)") for a, b in moves], "translateX(0)"))
        css.append(f".k{i}{{animation-name:k{i}}}")
        caret = ""
        if cursor:
            css.append(keyframes(f"u{i}", "opacity", cursor, "0"))
            css.append(f".u{i}{{opacity:0;animation:u{i} {CYCLE}s step-end infinite}}")
            caret = f'<rect class="u{i}" x="{x0}" y="{y - 2}" width="12" height="22" fill="{GOLD}"/>'
        svg.append(f'<g class="cv k{i}"><rect x="{x0 - 2}" y="{y - 4}" width="{bw}" height="28" '
                   f'fill="{WINDOW}"/>{caret}</g>')
    css.insert(0, f".cv{{animation-duration:{CYCLE}s;animation-timing-function:step-end;animation-iteration-count:infinite}}")
    clip = f'<clipPath id="tb"><rect x="{bx}" y="{by}" width="{bw}" height="{bh}"/></clipPath>'
    return f'<defs>{clip}</defs><g clip-path="url(#tb)">{"".join(svg)}</g>', "".join(css)


def star(bucket, x: int, y: int, color: str, s: int = 4) -> None:
    rect(bucket, color, x + s, y, s, 3 * s)
    rect(bucket, color, x, y + s, 3 * s, s)


def hero() -> None:
    W, H = 840, 456
    c = Canvas(W, H)
    desk = c.layer()
    notched(desk, 0, 0, W, H, INK, 8)
    for cls, stars in (("tw tw1", ((616, 24, GOLD), (36, 88, TEAL))),
                       ("tw tw2", ((648, 76, CREAM), (796, 22, GOLD))),
                       ("tw tw3", ((560, 92, TEAL), (812, 84, CREAM)))):
        layer = c.layer(cls)
        for x, y, color in stars:
            star(layer, x, y, color)
    title = c.layer()
    text(title, "press", "MANISH GHOSHAL", 32, 40, 5, CREAM)

    chrome = c.layer()
    body = pix.window(chrome, 24, 108, 792, 324, "terminal - manish@melbourne")
    bx, by, bw, bh = body
    words = c.layer()
    x0, y0, pitch = bx + 20, by + 22, 30
    for i, (kind, s) in enumerate(LINES):
        y = y0 + i * pitch
        if kind in ("cmd", "end"):
            w = text(words, "operator", PROMPT, x0, y, 2, GOLD)
            text(words, "operator", s, x0 + w, y, 2, CREAM)
        else:
            text(words, "operator", s, x0, y, 2, TEAL if kind == "hot" else MUTED)

    runs, (l, t, r, b) = sprite("parsek", INK)
    s = 3
    draw_sprite(c.layer("bob"), runs, 700, 108 + 10 - b * s, s)

    covers, type_css = typing(x0, y0, pitch, body)
    css = (BOB + type_css
           + ".tw{animation:tw 2.8s step-end infinite}.tw2{animation-delay:-.9s}.tw3{animation-delay:-1.7s}"
           "@keyframes tw{0%{opacity:1}50%{opacity:.2}}" + REDUCED)
    alt = ("Manish Ghoshal. A terminal types: a data scientist and AI engineer in Melbourne; "
           "health signals, NLP, and evaluation that holds up; Master of Data Science at UniMelb, "
           "open to internships; a koi lives just below this terminal.")
    write("hero.svg", pix.svg(c, alt, css, covers))


# ---- dock: links as desktop icons --------------------------------------------

DOCK = (("portfolio", "wayfox", "ManishOS"), ("linkedin", "netcat", "LinkedIn"),
        ("medium", "notequill", "Medium"), ("email", "servowl", "Email"))


def dock() -> None:
    W, H = 204, 156
    for i, (slug, kin, label) in enumerate(DOCK):
        c = Canvas(W, H)
        bg = c.layer()
        notched(bg, 0, 0, W, H, INK, 8)
        for k, half in enumerate((12, 18, 20)):
            rect(bg, TITLEBAR, W // 2 - half * 2, 104 + k * 4, half * 4, 4)
        runs, (l, t, r, b) = sprite(kin, INK)
        s = 3
        draw_sprite(c.layer(f"bob d{i}"), runs, W // 2 - (l + r) * s // 2, 112 - b * s, s)
        ink = c.layer()
        text(ink, "operator", label, centred("operator", label, 2, W // 2), 130, 2, CREAM)
        css = BOB + "".join(f".d{k}{{animation-delay:-{k * 0.4:.1f}s}}" for k in range(4)) + REDUCED
        write(f"dock-{slug}.svg", pix.svg(c, label, css))


# ---- party: one card per project ------------------------------------------------

CARDS = (
    ("wardsignal", "WARDSIGNAL", "statolotl", "Statolotl", SIGNAL, "FastAPI, LightGBM",
     "A synthetic-data prototype of four-hour ED forecasts with honest intervals.",
     "-37.5%", "alerts per shift"),
    ("nebula", "NEBULA", "glimmoth", "Glimmoth", VECTOR, "PyTorch, Optuna",
     "Gas-sensor classifiers that survive sensor ageing, plus a live drift dashboard.",
     "79.9%", "vs 47% under drift"),
    ("agrilens", "AGRILENS.AI", "verdeer", "Verdeer", LOGIC, "TensorFlow, FastAPI",
     "Diagnoses crop disease from one photo and flags possible local outbreaks.",
     "98.8%", "on 35,144 images"),
    ("redmane", "REDMANE", "cacheoon", "Cacheoon", PIPELINE, "Python CLI, RO-Crate",
     "Scans research datasets into RO-Crate metadata and an interactive HTML report.",
     "1 CLI", "from 3 scanners"),
)


def card(slug, name, kin, kin_name, tint, stack, desc, stat, stat_label) -> None:
    W, H = 416, 294
    c = Canvas(W, H)
    chrome, ink = c.layer(), c.layer()
    bx, by, bw, bh = pix.window(chrome, 0, 0, W - 4, H - 4, f"{slug}.sav")
    text(ink, "operator", "> open", bx + bw - 12 - pix.measure("operator", "> open") * 2, 14, 2, TEAL)
    notched(chrome, bx + 16, by + 16, 88, 88, tint, 4)
    runs, (l, t, r, b) = sprite(kin, tint)
    draw_sprite(c.layer("bob"), runs, bx + 60 - (l + r), by + 96 - b * 2, 2)
    tx = bx + 120
    room = bx + bw - 12 - tx
    text(ink, "press", fits("press", name, 2, room), tx, by + 22, 2, CREAM)
    text(ink, "operator", fits("operator", f"with {kin_name}", 2, room), tx, by + 50, 2, MUTED)
    text(ink, "operator", fits("operator", stack, 2, room), tx, by + 76, 2, DIM)
    lines = pix.wrap("operator", desc, bw - 32, 2)
    assert len(lines) <= 3, f"{slug}: description needs {len(lines)} lines"
    for k, line in enumerate(lines):
        text(ink, "operator", line, bx + 16, by + 122 + k * 26, 2, CREAM)
    w = text(ink, "press", stat, bx + 16, by + 212, 3, GOLD)
    fits("operator", stat_label, 2, bw - 44 - w)
    text(ink, "operator", stat_label, bx + 16 + w + 12, by + 214, 2, MUTED)
    alt = f"{name.title()}: {desc} {stat} {stat_label}. Card art: {kin_name}."
    write(f"card-{slug}.svg", pix.svg(c, alt, BOB + REDUCED))


# ---- trophies -----------------------------------------------------------------

CUP = ("..yyyyyyyyyy..", "yyYhYYYYYYYoyy", "y.YhYYYYYYYo.y", "y.YhYYYYYYYo.y",
       ".yYYYYYYYYYoy.", "...YYYYYYYo...", "....YYYYYo....", ".....oYYo.....",
       "......YY......", "......YY......", "....oYYYYo....", "...BBBBBBBB...", "...BBBBBBBB...")
CUP_COLORS = {"y": "#a8834f", "Y": "#e0b45a", "h": "#fff0c0", "o": "#9a6f2e", "B": "#5d4630"}
TROPHIES = (
    ("11TH PLACE", "Algothon 2026, Susquehanna (SIG) algorithmic trading"),
    ("235TH OF 4,018", "IMC Prosperity 2026, an algorithmic trading challenge"),
    ("TOP 15 OF 1,500+", "Amazon ML Challenge 2023"),
)


def trophies() -> None:
    W, H = 840, 292
    c = Canvas(W, H)
    chrome, ink, sparkle = c.layer(), c.layer(), c.layer("sp")
    bx, by, bw, bh = pix.window(chrome, 0, 0, W - 4, H - 4, "achievements.log")
    tag = f"{len(TROPHIES)}/{len(TROPHIES)} unlocked"
    text(ink, "operator", tag, bx + bw - 12 - pix.measure("operator", tag) * 2, 14, 2, GOLD)
    for i, (title, line) in enumerate(TROPHIES):
        y = by + 24 + i * 76
        notched(chrome, bx + 16, y - 6, bw - 32, 64, TITLEBAR, 4)
        for r, row in enumerate(CUP):
            for col, ch in enumerate(row):
                if ch != ".":
                    rect(ink, CUP_COLORS[ch], bx + 32 + col * 3, y + 6 + r * 3, 3, 3)
        star(sparkle, bx + 30 + (i * 13) % 30, y - 2, CREAM, 2)
        text(ink, "press", title, bx + 96, y + 6, 2, CREAM)
        text(ink, "operator", fits("operator", line, 2, bw - 112), bx + 96, y + 30, 2, MUTED)
    css = ".sp{animation:sp 2.2s step-end infinite}@keyframes sp{0%{opacity:1}30%{opacity:0}}" + REDUCED
    write("trophies.svg", pix.svg(c, "Achievements: " + "; ".join(f"{a}, {b}" for a, b in TROPHIES), css))


# ---- buttons ------------------------------------------------------------------

def button(slug: str, label: str, base: str, hi: str, lo: str, icon) -> None:
    W, H = 416, 80
    c = Canvas(W, H)
    bg, ink, moving = c.layer(), c.layer(), c.layer("bob")
    notched(bg, 0, 4, W, H - 4, lo, 8)
    notched(bg, 0, 0, W, H - 8, base, 8)
    rect(bg, hi, 8, 4, W - 16, 4)
    width = pix.measure("press", label) * 3 + 44
    x = (W - width) // 2
    icon(moving, x, 26)
    text(ink, "press", label, x + 44, 26, 3, INK)
    write(f"button-{slug}.svg", pix.svg(c, label.title(), BOB + REDUCED))


def pellets_icon(bucket, x: int, y: int) -> None:
    for dx, dy in ((0, 8), (12, 0), (16, 12)):
        for r, row in enumerate((".oo.", "oOOo", "OOOO", ".OO.")):
            for col, ch in enumerate(row):
                if ch != ".":
                    rect(bucket, "#5d4630" if ch == "o" else INK, x + dx + col * 3, y + dy + r * 3, 3, 3)


def wave_icon(bucket, x: int, y: int) -> None:
    for r, row in enumerate((".ww...ww..", "w..w.w..w.", "....w....w")):
        for col, ch in enumerate(row):
            if ch == "w":
                rect(bucket, INK, x + col * 3, y + 6 + r * 3, 3, 3)


# ---- footer: the whole party says thanks -----------------------------------------

PARTY = ("nimbusk", "inferra", "datlas", "servowl", "parsek", "geckode", "promptail", "cacheoon", "statolotl")


def footer() -> None:
    W, H = 840, 200
    c = Canvas(W, H)
    bg = c.layer()
    notched(bg, 0, 0, W, H, INK, 8)
    rect(bg, TITLEBAR, 24, 168, W - 48, 8)
    ink = c.layer()
    line = "THANKS FOR VISITING"
    text(ink, "press", line, centred("press", line, 3, W // 2), 28, 3, CREAM)
    sub = "the whole party lives in MG Quest, on my portfolio"
    text(ink, "operator", sub, centred("operator", sub, 2, W // 2), 62, 2, MUTED)
    gap = (W - 48) // len(PARTY)
    for i, kin in enumerate(PARTY):
        runs, (l, t, r, b) = sprite(kin, INK)
        draw_sprite(c.layer(f"hop h{i}"), runs, 24 + i * gap + gap // 2 - (l + r), 170 - b * 2, 2)
    css = (".hop{animation:hop 2.4s step-end infinite}"
           "@keyframes hop{0%{transform:translateY(0)}8%{transform:translateY(-10px)}16%{transform:translateY(0)}}"
           + "".join(f".h{i}{{animation-delay:{i * 0.12:.2f}s}}" for i in range(len(PARTY))) + REDUCED)
    write("footer.svg", pix.svg(c, "Thanks for visiting. Nine Bytekin from MG Quest hop in a wave.", css))


def main() -> None:
    hero()
    dock()
    for spec in CARDS:
        card(*spec)
    trophies()
    button("feed", "FEED THE KOI", GOLD, "#e2bf8a", "#8d6a3e", pellets_icon)
    button("wave", "WAVE HELLO", TEAL, "#7fdccf", "#23786c", wave_icon)
    footer()


if __name__ == "__main__":
    main()
