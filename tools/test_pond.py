#!/usr/bin/env python3
"""Checks for the pond's scorekeeping. Run: python3 tools/test_pond.py"""

import pond

DAY1, DAY2 = "2026-11-01", "2026-11-02"


def issue(number, title="koi: feed", login="octocat", is_bot=False):
    return {"number": number, "title": title, "login": login, "is_bot": is_bot}


def test_feed_wave_and_cooldown():
    s, r = pond.process(pond.empty_state(DAY1), [
        issue(1), issue(2, "Koi:  WAVE"), issue(3), issue(4, login="hubot"),
    ], DAY1)
    assert (s["feeds"], s["waves"], s["today"]["feeds"], s["max_issue"]) == (2, 1, 2, 4)
    assert r[2]["body"] == pond.COOLDOWN["feed"]          # second feed by octocat today
    assert [v["login"] for v in s["recent"]] == ["hubot", "octocat"]
    assert all(x["reason"] == "completed" for x in r)


def test_counted_issues_are_only_closed_again():
    s, _ = pond.process(pond.empty_state(DAY1), [issue(5)], DAY1)
    s2, r = pond.process(s, [issue(5), issue(6, login="mona")], DAY1)
    assert s2["feeds"] == 2 and r[0]["body"] is None      # #5 not counted twice


def test_hostile_input_is_rejected():
    bad = [issue(7, "koi: feed; rm -rf /"), issue(8, login="<svg onload=x>"),
           issue(9, login="dependabot", is_bot=True), issue(10, "koi: dance")]
    s, r = pond.process(pond.empty_state(DAY1), bad, DAY1)
    assert s["feeds"] == s["waves"] == 0 and s["recent"] == []
    assert all(x["reason"] == "not planned" for x in r)


def test_new_day_resets_cooldown_and_mood():
    s, _ = pond.process(pond.empty_state(DAY1), [issue(1)], DAY1)
    assert pond.mood(pond.pellets_today(s, DAY1))[0] == "CONTENT"
    assert pond.mood(pond.pellets_today(s, DAY2))[0] == "HUNGRY"
    s2, r = pond.process(s, [issue(2)], DAY2)
    assert s2["feeds"] == 2 and r[0]["body"] in pond.FEED_LINES


def test_board_renders_and_hides_titles():
    s, _ = pond.process(pond.empty_state(DAY1), [issue(1, login="a-very-long-login-name-x" * 1)], DAY1)
    svg = pond.render_board(s, DAY1)
    assert svg.startswith("<svg") and "koi: feed" not in svg and "1 pellet and 0 waves" in svg


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
