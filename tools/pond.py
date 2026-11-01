#!/usr/bin/env python3
"""The koi pond: visitors feed the koi by opening an issue, this keeps score.

Run by .github/workflows/pond.yml, standard library plus the gh CLI only.

    pond.py run --repo OWNER/NAME --replies FILE [--scene]
        Count every open `koi: feed` / `koi: wave` issue, update pond/state.json,
        redraw assets/pond-board.svg (and assets/pond.svg with --scene), and
        write the replies to FILE. Nothing is posted yet.
    pond.py reply --repo OWNER/NAME --replies FILE
        After the commit is pushed: comment on and close each issue.

Every run catches up on all open koi issues, so a run that GitHub cancels while
queued loses nothing. Issue numbers at or below state["max_issue"] were counted
already and are only closed. Issue titles and bodies are never echoed; the only
visitor text that reaches the SVG is a login checked against LOGIN.
"""

from __future__ import annotations

import argparse
import base64
import copy
import datetime as dt
import json
import pathlib
import re
import subprocess
import sys

import pix
from pix import CREAM, DIM, GOLD, MUTED, ORANGE, TEAL, Canvas

ROOT = pathlib.Path(__file__).resolve().parent.parent
STATE = ROOT / "pond" / "state.json"
BOARD = ROOT / "assets" / "pond-board.svg"
SCENE = ROOT / "assets" / "pond.svg"
KOI_GIF = ROOT / "koi" / "koi.gif"

LOGIN = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})")
ACTIONS = {"koi:feed": "feed", "koi:wave": "wave"}
RECENT = 6
PELLET = "#e4a672"         # git-koi's own pellet colours
PELLET_DARK = "#b86f50"

FEED_LINES = (
    "Plop. The koi found your pellet before it touched the bottom.",
    "The koi circles twice, and the pellet is gone. Rude, but grateful.",
    "A gold flash and a ripple. Your pellet has been accepted.",
    "The koi does a small, dignified flip. In koi, that means thank you.",
)
WAVE_LINES = (
    "The koi flicks its tail at you. That is a wave, in koi.",
    "A string of bubbles rises in your direction. Hello received.",
    "The koi stops mid-swim and looks right at you. Hi back.",
)
COOLDOWN = {
    "feed": "The koi already had a pellet from you today (UTC), so it is saving room. "
            "Come back tomorrow and it will be hungry again.",
    "wave": "The koi already waved back at you today (UTC). It is shy about doing it twice. "
            "Come back tomorrow.",
}
UNKNOWN = ("The koi only understands two titles: `koi: feed` and `koi: wave`. "
           "The buttons on the profile fill one in for you.")
MOODS = (  # (fewest pellets today, word, colour, aside)
    (6, "STUFFED", CREAM, "please, no more. maybe one."),
    (3, "HAPPY", TEAL, "doing small loops of joy"),
    (1, "CONTENT", GOLD, "a pellet or two, life is good"),
    (0, "HUNGRY", ORANGE, "it has been waiting all day"),
)


# ---- state --------------------------------------------------------------

def empty_state(today: str) -> dict:
    return {"since": today, "feeds": 0, "waves": 0, "max_issue": 0,
            "today": {"date": today, "feeds": 0, "done": []}, "recent": []}


def load_state(today: str) -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return empty_state(today)


def normalise(title: str) -> str:
    return re.sub(r"\s+", "", title or "").lower()


def process(state: dict, issues: list[dict], today: str) -> tuple[dict, list[dict]]:
    """Apply open koi issues to the state. Pure: returns (new state, replies)."""
    s = copy.deepcopy(state)
    if s["today"]["date"] != today:
        s["today"] = {"date": today, "feeds": 0, "done": []}
    replies: list[dict] = []
    for issue in sorted(issues, key=lambda i: i["number"]):
        number, login = issue["number"], issue["login"]
        if number <= s["max_issue"]:
            replies.append({"number": number, "body": None, "reason": "completed"})
            continue
        s["max_issue"] = number
        action = ACTIONS.get(normalise(issue["title"]))
        if action is None or issue.get("is_bot") or not LOGIN.fullmatch(login or ""):
            replies.append({"number": number, "body": UNKNOWN, "reason": "not planned"})
            continue
        key = f"{login.lower()}:{action}"
        if key in s["today"]["done"]:
            replies.append({"number": number, "body": COOLDOWN[action], "reason": "completed"})
            continue
        s["today"]["done"].append(key)
        if action == "feed":
            s["feeds"] += 1
            s["today"]["feeds"] += 1
            line = FEED_LINES[s["feeds"] % len(FEED_LINES)]
        else:
            s["waves"] += 1
            line = WAVE_LINES[s["waves"] % len(WAVE_LINES)]
        others = [r for r in s["recent"] if r["login"].lower() != login.lower()]
        s["recent"] = ([{"login": login, "action": action, "date": today}] + others)[:RECENT]
        replies.append({"number": number, "body": line, "reason": "completed", "login": login})
    return s, replies


