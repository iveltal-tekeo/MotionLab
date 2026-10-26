"""Content agency - your stats from the files the platforms let you download (0.6.0 step 13; docs\\plans.md: "the CSVs
YouTube Studio (Advanced mode > Export), TikTok Studio and Meta Business Suite (Insights > Export) give, dropped into
the app and matched to MotionLab's videos - views, watch time, retention where the platform gives it"): no login, no
reading of the platforms - the user's own export. A .csv (any delimiter, UTF-8 / UTF-16), an .xlsx (its first sheet,
read with the standard library) or YouTube Studio's .zip ("Table data.csv" inside); headers in English or Spanish.
knowledge\\local\\stats.json (never shared):
  "videos": {platform: {key: {id, url, title, date, views, likes, comments, shares, watch_h, avg_view_s, avg_pct,
                              impressions, ctr, subs, file, imported}}},   key = the id, else the link, else title|date
  "imports": [{"platform", "file", "rows", "date"}]

    import_file(path, platform=None) -> {"platform", "rows", "new", "updated", "columns"}   (platform guessed)
    load()
"""
from __future__ import annotations

import csv
import io
import json
import re
import time
import zipfile
from datetime import date, datetime
from pathlib import Path
from xml.etree import ElementTree as ET

from .util import LAB

PATH = Path(__import__("os").environ.get("MOTIONLAB_STATS") or LAB / "knowledge" / "local" / "stats.json")  # (tests)
PLATFORMS = ("youtube", "tiktok", "instagram", "facebook", "x", "linkedin", "threads")
# a column -> the key: the header lower-cased with its punctuation dropped, English and Spanish (the user's Studio may
# be in either); the first matching key wins, so the more precise words come first
COLS = [
    ("avg_pct", ("average percentage viewed", "porcentaje medio visto", "average watch percentage")),
    ("avg_view_s", ("average view duration", "duracion media de las visualizaciones", "duración media de las visualizaciones",
                    "average watch time", "tiempo medio de visualizacion", "tiempo medio de visualización")),
    ("watch_h", ("watch time hours", "tiempo de visualizacion horas", "tiempo de visualización horas", "total watch time",
                 "tiempo total de visualizacion", "tiempo total de visualización")),
    ("ctr", ("impressions clickthrough rate", "porcentaje de clics de las impresiones", "ctr")),
    ("impressions", ("impressions", "impresiones")),
    ("subs", ("subscribers", "suscriptores", "followers gained", "seguidores obtenidos")),
    ("id", ("content", "contenido", "video id", "id del video", "id del vídeo", "post id", "identificador de la publicacion",
            "identificador de la publicación", "id de la publicacion", "id de la publicación")),
    ("url", ("permalink", "enlace permanente", "video link", "enlace del video", "enlace del vídeo", "post link", "url", "link")),
    ("title", ("video title", "titulo del video", "título del vídeo", "título del video", "title", "titulo", "título",
               "description", "descripcion", "descripción", "caption", "texto")),
    ("date", ("video publish time", "hora de publicacion del video", "hora de publicación del vídeo",
              "hora de publicación del video", "publish time", "hora de publicacion", "hora de publicación", "post time",
              "posted", "date", "fecha", "created")),
    ("views", ("views", "visualizaciones", "video views", "visualizaciones del video", "plays", "reproducciones")),
    ("likes", ("likes", "me gusta", "reactions", "reacciones")),
    ("comments", ("comments", "comentarios")),
    ("shares", ("shares", "veces compartido", "compartidos", "compartir")),
]
NUMERIC = ("views", "likes", "comments", "shares", "watch_h", "avg_pct", "impressions", "ctr", "subs")


