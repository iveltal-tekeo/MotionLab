"""Tiny headless-Edge driver for app tests (stdlib only): DevTools protocol over a minimal websocket client.

    from cdp import Browser
    b = Browser(port=9333)                 # starts msedge --headless=new with its own profile
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
import time
import urllib.request
from pathlib import Path

EDGE = [Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Microsoft/Edge/Application/msedge.exe",
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Microsoft/Edge/Application/msedge.exe"]
PROFILE = Path(__file__).resolve().parents[2] / ".app" / "dev" / "edge-profile"   # scratch, not in git


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


class Browser:
    def __init__(self, port: int = 9333, width: int = 1600, height: int = 1000):
        edge = next(p for p in EDGE if p.exists())
        shutil.rmtree(PROFILE, ignore_errors=True)
        self.proc = subprocess.Popen([str(edge), "--headless=new", f"--remote-debugging-port={port}",
                                      f"--user-data-dir={PROFILE}", f"--window-size={width},{height}",
                                      "--no-first-run", "--disable-extensions", "about:blank"])
        for _ in range(60):
            try:
                tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=2))
                page = next(t for t in tabs if t.get("type") == "page")
                break
            except (OSError, StopIteration, ValueError):
                time.sleep(0.5)
        else:
            raise RuntimeError("Edge did not start")
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