def pellets_today(state: dict, today: str) -> int:
    return state["today"]["feeds"] if state["today"]["date"] == today else 0


def mood(pellets: int) -> tuple[str, str, str]:
    for least, word, color, aside in MOODS:
        if pellets >= least:
            return word, color, aside
    raise AssertionError("unreachable")


def pretty_date(iso: str) -> str:
    d = dt.date.fromisoformat(iso)
    return f"{d.day} {d.strftime('%b')} {d.year}"


# ---- drawing ------------------------------------------------------------

def pellet(bucket, x: int, y: int, s: int) -> None:
    for r, row in enumerate((".oo.", "oOOo", "OOOO", ".OO.")):
        for c, ch in enumerate(row):
            if ch != ".":
                pix.rect(bucket, PELLET if ch == "O" else PELLET_DARK, x + c * s, y + r * s, s, s)


def ripple_mark(bucket, x: int, y: int, s: int) -> None:
    for r, row in enumerate((".tt...tt..", "t..t.t..t.", "....t....t")):
        for c, ch in enumerate(row):
            if ch == "t":
                pix.rect(bucket, TEAL, x + c * s, y + r * s, s, s)


def fit(font: str, s: str, max_px: int, scale: int) -> str:
    if pix.measure(font, s) * scale <= max_px:
        return s
    while s and pix.measure(font, s + "..") * scale > max_px:
        s = s[:-1]
    return s + ".."