def _norm(h: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", str(h).lower())).strip()


def _col_map(headers: list[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for i, h in enumerate(headers):
        n = _norm(h)
        for key, words in COLS:
            if key in out:
                continue
            if any(n == _norm(w) or n.startswith(_norm(w) + " ") for w in words):
                out[key] = i
                break
    return out


def _xlsx_rows(data: bytes) -> list[list[str]]:
    """The first sheet of an .xlsx as rows of strings (shared strings and inline strings; numbers as written)."""
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", ns):
                shared.append("".join(t.text or "" for t in si.iter(f"{{{ns['m']}}}t")))
        sheets = sorted(n for n in z.namelist() if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n))
        if not sheets:
            return []
        root = ET.fromstring(z.read(sheets[0]))
    rows = []
    for r in root.iter(f"{{{ns['m']}}}row"):
        cells: dict[int, str] = {}
        for c in r.findall("m:c", ns):
            ref = re.match(r"([A-Z]+)", c.get("r", "A"))[1]
            col = 0
            for ch in ref:
                col = col * 26 + ord(ch) - 64
            v = c.find("m:v", ns)
            if c.get("t") == "s" and v is not None:
                cells[col - 1] = shared[int(v.text)]
            elif c.get("t") == "inlineStr":
                cells[col - 1] = "".join(t.text or "" for t in c.iter(f"{{{ns['m']}}}t"))
            else:
                cells[col - 1] = v.text if v is not None and v.text is not None else ""
        if cells:
            rows.append([cells.get(i, "") for i in range(max(cells) + 1)])
    return rows


def _csv_rows(data: bytes) -> list[list[str]]:
    for enc in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            text = data.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("the file's text could not be read")
    try:
        dialect = csv.Sniffer().sniff(text[:4000], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    return [r for r in csv.reader(io.StringIO(text), dialect) if any(x.strip() for x in r)]


def read_table(path: Path) -> list[list[str]]:
    """A file's rows: .csv, .xlsx, or a .zip holding one (YouTube Studio's "Table data.csv" first)."""
    path = Path(path)
    data = path.read_bytes()
    suf = path.suffix.lower()
    if suf == ".zip":
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            names = [n for n in z.namelist() if n.lower().endswith((".csv", ".xlsx"))]
            pick = next((n for n in names if re.search(r"table data|datos de la tabla", n, re.I)), names[0] if names else None)
            if not pick:
                raise ValueError("no table (.csv / .xlsx) in the zip")
            data, suf = z.read(pick), Path(pick).suffix.lower()
    if suf == ".xlsx":
        return _xlsx_rows(data)
    if suf in (".csv", ".txt", ".tsv"):
        return _csv_rows(data)
    raise ValueError("a .csv, .xlsx or .zip file from YouTube Studio, TikTok Studio or Meta Business Suite")


def _num(v) -> float | None:
    s = str(v or "").strip().replace(" ", " ").replace("%", "").strip()
    if not s or s in ("-", "—"):
        return None
    if re.fullmatch(r"\d+:\d{2}(:\d{2})?", s):                  # a duration 0:45 / 1:02:03 -> seconds
        parts = [int(x) for x in s.split(":")]
        return float(sum(p * 60 ** i for i, p in enumerate(reversed(parts))))
    s = s.replace(" ", "")
    if re.fullmatch(r"-?\d{1,3}(\.\d{3})+(,\d+)?", s):           # 1.234.567,8 (Spanish)
        s = s.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"-?\d{1,3}(,\d{3})+(\.\d+)?", s):         # 1,234,567.8
        s = s.replace(",", "")
    elif re.fullmatch(r"-?\d+,\d+", s):                          # 12,5
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _date(v) -> str:
    s = str(v or "").strip()
    if re.fullmatch(r"\d{5}(\.\d+)?", s):                        # an Excel serial date
        return date.fromordinal(date(1899, 12, 30).toordinal() + int(float(s))).isoformat()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%b %d, %Y", "%d %b %Y",
                "%m/%d/%Y %H:%M", "%m/%d/%Y", "%d/%m/%Y %H:%M", "%d/%m/%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(s[:len(datetime.now().strftime(fmt))] if "%b" not in fmt else s, fmt).date().isoformat()
        except ValueError:
            continue
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    return f"{m[1]}-{m[2]}-{m[3]}" if m else ""


def guess_platform(rows: list[dict]) -> str | None:
    blob = " ".join(str(r.get("url", "")) + " " + str(r.get("id", "")) for r in rows[:30]).lower()
    for p, rx in (("instagram", r"instagram\.com"), ("tiktok", r"tiktok\.com"), ("facebook", r"facebook\.com|fb\.watch"),
                  ("youtube", r"youtube\.com|youtu\.be")):
        if re.search(rx, blob):
            return p
    ids = [str(r.get("id", "")) for r in rows[:30] if r.get("id")]
    if ids and sum(bool(re.fullmatch(r"[A-Za-z0-9_-]{11}", x)) for x in ids) >= 0.8 * len(ids):
        return "youtube"
    if ids and sum(bool(re.fullmatch(r"\d{17,20}", x)) for x in ids) >= 0.8 * len(ids):
        return "tiktok"
    return None


def parse(path: Path) -> tuple[list[dict], list[str]]:
    """The export's video rows (the header found within its first 10 rows; a "Total" row left out) -> (rows,
    the keys found)."""
    raw = read_table(path)
    hi, cm = None, {}
    for i, r in enumerate(raw[:10]):
        cm = _col_map(r)
        if ("title" in cm or "id" in cm or "url" in cm) and ("views" in cm or "likes" in cm):
            hi = i
            break
    if hi is None:
        raise ValueError("no video table found (a header with the title or link and the views)")
    out = []
    for r in raw[hi + 1:]:
        row = {k: (r[i] if i < len(r) else "") for k, i in cm.items()}
        first = str(r[0] if r else "").strip().lower()
        if first in ("total", "totales", "totals") or not any(str(row.get(k, "")).strip() for k in ("title", "id", "url")):
            continue
        v = {"id": str(row.get("id", "")).strip()[:80], "url": str(row.get("url", "")).strip()[:300],
             "title": re.sub(r"\s+", " ", str(row.get("title", ""))).strip()[:200], "date": _date(row.get("date"))}
        for k in NUMERIC:
            if k in row:
                v[k] = _num(row[k])
        if "avg_view_s" in row:
            v["avg_view_s"] = _num(row["avg_view_s"])
        out.append(v)
    return out, sorted(cm)


def load(path: Path = PATH) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"videos": {}, "imports": []}


def _key(v: dict) -> str:
    return v.get("id") or v.get("url") or f"{v.get('title', '').lower()}|{v.get('date', '')}"


def import_file(src: Path, platform: str | None = None, name: str = "", path: Path = PATH) -> dict:
    """An export into stats.json (the platform guessed when not given); a video seen before = its numbers updated."""
    rows, keys = parse(src)
    if not rows:
        raise ValueError("no video rows in the file")
    plat = platform if platform in PLATFORMS else guess_platform(rows)
    if not plat:
        raise ValueError("which platform is it from? - pick it")
    S = load(path)
    have = S["videos"].setdefault(plat, {})
    new = upd = 0
    today = time.strftime("%Y-%m-%d")
    for v in rows:
        k = _key(v)
        if k in have:
            upd += 1
        else:
            new += 1
        have[k] = {**have.get(k, {}), **{x: y for x, y in v.items() if y not in (None, "")},
                   "file": name or Path(src).name, "imported": today}
    S["imports"] = (S.get("imports") or [])[-49:] + [{"platform": plat, "file": name or Path(src).name, "rows": len(rows),
                                                      "date": time.strftime("%Y-%m-%d %H:%M")}]
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(S, indent=1, ensure_ascii=False), encoding="utf-8")
    return {"platform": plat, "rows": len(rows), "new": new, "updated": upd, "columns": keys}


