"""Write DaVinci Resolve / Fusion compositions (.comp text, a Lua table) from Python.

A Comp holds tools in creation order; inputs are plain values or the helpers below:
    Conn("Tool")                    -> the output of another tool (Source = "Output")
    Conn("Rect1", "Mask")           -> a mask output
    Expr("Merge1.Blend * 2")        -> an expression
    FuID("Fast Gaussian")           -> an enumerated value
    Spline([(f, v), ...])           -> a keyframed number (linear, or "step" holds)
    Path([(f, x, y), ...])          -> a keyframed point (XYPath with linear X / Y splines)
Points are tuples (x, y) in Fusion's normalised coordinates (x right, y UP, 0..1 of the image).
`Comp.text()` returns the composition; Resolve imports it with TimelineItem.ImportFusionComp(path).
`parse_comp(text)` reads such a text back (what the lab imported), so a live comp can be compared with it.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field


@dataclass
class Conn:
    tool: str
    source: str = "Output"


@dataclass
class Expr:
    expr: str
    value: object = None


@dataclass
class FuID:
    name: str


@dataclass
class Spline:
    keys: list                     # [(frame, value)] sorted; consecutive equal values collapse
    step: bool = False             # True: each key holds until the next one (no interpolation)
    color: tuple = (205, 205, 205)


@dataclass
class Path:
    keys: list                     # [(frame, x, y)]


@dataclass
class Raw:
    text: str                      # a literal Lua value


def lua_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def lua_num(v: float) -> str:
    v = float(v)
    if math.isfinite(v) and v == int(v) and abs(v) < 1e15:
        return str(int(v))
    return repr(round(v, 9))


def lua_val(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return lua_num(v)
    if isinstance(v, str):
        return lua_str(v)
    if isinstance(v, FuID):
        return f"FuID {{ {lua_str(v.name)} }}"
    if isinstance(v, Raw):
        return v.text
    if isinstance(v, (tuple, list)):
        return "{ " + ", ".join(lua_val(x) for x in v) + " }"
    if isinstance(v, dict):
        return "{ " + ", ".join(f"{_key(k)} = {lua_val(x)}" for k, x in v.items()) + " }"
    raise TypeError(f"cannot write {type(v)} to Lua")


def _key(k: str) -> str:
    return k if k.replace("_", "").isalnum() and not k[0].isdigit() else f"[{lua_str(k)}]"


def spline_keys(keys: list, step: bool = False) -> list:
    """Drop keys that a linear (or step) interpolation reproduces exactly: per-frame curves become compact
    but evaluate to the same value on every integer frame."""
    keys = sorted((int(f), float(v)) for f, v in keys)
    if len(keys) <= 2:
        return keys
    out = [keys[0]]
    for i in range(1, len(keys) - 1):
        f0, v0 = out[-1]
        f1, v1 = keys[i]
        f2, v2 = keys[i + 1]
        if step:
            if v1 != v0:
                out.append(keys[i])
            continue
        # keep the key unless it lies on the straight line from the last kept key to the next key
        t = (f1 - f0) / (f2 - f0)
        if abs(v0 + (v2 - v0) * t - v1) > 1e-9 * max(1.0, abs(v1)):
            out.append(keys[i])
    out.append(keys[-1])
    return out


@dataclass
class Tool:
    name: str
    kind: str
    inputs: dict
    pos: tuple
    extra: str = ""                # raw Lua fields (e.g. MediaIn Clips/CustomData)
    controls: dict = field(default_factory=dict)   # custom Inspector controls (UserControls), see Comp.control


@dataclass
class Comp:
    tools: list = field(default_factory=list)
    names: set = field(default_factory=set)
    fps: float = 25.0
    width: int = 1520
    height: int = 1080
    render_range: tuple | None = None
    t0: int = 0                    # keys are written at frame - t0: a Resolve clip's comp starts at 0 on its first frame
    _col: int = 0

    def uid(self, base: str) -> str:
        i = 1
        while f"{base}{i}" in self.names:
            i += 1
        return f"{base}{i}"

    def add(self, kind: str, name: str | None = None, pos: tuple | None = None, extra: str = "",
            **inputs) -> str:
        name = name or self.uid(kind)
        if name in self.names:
            raise ValueError(f"duplicate tool name {name}")
        self.names.add(name)
        if pos is None:
            pos = (self._col * 110, 0)
            self._col += 1
        self.tools.append(Tool(name, kind, inputs, pos, extra))
        return name

    # ---------------------------------------------------------------------------------------------- text
    def _input(self, tname: str, key: str, v, out: list) -> str:
        if isinstance(v, Conn):
            return f"Input {{ SourceOp = {lua_str(v.tool)}, Source = {lua_str(v.source)}, }}"
        if isinstance(v, Expr):
            val = f"Value = {lua_val(v.value)}, " if v.value is not None else ""
            return f"Input {{ {val}Expression = {lua_str(v.expr)}, }}"
        if isinstance(v, Spline):
            sname = f"{tname}{key.replace('.', '')}"
            keys = spline_keys([(f - self.t0, val) for f, val in v.keys], v.step)
            if len(keys) == 1:
                return f"Input {{ Value = {lua_num(keys[0][1])}, }}"
            out.append(self._spline_text(sname, keys, v.step, v.color))
            return f"Input {{ SourceOp = {lua_str(sname)}, Source = \"Value\", }}"
        if isinstance(v, Path):
            pname = f"{tname}{key}Path"
            xs = spline_keys([(f - self.t0, x) for f, x, _ in v.keys])
            ys = spline_keys([(f - self.t0, y) for f, _, y in v.keys])
            out.append(self._spline_text(pname + "X", xs, False, (255, 0, 0)))
            out.append(self._spline_text(pname + "Y", ys, False, (0, 255, 0)))
            out.append(f"\t\t{pname} = XYPath {{\n\t\t\tShowKeyPoints = false,\n\t\t\tDrawMode = \"ModifyOnly\",\n"
                       f"\t\t\tInputs = {{\n"
                       f"\t\t\t\tX = Input {{ SourceOp = {lua_str(pname + 'X')}, Source = \"Value\", }},\n"
                       f"\t\t\t\tY = Input {{ SourceOp = {lua_str(pname + 'Y')}, Source = \"Value\", }},\n"
                       f"\t\t\t}},\n\t\t}},\n")
            return f"Input {{ SourceOp = {lua_str(pname)}, Source = \"Value\", }}"
        return f"Input {{ Value = {lua_val(v)}, }}"

    @staticmethod
    def _spline_text(name: str, keys: list, step: bool, color: tuple) -> str:
        rows = []
        for i, (f, v) in enumerate(keys):
            parts = [lua_num(v)]
            if i > 0:
                pf, pv = keys[i - 1]
                parts.append(f"LH = {{ {lua_num(f - (f - pf) / 3)}, {lua_num(v - (v - pv) / 3)} }}")
            if i < len(keys) - 1:
                nf, nv = keys[i + 1]
                parts.append(f"RH = {{ {lua_num(f + (nf - f) / 3)}, {lua_num(v + (nv - v) / 3)} }}")
            parts.append("Flags = { StepIn = true }" if step else "Flags = { Linear = true }")
            rows.append(f"\t\t\t\t[{int(f)}] = {{ {', '.join(parts)} }}")
        r, g, b = color
        return (f"\t\t{name} = BezierSpline {{\n\t\t\tSplineColor = {{ Red = {r}, Green = {g}, Blue = {b} }},\n"
                f"\t\t\tNameSet = true,\n\t\t\tKeyFrames = {{\n" + ",\n".join(rows) + "\n\t\t\t}\n\t\t},\n")

    def control(self, tool: str, cid: str, label: str, default: float = 0.0, lo: float = 0.0, hi: float = 1.0,
                integer: bool = False, kind: str = "SliderControl", page: str = "Controls", choices=None):
        """A custom Inspector control (UserControls) on a tool; other tools read it in expressions as Tool.cid.
        kind: SliderControl / CheckboxControl / ComboControl (choices = labels)."""
        t = next(x for x in self.tools if x.name == tool)
        c = {"LINKS_Name": label, "LINKID_DataType": "Number", "INPID_InputControl": kind,
             "INP_Default": float(default), "ICS_ControlPage": page}
        if kind == "SliderControl":
            c.update(INP_MinScale=float(lo), INP_MaxScale=float(hi))
        if integer:
            c["INP_Integer"] = True
        if choices:
            c["CCS_AddString"] = list(choices)
        t.controls[cid] = c
        t.inputs.setdefault(cid, float(default))

    def _controls_text(self, t: Tool) -> str:
        if not t.controls:
            return ""
        rows = []
        for cid, c in t.controls.items():
            fields = []
            for k, v in c.items():
                if k == "CCS_AddString":
                    fields += [f"{{ CCS_AddString = {lua_str(s)}, }}" for s in v]
                else:
                    fields.append(f"{k} = {lua_val(v)}")
            rows.append(f"\t\t\t\t{_key(cid)} = {{ " + ", ".join(fields) + ", },")
        return "\t\t\tUserControls = ordered() {\n" + "\n".join(rows) + "\n\t\t\t},\n"

    def tools_text(self, indent: int = 0) -> str:
        """The tool definitions (the body of Tools = ordered() { ... }), optionally indented for a macro."""
        out = []
        for t in self.tools:
            extra_tools: list = []
            ins = []
            for k, v in t.inputs.items():
                key = k.replace("__", ".")
                ins.append(f"\t\t\t\t{_key(key)} = {self._input(t.name, key, v, extra_tools)},")
            body = f"\t\t{t.name} = {t.kind} {{\n"
            if t.extra:
                body += t.extra
            body += "\t\t\tInputs = {\n" + "\n".join(ins) + "\n\t\t\t},\n"
            body += self._controls_text(t)
            body += f"\t\t\tViewInfo = OperatorInfo {{ Pos = {{ {t.pos[0]}, {t.pos[1]} }} }},\n\t\t}},\n"
            out.append(body)
            out.extend(extra_tools)
        text = "".join(out)
        if indent:
            text = "".join(("\t" * indent + ln if ln.strip() else ln) for ln in text.splitlines(True))
        return text

    def text(self) -> str:
        rr = ""
        if self.render_range:
            rr = f"\tRenderRange = {{ {self.render_range[0] - self.t0}, {self.render_range[1] - self.t0} }},\n"
        return ("Composition {\n" + rr + "\tTools = ordered() {\n" + self.tools_text() + "\t},\n"
                f"\tPrefs = {{ Comp = {{ FrameFormat = {{ Rate = {lua_num(self.fps)}, Width = {self.width}, "
                f"Height = {self.height}, }}, }}, }},\n}}\n")

    def macro_block(self, name: str, inputs: list, outputs: list, help_text: str = "") -> str:
        """A MacroOperator holding this comp's tools. inputs: [(id, tool, input id, label or None, extra dict)];
        outputs: [(id, tool, output id)]. Ids MainInput1 / MainOutput1 make it an Edit-page effect / title."""
        rows = []
        for iid, tool, src, label, extra in inputs:
            f = [f"SourceOp = {lua_str(tool)}", f"Source = {lua_str(src)}"]
            if label:
                f.append(f"Name = {lua_str(label)}")
            for k, v in (extra or {}).items():
                f.append(f"{k} = {lua_val(v)}")
            rows.append(f"\t\t\t\t{_key(iid)} = InstanceInput {{ " + ", ".join(f) + ", },")
        outs = [f"\t\t\t\t{oid} = InstanceOutput {{ SourceOp = {lua_str(tool)}, Source = {lua_str(src)}, }},"
                for oid, tool, src in outputs]
        cd = f"\t\t\tCustomData = {{ HelpPage = {lua_str(help_text)}, }},\n" if help_text else ""
        return (f"\t\t{name} = MacroOperator {{\n\t\t\tCtrlWZoom = false,\n\t\t\tNameSet = true,\n{cd}"
                "\t\t\tInputs = ordered() {\n" + "\n".join(rows) + "\n\t\t\t},\n"
                "\t\t\tOutputs = {\n" + "\n".join(outs) + "\n\t\t\t},\n"
                "\t\t\tViewInfo = GroupInfo { Pos = { 0, 0 } },\n"
                "\t\t\tTools = ordered() {\n" + self.tools_text(indent=2) + "\t\t\t},\n\t\t},\n")

    def setting_text(self, name: str, inputs: list, outputs: list, help_text: str = "") -> str:
        """A Fusion macro file (.setting) - what Resolve loads from its Templates / Macros folders."""
        return ("{\n\tTools = ordered() {\n" + self.macro_block(name, inputs, outputs, help_text) + "\t},\n"
                f"\tActiveTool = {lua_str(name)}\n}}\n")


def media_in_extra(path: str, media_id: str, name: str, frames: int, width: int, height: int, fps: float,
                   layer: int) -> str:
    """The Clips / CustomData block of a MediaIn that reads a Resolve media pool clip (by its media ID)."""
    return (f"\t\t\tCustomData = {{ MediaProps = {{ MEDIA_ID = {lua_str(media_id)}, MEDIA_NAME = {lua_str(name)}, "
            f"MEDIA_PATH = {lua_str(path)}, MEDIA_WIDTH = {width}, MEDIA_HEIGHT = {height}, "
            f"MEDIA_NUM_FRAMES = {frames}, MEDIA_SRC_FRAME_RATE = {lua_num(fps)}, MEDIA_START_FRAME = 0, "
            f"MEDIA_MARK_IN = 0, MEDIA_MARK_OUT = {frames - 1}, MEDIA_IS_SOURCE_RES = true, MEDIA_PAR = 1, "
            f"MEDIA_NUM_LAYERS = 1, MEDIA_FORMAT_TYPE = \"QuickTime\", MEDIA_HAS_AUDIO = false, }}, }},\n"
            f"\t\t\tClips = {{ Clip {{ ID = \"Clip1\", Multiframe = true, Filename = {lua_str(path)}, "
            f"Length = {frames}, LengthSetManually = true, GlobalEnd = {frames - 1}, TrimOut = {frames - 1}, }}, }},\n")


def media_in(comp: Comp, path: str, media_id: str, name: str, frames: int, width: int, height: int, fps: float,
             tool_name: str | None = None, layer: int = 1, pos: tuple | None = None) -> str:
    return comp.add("Loader", tool_name or comp.uid("MediaIn"), pos,
                    media_in_extra(path, media_id, name, frames, width, height, fps, layer),
                    MediaSource=FuID("MediaPool"), MediaID=media_id, Layer=str(layer), GlobalOut=frames - 1,
                    ClipTimeEnd=frames - 1, AudioTrack=FuID("No_Audo_Track"))


# ---------------------------------------------------------------------------------------------- reading back
@dataclass
class CompSpec:
    """A comp text written by Comp.text(), read back. Input values are (form, value):
    num -> float, point -> (x, y), fuid / str -> str, conn -> (tool, output), anim -> spline or path name,
    expr -> expression text, raw -> literal Lua (polylines, gradients; not compared)."""
    tools: dict                    # name -> (kind, {input: (form, value)})
    splines: dict                  # name -> [(comp frame, value, step)]
    paths: dict                    # name -> (X spline name, Y spline name)
    render_range: tuple | None


_NUM = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"
_TOOL = re.compile(r"^\t\t(\w+) = (\w+) \{$")
_INPUT = re.compile(r'^\t\t\t\t(\["[^"]+"\]|\w+) = Input \{ (.*) \},$')
_SKEY = re.compile(rf"^\t\t\t\t\[(-?\d+)\] = \{{ ({_NUM})(.*)$")
_FORMS = [("num", re.compile(rf"^Value = ({_NUM})$")),
          ("point", re.compile(rf"^Value = \{{ ({_NUM}), ({_NUM}) \}}$")),
          ("fuid", re.compile(r'^Value = FuID \{ "(.*)" \}$')),
          ("str", re.compile(r'^Value = "(.*)"$')),
          ("conn", re.compile(r'^SourceOp = "(.*)", Source = "(.*)"$')),
          ("expr", re.compile(r'^(?:Value = .*?, )?Expression = "(.*)"$')),
          ("raw", re.compile(r"^Value = (.*)$"))]


def lua_unstr(s: str) -> str:
    return re.sub(r"\\(.)", lambda m: "\n" if m.group(1) == "n" else m.group(1), s)


def parse_comp(text: str) -> CompSpec:
    tools, splines, paths, rr = {}, {}, {}, None
    m = re.search(rf"^\tRenderRange = \{{ ({_NUM}), ({_NUM}) \}},$", text, re.M)
    if m:
        rr = (int(float(m.group(1))), int(float(m.group(2))))
    cur = None
    for line in text.split("\n"):
        mt = _TOOL.match(line)
        if mt:
            cur, kind = mt.group(1), mt.group(2)
            if kind == "BezierSpline":
                splines[cur] = []
            else:
                tools[cur] = (kind, {})
            continue
        if cur is None:
            continue
        if cur in splines:
            mk = _SKEY.match(line)
            if mk:
                splines[cur].append((int(mk.group(1)), float(mk.group(2)), "StepIn" in mk.group(3)))
            continue
        mi = _INPUT.match(line)
        if not mi:
            continue
        key = mi.group(1).strip('[]"')
        body = mi.group(2).rstrip().rstrip(",")
        for form, rx in _FORMS:
            mf = rx.match(body)
            if not mf:
                continue
            if form == "num":
                v = float(mf.group(1))
            elif form == "point":
                v = (float(mf.group(1)), float(mf.group(2)))
            elif form == "conn":
                v = (mf.group(1), mf.group(2))
                if v[1] == "Value":                    # driven by a spline or a path
                    form, v = "anim", v[0]
            elif form == "raw":
                v = mf.group(1)
            else:
                v = lua_unstr(mf.group(1))
            tools[cur][1][key] = (form, v)
            break
    for name in [n for n, (k, _) in tools.items() if k == "XYPath"]:
        ins = tools.pop(name)[1]
        paths[name] = (ins["X"][1], ins["Y"][1])
    return CompSpec(tools, splines, paths, rr)


def spline_at(keys: list, t: float) -> float:
    """Value of a parsed spline (linear keys, or step keys that hold until the next one) at comp frame t."""
    if t <= keys[0][0]:
        return keys[0][1]
    for (f0, v0, step), (f1, v1, _) in zip(keys, keys[1:]):
        if f0 <= t < f1:
            return v0 if step else v0 + (v1 - v0) * (t - f0) / (f1 - f0)
    return keys[-1][1]