def render_board(state: dict, today: str) -> str:
    W, H = 840, 376
    c = Canvas(W, H)
    chrome, ink = c.layer(), c.layer()
    bx, by, bw, bh = pix.window(chrome, 0, 0, W - 4, H - 4, "pond.log")
    tag = "live, updated by visitors"
    pix.text(ink, "operator", tag, bx + bw - 12 - 2 * pix.measure("operator", tag), 14, 2, DIM)

    fed = pellets_today(state, today)
    word, color, aside = mood(fed)
    cols = (bx + 24, bx + 300, bx + 584)
    top = by + 20
    pix.text(ink, "operator", "PELLETS, ALL TIME", cols[0], top, 2, MUTED)
    pix.text(ink, "press", str(state["feeds"]), cols[0], top + 30, 5, GOLD)
    pix.text(ink, "operator", "MOOD TODAY", cols[1], top, 2, MUTED)
    pix.text(ink, "press", word, cols[1], top + 30, 3, color)
    for i in range(6):
        slot = cols[1] + i * 28
        if i < fed:
            pellet(ink, slot, top + 64, 4)
        else:
            pix.rect(ink, DIM, slot + 4, top + 68, 8, 8)
    pix.text(ink, "operator", aside, cols[1], top + 92, 2, DIM)
    pix.text(ink, "operator", "WAVES", cols[2], top, 2, MUTED)
    pix.text(ink, "press", str(state["waves"]), cols[2], top + 30, 5, TEAL)

    row = top + 136
    pix.text(ink, "operator", "RECENT VISITORS", cols[0], row, 2, MUTED)
    if not state["recent"]:
        pix.text(ink, "operator", "nobody yet. the first pellet could be yours.", cols[0], row + 32, 2, CREAM)
    for i, visit in enumerate(state["recent"][:RECENT]):
        x = cols[0] + (i % 2) * 392
        y = row + 32 + (i // 2) * 30
        if visit["action"] == "feed":
            pellet(ink, x, y + 2, 4)
        else:
            ripple_mark(ink, x - 4, y + 4, 3)
        when = "today" if visit["date"] == today else pretty_date(visit["date"])[:-5]
        name = fit("operator", "@" + visit["login"], 340 - 2 * pix.measure("operator", when) - 40, 2)
        width = pix.text(ink, "operator", name, x + 32, y, 2, CREAM)
        pix.text(ink, "operator", when, x + 32 + width + 10, y, 2, DIM)

    note = f"since {pretty_date(state['since'])}. one pellet and one wave per visitor per day."
    pix.text(ink, "operator", note, cols[0], by + bh - 32, 2, DIM)
    plural = lambda n, word: f"{n} {word}{'' if n == 1 else 's'}"
    title = (f"Pond log: {plural(state['feeds'], 'pellet')} and {plural(state['waves'], 'wave')} so far. "
             f"The koi is {word.lower()} today.")
    return pix.svg(c, title)


# Scene sprites: one character per pixel, "." is water.
LILY = ("....HGGGGGGG....", "..HGGGGGGGGGGG..", ".HGGGGGGGGGGGGG.", "GGGGGGGvGGGGGGG.",
        "GGGGGGGGvv......", "GGGGGGGvGGGGGGG.", ".GGGGGGGGGGGGGd.", "..dGGGGGGGGGdd..",
        "....dddddddd....")
FLOWER = ("..p.p..", ".pPpPp.", "pPPyPPp", ".pPPPp.", "..ppp..")
STONE = ("...ssss.....", ".sSShSSss...", "sSShhSSSSs..", "sSSSSSSSSSs.", ".ssssssssss.")
SCENE_COLORS = {"G": "#3f7f4a", "H": "#5a9e5f", "v": "#2e5f37", "d": "#2a5533",
                "p": "#d9768f", "P": "#f4b6c4", "y": "#f6d26b",
                "s": "#232838", "S": "#353b52", "h": "#545d7c"}
WATER, WATER_DEEP, SHIMMER, RING = "#0f3443", "#0a2833", "#1d5868", "#2f7385"


def stamp(bucket, art: tuple[str, ...], x: int, y: int, s: int) -> None:
    for r, row in enumerate(art):
        for col, ch in enumerate(row):
            if ch != ".":
                pix.rect(bucket, SCENE_COLORS[ch], x + col * s, y + r * s, s, s)


def ring(bucket, cx: int, cy: int, radius: int, s: int) -> None:
    """A pixel circle by the midpoint algorithm, flattened to look like water."""
    x, y, err = radius, 0, 1 - radius
    points = set()
    while x >= y:
        for px_, py_ in ((x, y), (y, x), (-y, x), (-x, y), (-x, -y), (-y, -x), (y, -x), (x, -y)):
            points.add((px_, py_ // 2))
        y += 1
        if err < 0:
            err += 2 * y + 1
        else:
            x -= 1
            err += 2 * (y - x) + 1
    for px_, py_ in points:
        pix.rect(bucket, RING, cx + px_ * s, cy + py_ * s, s, s)


def render_scene(koi_gif: bytes) -> str:
    W, H = 840, 456
    c = Canvas(W, H)
    chrome = c.layer()
    bx, by, bw, bh = pix.window(chrome, 0, 0, W - 4, H - 4, "koi_pond.exe")
    hint = "click the water to feed"
    pix.text(chrome, "operator", hint, bx + bw - 12 - 2 * pix.measure("operator", hint), 14, 2, GOLD)
    water = c.layer()
    pix.rect(water, WATER_DEEP, bx, by, bw, bh)
    pix.rect(water, WATER, bx + 8, by + 8, bw - 16, bh - 16)
    shimmer = c.layer("sh")
    for x, y, w in ((60, 90, 24), (150, 300, 16), (700, 120, 20), (610, 360, 28), (240, 400, 12), (760, 260, 16)):
        pix.rect(shimmer, SHIMMER, x, y, w, 4)
    for i, (cx, cy) in enumerate(((150, 210), (690, 330))):
        for j, radius in enumerate((3, 6, 9)):
            ring(c.layer(f"rp r{i}{j}"), cx, cy, radius, 4)
    plants = c.layer()
    stamp(plants, LILY, 48, 96, 5)
    stamp(plants, FLOWER, 88, 104, 4)
    stamp(plants, LILY, 640, 210, 4)
    stamp(plants, LILY, 700, 70, 6)
    stamp(plants, STONE, 24, 360, 6)
    stamp(plants, STONE, 740, 380, 5)
    stamp(plants, FLOWER, 746, 96, 4)
    koi = base64.b64encode(koi_gif).decode("ascii")
    image = (f'<image href="data:image/gif;base64,{koi}" x="{(W - 4 - 384) // 2}" y="{by + (bh - 384) // 2}" '
             f'width="384" height="384" style="image-rendering:pixelated"/>')
    style = (
        ".sh{animation:sh 3s step-end infinite}"
        "@keyframes sh{0%{transform:translateX(0)}50%{transform:translateX(8px)}}"
        ".rp{opacity:0;animation:rp 4s step-end infinite}"
        "@keyframes rp{0%{opacity:0}10%{opacity:.9}35%{opacity:0}}"
        ".r01{animation-delay:.6s}.r02{animation-delay:1.2s}"
        ".r10{animation-delay:2s}.r11{animation-delay:2.6s}.r12{animation-delay:3.2s}"
        "@media (prefers-reduced-motion:reduce){.sh,.rp{animation:none}.rp{opacity:.5}}"
    )
    return pix.svg(c, "My koi swimming in a pixel pond with lily pads. Click to feed it.", style, image)


# ---- GitHub -------------------------------------------------------------

def gh(args: list[str], stdin: str | None = None) -> str:
    done = subprocess.run(["gh", *args], input=stdin, text=True, capture_output=True)
    if done.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:3])} failed: {done.stderr.strip()}")
    return done.stdout