def selfcheck() -> dict:
    """Made-up exports (no files of the user's): YouTube Studio in Spanish inside a zip, an Instagram CSV with ';'
    and Spanish numbers, a TikTok .xlsx written here -> rows, columns, the platform guessed; one imported twice = updated."""
    import tempfile
    t0, lines, ok = time.time(), [], True

    def case(name, cond):
        nonlocal ok
        ok &= bool(cond)
        lines.append(("PASS " if cond else "FAIL ") + name)
    with tempfile.TemporaryDirectory(prefix="ml_stats_") as td:
        td = Path(td)
        yt = ("Contenido,Título del vídeo,Hora de publicación del vídeo,Duración,Visualizaciones,Tiempo de visualización "
              "(horas),Suscriptores,Impresiones,Porcentaje de clics de las impresiones (%),Duración media de las "
              "visualizaciones\nTotal,,,,2410,51.2,12,30100,5.1,0:38\n"
              "dQw4w9WgXcQ,Your song needs a real video,\"Oct 25, 2026\",31,1840,40.1,9,22000,6.2,0:41\n"
              "abcdefghijk,How I edit,\"Oct 20, 2026\",58,570,11.1,3,8100,3.4,1:02\n")
        with zipfile.ZipFile(td / "yt.zip", "w") as z:
            z.writestr("Datos de la tabla.csv", yt)
        r1 = import_file(td / "yt.zip", path=td / "s.json")
        S = load(td / "s.json")
        v = S["videos"]["youtube"]["dQw4w9WgXcQ"]
        case(f"YouTube Studio in Spanish (a zip): {r1['rows']} videos, the total row left out, the platform guessed; "
             f"views {v['views']:g}, watch {v['watch_h']:g} h, CTR {v['ctr']:g} %, average view {v['avg_view_s']:g} s, "
             f"date {v['date']}", r1["platform"] == "youtube" and r1["rows"] == 2 and v["views"] == 1840
             and v["avg_view_s"] == 41 and v["date"] == "2026-10-25" and v["ctr"] == 6.2)
        ig = ("Identificador de la publicación;Enlace permanente;Descripción;Hora de publicación;Visualizaciones;Me gusta;"
              "Comentarios;Veces compartido\n1789;https://www.instagram.com/reel/AbC/;Behind the scenes;25/10/2026 18:02;"
              "12.450;1.203;87;40\n")
        (td / "ig.csv").write_text(ig, encoding="utf-8-sig")
        r2 = import_file(td / "ig.csv", path=td / "s.json")
        w = load(td / "s.json")["videos"]["instagram"]["1789"]
        case(f"Instagram (Meta Business Suite, ';' and Spanish numbers): views {w['views']:g}, likes {w['likes']:g}",
             r2["platform"] == "instagram" and w["views"] == 12450 and w["likes"] == 1203 and w["date"] == "2026-10-25")
        sheet = ('<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
                 '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c><c r="C1" t="s"><v>2</v></c></row>'
                 '<row r="2"><c r="A2" t="s"><v>3</v></c><c r="B2"><v>45931</v></c><c r="C2"><v>9800</v></c></row>'
                 '</sheetData></worksheet>')
        sst = ('<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><si><t>Video title</t></si>'
               '<si><t>Post time</t></si><si><t>Video views</t></si><si><t>My first edit</t></si></sst>')
        with zipfile.ZipFile(td / "tt.xlsx", "w") as z:
            z.writestr("xl/worksheets/sheet1.xml", sheet)
            z.writestr("xl/sharedStrings.xml", sst)
        r3 = import_file(td / "tt.xlsx", platform="tiktok", path=td / "s.json")
        x = list(load(td / "s.json")["videos"]["tiktok"].values())[0]
        r4 = import_file(td / "yt.zip", path=td / "s.json")
        case(f"a TikTok .xlsx read without a library (views {x['views']:g}, date {x['date']}); the YouTube file again = "
             "2 updated, 0 new", r3["rows"] == 1 and x["views"] == 9800 and x["date"] == "2025-10-01"
             and r4["new"] == 0 and r4["updated"] == 2)
        try:
            (td / "x.csv").write_text("a,b\n1,2\n", encoding="utf-8")
            import_file(td / "x.csv", path=td / "s.json")
            case("a file with no video table refused", False)
        except ValueError:
            case("a file with no video table refused", True)
    return {"passed": ok, "seconds": round(time.time() - t0, 2), "lines": lines}
