"""My Brand (0.6.0): the user's brand - knowledge\\local\\brand.json, the app's My Brand page. The logic is
tools\\motionlab\\brand.py (the file, checked on every save) and tools\\motionlab\\siteread.py (Import from your website).

    .venv\\Scripts\\python tools\\brand.py import [<url>]   read the user's own website (the saved one when no url):
                                                        name, description, colours, fonts, logos, pages, products ->
                                                        knowledge\\local\\brand\\import\\found.json + the pictures;
                                                        the page shows them, the user ticks what goes into My Brand
                                                        (the app's job "brand_import", group net)
    .venv\\Scripts\\python tools\\brand.py show             My Brand as a brief's *For my brand* section
    .venv\\Scripts\\python tools\\brand.py sound-logo "<description>" [--seconds 2]   (0.6.0 step 10) the brand's sound
                                                        logo made with ElevenLabs (the key of Motion Graphics > Sounds;
                                                        about 10 credits a second) -> knowledge\\local\\brand\\
                                                        sound_logo.<ext>, played on the end card
    .venv\\Scripts\\python tools\\brand.py selfcheck        known answers (no network)
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab import brand as BR  # noqa: E402
from motionlab import siteread as SR  # noqa: E402
from motionlab.util import setup_console  # noqa: E402


def main() -> int:
    setup_console()
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if a[0] == "import":
        url = a[1] if len(a) > 1 else (BR.load().get("site") or {}).get("url", "")
        if not url:
            print("No website: type it in My Brand > Your website first, or give it here.")
            return 2
        try:
            SR.read(url, lambda s: print(s, flush=True))
        except RuntimeError as e:
            print(f"ERROR: {e}")
            return 1
        return 0
    if a[0] == "show":
        snap = BR.snapshot()
        print("\n".join(BR.brief_lines(snap)) if snap else "My Brand is empty.")
        return 0
    if a[0] == "sound-logo":
        from motionlab import sfxgen as GEN
        if len(a) < 2 or not a[1].strip():
            print(f"Describe it, e.g.: brand.py sound-logo \"{BR.sound_logo_words(BR.load())}\"")
            return 2
        secs = float(a[a.index("--seconds") + 1]) if "--seconds" in a else 2.0
        s, P = GEN.settings(), GEN.prompts()
        if not s["key"]:
            print("ERROR: no ElevenLabs key yet - add yours in Motion Graphics > Sounds > Make sounds")
            return 1
        fmt = str(P.get("format") or "mp3_44100_128")
        print(f"making it ({secs:g} s, about {GEN.cost(secs)} credits): \"{a[1][:90]}\"", flush=True)
        try:
            raw = GEN._post(s["key"], a[1].strip(), secs, float(P.get("prompt_influence", 0.45)),
                            str(P.get("model") or ""), fmt)
            keep = GEN.OUT / time.strftime("%Y%m%d-%H%M%S") / f"sound_logo.{'wav' if fmt.startswith('wav') else 'mp3'}"
            keep.parent.mkdir(parents=True, exist_ok=True)
            keep.write_bytes(raw)
            b = BR.save_sound_logo(keep.name, raw)
        except (GEN.GenError, ValueError) as e:
            print(f"ERROR: {e}")
            return 1
        print(f"saved: {b['identity']['sound_logo']} - it plays on your end card (My Brand > Style)")
        return 0
    if a[0] == "selfcheck":
        ok = True
        for r in (BR.selfcheck(), SR.selfcheck()):
            print("\n".join(r["lines"]))
            ok = ok and r["passed"]
        print("PASS" if ok else "FAIL")
        return 0 if ok else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