def open_koi_issues(repo: str) -> list[dict]:
    jq = ('.[] | {number, title, login: .user.login, is_bot: (.user.type == "Bot"), '
          'is_pr: (.pull_request != null)}')
    out = gh(["api", "--paginate", f"repos/{repo}/issues?state=open&per_page=100", "--jq", jq])
    items = [json.loads(line) for line in out.splitlines() if line.strip()]
    return [i for i in items if not i["is_pr"] and normalise(i["title"]).startswith("koi:")]


def reply_body(reply: dict, repo: str) -> str | None:
    if not reply["body"] or "login" not in reply:
        return reply["body"]
    owner = repo.split("/")[0]
    return (f"{reply['body']}\n\nYou are on the pond board now as @{reply['login']}. "
            f"GitHub caches images for a few minutes, so the profile catches up shortly: "
            f"https://github.com/{owner}\n\nThanks for visiting.")


def send_replies(repo: str, replies: list[dict]) -> int:
    failures = 0
    for reply in replies:
        number = str(reply["number"])
        try:
            body = reply_body(reply, repo)
            if body:
                gh(["issue", "comment", number, "--repo", repo, "--body-file", "-"], stdin=body)
            gh(["issue", "close", number, "--repo", repo, "--reason", reply["reason"]])
        except RuntimeError as err:
            failures += 1
            print(f"issue #{number}: {err}", file=sys.stderr)
    return failures


# ---- entry point --------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="Run the koi pond.")
    ap.add_argument("mode", choices=("run", "reply"))
    ap.add_argument("--repo", required=True)
    ap.add_argument("--replies", required=True, type=pathlib.Path)
    ap.add_argument("--scene", action="store_true", help="also redraw the pond around koi/koi.gif")
    args = ap.parse_args()

    if args.mode == "reply":
        replies = json.loads(args.replies.read_text()) if args.replies.exists() else []
        failures = send_replies(args.repo, replies)
        print(f"replied to {len(replies) - failures} of {len(replies)} issues")
        return 1 if failures else 0

    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    state, replies = process(load_state(today), open_koi_issues(args.repo), today)
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(state, indent=1) + "\n", encoding="utf-8")
    BOARD.write_text(render_board(state, today), encoding="utf-8")
    if args.scene:
        SCENE.write_text(render_scene(KOI_GIF.read_bytes()), encoding="utf-8")
    args.replies.write_text(json.dumps(replies), encoding="utf-8")
    print(f"processed {len(replies)} koi issues; {state['feeds']} pellets, {state['waves']} waves")
    return 0


if __name__ == "__main__":
    sys.exit(main())
