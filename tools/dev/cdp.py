"""Tiny headless-Edge driver for app tests (stdlib only): DevTools protocol over a minimal websocket client.

    from cdp import Browser
    b = Browser()                          # starts msedge --headless=new with its own profile, on a free port
    b.goto("http://127.0.0.1:8791/")
    b.wait("document.querySelector('#side-update') && !document.querySelector('#side-update').hidden")
    print(b.eval("document.title"))
    b.shot(r"C:\\MotionLab\\.app\\dev\\shot.png")
    b.close()
"""
from __future__ import annotations

import base64
import json
import os
import shutil
import socket
import struct
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

EDGE = [Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Microsoft/Edge/Application/msedge.exe",
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Microsoft/Edge/Application/msedge.exe",
        Path("/opt/pw-browsers/chromium")]                  # a Claude Code cloud session (Linux): Playwright's Chromium
PROFILES = Path(__file__).resolve().parents[2] / ".app" / "dev"     # edge-<pid>-*: one profile per run, not in git


class WS:
    def __init__(self, url: str):
        assert url.startswith("ws://")
        hostport, path = url[5:].split("/", 1)
        host, port = hostport.split(":")
        self.s = socket.create_connection((host, int(port)), timeout=30)
        key = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall((f"GET /{path} HTTP/1.1\r\nHost: {hostport}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                        f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            buf += self.s.recv(4096)
        head, self.rest = buf.split(b"\r\n\r\n", 1)
        if b" 101 " not in head.split(b"\r\n")[0]:
            raise RuntimeError(head.decode(errors="replace"))

    def send(self, text: str):
        data = text.encode()
        hdr = bytearray([0x81])
        n = len(data)
        if n < 126:
            hdr.append(0x80 | n)
        elif n < 65536:
            hdr.append(0x80 | 126)
            hdr += struct.pack(">H", n)
        else:
            hdr.append(0x80 | 127)
            hdr += struct.pack(">Q", n)
        mask = os.urandom(4)
        hdr += mask
        self.s.sendall(bytes(hdr) + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def _read(self, n: int) -> bytes:
        while len(self.rest) < n:
            chunk = self.s.recv(65536)
            if not chunk:
                raise ConnectionError("websocket closed")
            self.rest += chunk
        out, self.rest = self.rest[:n], self.rest[n:]
        return out

    def recv(self) -> str:
        parts = []
        while True:
            b0, b1 = self._read(2)
            n = b1 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._read(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._read(8))[0]
            payload = self._read(n)
            op = b0 & 0x0F
            if op == 0x8:
                raise ConnectionError("websocket closed by peer")
            if op in (0x9, 0xA):
                continue
            parts.append(payload)
            if b0 & 0x80:
                return b"".join(parts).decode(errors="replace")


def _alive(pid: int) -> bool:
    """Does process <pid> still run? (os.kill(pid, 0) would send Ctrl+C on Windows.)"""
    if os.name != "nt":
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except OSError:
            return True
        return True
    import ctypes
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.OpenProcess.restype = ctypes.c_void_p
    h = k.OpenProcess(0x1000, False, pid)                           # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return ctypes.get_last_error() == 5                         # access denied: it exists
    code = ctypes.c_ulong()
    ok = k.GetExitCodeProcess(ctypes.c_void_p(h), ctypes.byref(code))
    k.CloseHandle(ctypes.c_void_p(h))
    return bool(ok) and code.value == 259                           # STILL_ACTIVE


def _sweep() -> None:
    """Profiles of runs that died without close() (a killed test): their test process is gone. And the one profile
    every run shared before 2026-10-19 (edge-profile)."""
    shutil.rmtree(PROFILES / "edge-profile", ignore_errors=True)
    for d in PROFILES.glob("edge-*-*"):
        pid = d.name.split("-")[1]
        if d.is_dir() and pid.isdigit() and not _alive(int(pid)):
            shutil.rmtree(d, ignore_errors=True)


class Browser:
    def __init__(self, port: int = 0, width: int = 1600, height: int = 1000):
        """port 0 = a free one Edge picks itself (read back from its DevToolsActivePort file). Every run gets its own
        profile folder, removed again by close(): two tests at once never share a profile or a port."""
        edge = next(p for p in EDGE if p.exists())
        PROFILES.mkdir(parents=True, exist_ok=True)
        _sweep()
        self.profile = Path(tempfile.mkdtemp(prefix=f"edge-{os.getpid()}-", dir=PROFILES))
        self.proc = subprocess.Popen([str(edge), "--headless=new", f"--remote-debugging-port={port}",
                                      f"--user-data-dir={self.profile}", f"--window-size={width},{height}",
                                      "--no-first-run", "--disable-extensions"]
                                     + (["--no-sandbox"] if os.name != "nt" else []) + ["about:blank"])
        page, t0 = None, time.time()
        while page is None:
            if self.proc.poll() is not None or time.time() - t0 > 30:     # gone, or no DevTools port: fail now
                gone = self.proc.poll()
                if gone is None:
                    self.proc.kill()
                    self.proc.wait(timeout=10)
                self._remove()
                raise RuntimeError("Edge did not start" + (f" (it exited with {gone})" if gone is not None else
                                                           " (no DevTools port after 30 s)"))
            try:
                self.port = int((self.profile / "DevToolsActivePort").read_text().split()[0])
                tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{self.port}/json/list", timeout=2))
                page = next(t for t in tabs if t.get("type") == "page")
            except (OSError, IndexError, StopIteration, ValueError):
                time.sleep(0.2)
        self.ws = WS(page["webSocketDebuggerUrl"])
        self.i = 0
        self.call("Page.enable")
        self.call("Runtime.enable")
        self.call("Emulation.setDeviceMetricsOverride", width=width, height=height, deviceScaleFactor=1, mobile=False)
        self.call("Page.addScriptToEvaluateOnNewDocument",       # page errors -> window.__errs (tests check it)
                  source="window.__errs = []; addEventListener('error', e => __errs.push(String(e.message))); "
                         "addEventListener('unhandledrejection', e => __errs.push(String(e.reason && "
                         "(e.reason.message || e.reason))));")

    def call(self, method: str, **params):
        self.i += 1
        my = self.i
        self.ws.send(json.dumps({"id": my, "method": method, "params": params}))
        while True:
            m = json.loads(self.ws.recv())
            if m.get("id") == my:
                if "error" in m:
                    raise RuntimeError(f"{method}: {m['error']}")
                return m.get("result", {})

    def eval(self, expr: str, await_promise: bool = True):
        r = self.call("Runtime.evaluate", expression=expr, returnByValue=True, awaitPromise=await_promise)
        if r.get("exceptionDetails"):
            raise RuntimeError(json.dumps(r["exceptionDetails"])[:800])
        return r.get("result", {}).get("value")

    def goto(self, url: str, settle: float = 1.5):
        self.call("Page.navigate", url=url)
        time.sleep(settle)

    def wait(self, expr: str, timeout: float = 30, every: float = 0.5):
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                if self.eval(f"!!({expr})"):
                    return True
            except (RuntimeError, ConnectionError):
                pass
            time.sleep(every)
        return False

    def click(self, selector: str):
        return self.eval(f"(() => {{ const e = document.querySelector({json.dumps(selector)}); if (!e) return false; "
                         f"e.click(); return true; }})()")

    def text(self, selector: str):
        return self.eval(f"(() => {{ const e = document.querySelector({json.dumps(selector)}); "
                         f"return e ? e.innerText : null; }})()")

    def shot(self, path: str):
        r = self.call("Page.captureScreenshot", format="png")
        Path(path).write_bytes(base64.b64decode(r["data"]))
        return path

    def close(self):
        try:
            self.call("Browser.close")
        except Exception:                                   # noqa: BLE001
            pass
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait(timeout=10)
        self._remove()

    def _remove(self):
        """This run's profile, once Edge let go of it (its helper processes close their files a moment later)."""
        for _ in range(20):
            shutil.rmtree(self.profile, ignore_errors=True)
            if not self.profile.exists():
                return
            time.sleep(0.25)
