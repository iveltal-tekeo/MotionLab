"""Fake-GitHub update test, step 2: drive the friend's app (port 8791) in headless Edge through every update path.

    python upd_test.py whatsnew        the restarted window shows "What's new" once, Got it marks it seen
    python upd_test.py button <ver>    (after upd_prepare.py <ver>) Check now -> sidebar button -> dialog -> Update now
                                       -> restart -> What's new <ver>
    python upd_test.py knowledge       (after upd_prepare.py x --knowledge) button "New from friends" -> Get it now
    python upd_test.py settings        the update choice is saved
Run with the lab's venv (.venv\\Scripts\\python tools\\dev\\upd_test.py ...); screenshots go to .app\\dev\\shots\\.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cdp import Browser  # noqa: E402

URL = "http://127.0.0.1:8791/"
SHOTS = Path(__file__).resolve().parents[2] / ".app" / "dev" / "shots"
SHOTS.mkdir(parents=True, exist_ok=True)
FRIEND = Path(__file__).resolve().parents[2] / ".app" / "dev" / "upd" / "friendA"
MODAL = "!document.querySelector('#modal').hidden"


def ok(cond, what):
    print(("PASS " if cond else "FAIL ") + what)
    if not cond:
        global FAILED
        FAILED = True


FAILED = False


def last():
    try:
        return json.loads((FRIEND / ".app" / "update_last.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def main():
    what = sys.argv[1]
    b = Browser(9341)
    try:
        b.goto(URL, 2.5)
        if what == "whatsnew":
            ok(b.wait(MODAL, 15), "What's new dialog opens by itself")
            t = b.text("#modal .mbody") or ""
            ok("Updated to MotionLab 0.3.0" in t, "title: Updated to MotionLab 0.3.0")
            ok("from 0.2.5" in t, "says it came from 0.2.5")
            ok("Test release 0.3.0" in t and "Update button" in t, "shows the 0.3.0 changelog section")
            ok("0.2.5 - 2026-10-07" not in t, "does not repeat older sections")
            b.shot(str(SHOTS / "1_whatsnew.png"))
            b.click("#modal [data-ok]")
            time.sleep(1)
            ok(last().get("seen") is True, "Got it -> seen in update_last.json")
            b.goto(URL, 3)
            ok(not b.eval(MODAL), "not shown again after a reload")
        elif what == "button":
            ver = sys.argv[2]
            ok(b.wait("document.querySelector('#side-update') && document.querySelector('#side-update').hidden", 5),
               "no Update button before the check")
            b.eval("fetch('/api/update/check', {method: 'POST', headers: {'Content-Type': 'application/json', "
                   "'X-ML-Token': document.querySelector('meta[name=ml-token]').content}, body: '{}'})"
                   ".then(r => r.json())")
            ok(b.wait("!document.querySelector('#side-update').hidden", 15), "Update button appears after a check")
            t = b.text("#side-update") or ""
            ok("Update available" in t and ver in t, f"button says Update available / MotionLab {ver}: {t!r}")
            b.shot(str(SHOTS / f"2_button_{ver}.png"))
            b.click("#side-update")
            ok(b.wait(MODAL, 10), "dialog opens on click")
            t = b.text("#modal .mbody") or ""
            ok(f"MotionLab {ver} is available" in t, "dialog title")
            ok(f"Test release {ver}" in t, "dialog shows the new section")
            ok("Test release 0.3.0" not in t, "dialog leaves out what this copy already has")
            ok("Update now" in t and "Later" in t, "Update now / Later")
            b.shot(str(SHOTS / f"3_dialog_{ver}.png"))
            b.click("#modal [data-go]")
            ok(b.wait("document.querySelector('#overlay') && !document.querySelector('#overlay').hidden", 10),
               "Updating... overlay")
            time.sleep(4)
            ok(b.wait(MODAL, 60), "after the restart: What's new opens")
            t = b.text("#modal .mbody") or ""
            ok(f"Updated to MotionLab {ver}" in t and f"Test release {ver}" in t, "What's new for the new version")
            b.shot(str(SHOTS / f"4_whatsnew_{ver}.png"))
            b.click("#modal [data-ok]")
            time.sleep(1)
            ok(b.eval("document.querySelector('#side-update').hidden"), "button gone after the update")
        elif what == "knowledge":
            b.eval("fetch('/api/update/check', {method: 'POST', headers: {'Content-Type': 'application/json', "
                   "'X-ML-Token': document.querySelector('meta[name=ml-token]').content}, body: '{}'})"
                   ".then(r => r.json())")
            ok(b.wait("!document.querySelector('#side-update').hidden", 15), "button appears")
            t = b.text("#side-update") or ""
            ok("New from friends" in t and "1 reference card" in t, f"button says New from friends: {t!r}")
            ok(b.eval("document.querySelector('#side-update').classList.contains('kn')"), "calmer style for knowledge")
            b.shot(str(SHOTS / "5_knowledge_button.png"))
            b.click("#side-update")
            ok(b.wait(MODAL, 10), "dialog opens")
            t = b.text("#modal .mbody") or ""
            ok("New knowledge from your friends" in t and "No restart needed" in t and "Get it now" in t,
               "knowledge dialog")
            b.shot(str(SHOTS / "6_knowledge_dialog.png"))
            ver_before = b.eval("document.querySelector('meta[name=ml-version]').content")
            b.click("#modal [data-go]")
            ok(b.wait(MODAL + " && document.querySelector('#modal .mbody').innerText.includes(\"Friends' knowledge "
                      "added\")", 30), "result dialog without a restart")
            ok(b.eval("document.querySelector('meta[name=ml-version]').content") == ver_before, "no restart")
            b.shot(str(SHOTS / "7_knowledge_added.png"))
            b.click("#modal [data-ok]")
            ok(b.wait("document.querySelector('#side-update').hidden", 10), "button gone")
        elif what == "settings":
            b.goto(URL + "#/settings", 2.5)
            ok(b.eval("document.querySelector('input[name=upm][value=ask]').checked"), "default choice: ask")
            b.click("input[name=upm][value=auto]")
            b.click("#save")
            time.sleep(1.5)
            st = json.loads((FRIEND / "settings.json").read_text(encoding="utf-8"))
            ok(st.get("update_mode") == "auto" and "update_auto" not in st, f"saved update_mode=auto: {st}")
            b.goto(URL + "#/settings", 2.5)
            ok(b.eval("document.querySelector('input[name=upm][value=auto]').checked"), "auto shown after reload")
            b.shot(str(SHOTS / "8_settings.png"))
            b.click("input[name=upm][value=ask]")
            b.click("#save")
            time.sleep(1)
            st = json.loads((FRIEND / "settings.json").read_text(encoding="utf-8"))
            ok(st.get("update_mode") == "ask", "back to ask")
        errs = b.eval("window.__errs || []")
        ok(not errs, f"no page errors {errs}")
    finally:
        b.close()
    print("ALL PASS" if not FAILED else "SOME FAILED")


if __name__ == "__main__":
    main()
