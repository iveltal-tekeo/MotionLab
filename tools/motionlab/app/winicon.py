"""MotionLab's own taskbar button (2026-10-24, a friend's ask: "MotionLab's icon, not Microsoft Edge's").

The window is Microsoft Edge in app mode, so Windows groups it under Edge with Edge's icon. While the server runs,
watch() looks every few seconds for MotionLab's windows (Edge's, titled "MotionLab") and gives each one its own
AppUserModelID "MotionLab" + the relaunch properties (the launcher, MotionLab.ico, the name) through
SHGetPropertyStoreForWindow, and MotionLab's icon (WM_SETICON): the window gets a taskbar button of its own and "Pin
to taskbar" pins MotionLab, not Edge. tag_shortcut() gives a MotionLab.lnk the same ID (system.make_shortcut, and the
Desktop / Start-menu shortcuts made before, once at start), so Windows matches the window with it.

Windows only, the standard library only (ctypes - no pywin32); every failure is silent: the app works without it.
"""
from __future__ import annotations

import os
import sys
import threading
import time
import uuid
from pathlib import Path

from motionlab.util import LAB

APP_ID = "MotionLab"
ICON = LAB / "MotionLab.ico"
TITLE = "MotionLab"                                       # index.html's <title>

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    class GUID(ctypes.Structure):
        _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD), ("Data3", wintypes.WORD),
                    ("Data4", ctypes.c_ubyte * 8)]

    class PROPERTYKEY(ctypes.Structure):
        _fields_ = [("fmtid", GUID), ("pid", wintypes.DWORD)]

    class PROPVARIANT(ctypes.Structure):                  # VT_LPWSTR only; 24 bytes on 64-bit Windows
        _fields_ = [("vt", wintypes.USHORT), ("r1", wintypes.WORD), ("r2", wintypes.WORD), ("r3", wintypes.WORD),
                    ("pwsz", ctypes.c_wchar_p), ("pad", ctypes.c_void_p)]

    def _guid(s: str) -> GUID:
        u, g = uuid.UUID(s), GUID()
        g.Data1, g.Data2, g.Data3 = u.time_low, u.time_mid, u.time_hi_version
        g.Data4[:] = list(u.bytes[8:])
        return g

    IID_IPropertyStore = _guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99")
    IID_IPersistFile = _guid("0000010B-0000-0000-C000-000000000046")
    IID_IShellLinkW = _guid("000214F9-0000-0000-C000-000000000046")
    CLSID_ShellLink = _guid("00021401-0000-0000-C000-000000000046")
    _AUM = "9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3"          # PKEY_AppUserModel_*: 2 RelaunchCommand, 3 RelaunchIcon-
    PK = {n: PROPERTYKEY(_guid(_AUM), pid) for n, pid in   # Resource, 4 RelaunchDisplayNameResource, 5 ID
          (("command", 2), ("icon", 3), ("name", 4), ("id", 5))}
    VT_LPWSTR = 31
    HRESULT = ctypes.c_long

    def _method(obj: ctypes.c_void_p, index: int, *argtypes):
        """A COM method of obj (its vtable entry index) as a callable taking the arguments after `this`."""
        vtbl = ctypes.cast(obj, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        fn = ctypes.WINFUNCTYPE(HRESULT, ctypes.c_void_p, *argtypes)(vtbl[index])
        return lambda *a: fn(obj, *a)

    def _release(obj) -> None:
        if obj and obj.value:
            ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(
                ctypes.cast(obj, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents[2])(obj)

    def _set_props(store: ctypes.c_void_p, values: dict) -> bool:
        set_value = _method(store, 6, ctypes.POINTER(PROPERTYKEY), ctypes.POINTER(PROPVARIANT))
        ok = True
        for k in ("command", "icon", "name", "id"):       # the relaunch properties first, the ID last
            if k in values:
                pv = PROPVARIANT(vt=VT_LPWSTR, pwsz=values[k])
                ok = set_value(ctypes.byref(PK[k]), ctypes.byref(pv)) >= 0 and ok
        return _method(store, 7)() >= 0 and ok           # Commit

    def relaunch() -> dict:
        pyw = LAB / ".venv" / "Scripts" / "pythonw.exe"
        return {"command": f'"{pyw}" "{LAB / "tools" / "app.py"}"', "icon": f"{ICON},0", "name": APP_ID, "id": APP_ID}

    def _exe_of(hwnd) -> str:
        pid = wintypes.DWORD()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        h = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid.value)       # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return ""
        try:
            buf, n = ctypes.create_unicode_buffer(1024), wintypes.DWORD(1024)
            ok = ctypes.windll.kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n))
            return buf.value if ok else ""
        finally:
            ctypes.windll.kernel32.CloseHandle(h)

    def windows() -> list[int]:
        """MotionLab's windows: visible top-level Edge windows titled exactly "MotionLab"."""
        out: list[int] = []
        u32 = ctypes.windll.user32

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def each(hwnd, _):
            if u32.IsWindowVisible(hwnd):
                t = ctypes.create_unicode_buffer(64)
                u32.GetWindowTextW(hwnd, t, 64)
                if t.value == TITLE:
                    c = ctypes.create_unicode_buffer(64)
                    u32.GetClassNameW(hwnd, c, 64)
                    if c.value.startswith("Chrome_WidgetWin") and _exe_of(hwnd).lower().endswith("msedge.exe"):
                        out.append(hwnd)
            return True
        u32.EnumWindows(each, 0)
        return out

    def tag_window(hwnd: int) -> bool:
        """MotionLab's AppUserModelID, relaunch properties and icon on one window."""
        store = ctypes.c_void_p()
        sh = ctypes.windll.shell32
        sh.SHGetPropertyStoreForWindow.argtypes = [wintypes.HWND, ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)]
        if sh.SHGetPropertyStoreForWindow(hwnd, ctypes.byref(IID_IPropertyStore), ctypes.byref(store)) < 0:
            return False
        try:
            ok = _set_props(store, relaunch())
        finally:
            _release(store)
        if ICON.is_file():
            u32 = ctypes.windll.user32
            u32.LoadImageW.restype = wintypes.HANDLE
            u32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
            for which, size in ((1, 32), (0, 16)):            # ICON_BIG, ICON_SMALL
                hi = u32.LoadImageW(None, str(ICON), 1, size, size, 0x10)       # IMAGE_ICON, LR_LOADFROMFILE
                if hi:
                    u32.SendMessageW(hwnd, 0x0080, which, hi)                     # WM_SETICON
        return ok

    def read_id(hwnd: int) -> str | None:
        """The AppUserModelID a window carries (tests)."""
        store = ctypes.c_void_p()
        sh = ctypes.windll.shell32
        sh.SHGetPropertyStoreForWindow.argtypes = [wintypes.HWND, ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)]
        if sh.SHGetPropertyStoreForWindow(hwnd, ctypes.byref(IID_IPropertyStore), ctypes.byref(store)) < 0:
            return None
        try:
            pv = PROPVARIANT()
            _method(store, 5, ctypes.POINTER(PROPERTYKEY), ctypes.POINTER(PROPVARIANT))(ctypes.byref(PK["id"]),
                                                                                        ctypes.byref(pv))
            return pv.pwsz if pv.vt == VT_LPWSTR else None
        finally:
            _release(store)

    def tag_shortcut(lnk: Path, only_ours: bool = True) -> bool:
        """MotionLab's AppUserModelID on a .lnk (made by system.make_shortcut) - only one that starts this lab's
        app.py when only_ours."""
        ole = ctypes.windll.ole32
        ole.CoInitializeEx(None, 2)                       # COINIT_APARTMENTTHREADED (S_FALSE when already)
        link, pf, store = ctypes.c_void_p(), ctypes.c_void_p(), ctypes.c_void_p()
        try:
            if ole.CoCreateInstance(ctypes.byref(CLSID_ShellLink), None, 1, ctypes.byref(IID_IShellLinkW),
                                    ctypes.byref(link)) < 0:
                return False
            qi = _method(link, 0, ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p))
            if qi(ctypes.byref(IID_IPersistFile), ctypes.byref(pf)) < 0:
                return False
            if _method(pf, 5, ctypes.c_wchar_p, wintypes.DWORD)(str(lnk), 2) < 0:      # Load(path, STGM_READWRITE)
                return False
            if only_ours:
                args = ctypes.create_unicode_buffer(2048)
                _method(link, 10, ctypes.c_wchar_p, ctypes.c_int)(args, 2048)            # GetArguments
                if str(LAB / "tools" / "app.py").lower() not in args.value.lower():
                    return False
            if qi(ctypes.byref(IID_IPropertyStore), ctypes.byref(store)) < 0:
                return False
            if not _set_props(store, {"id": APP_ID}):
                return False
            return _method(pf, 6, ctypes.c_wchar_p, wintypes.BOOL)(None, True) >= 0    # Save(same file)
        finally:
            for o in (store, pf, link):
                _release(o)
            ole.CoUninitialize()

    def known_shortcuts() -> list[Path]:
        """MotionLab.lnk on the Desktop and in the Start menu's Programs, where they exist."""
        out = []
        for csidl in (0x10, 0x02):                         # CSIDL_DESKTOPDIRECTORY, CSIDL_PROGRAMS
            buf = ctypes.create_unicode_buffer(260)
            if ctypes.windll.shell32.SHGetFolderPathW(None, csidl, None, 0, buf) == 0:
                p = Path(buf.value) / "MotionLab.lnk"
                if p.is_file():
                    out.append(p)
        return out


_started = False


def watch(every: float = 3.0) -> None:
    """Start the watcher (once per process): new MotionLab windows get their own taskbar button; the shortcuts made
    before get MotionLab's ID once."""
    global _started
    if sys.platform != "win32" or _started or os.environ.get("MOTIONLAB_NO_TASKBAR"):
        return
    _started = True

    def run():
        try:
            for lnk in known_shortcuts():
                tag_shortcut(lnk)
        except Exception:                                 # noqa: BLE001 - only the icon is at stake
            pass
        done: set[int] = set()
        while True:
            try:
                live = set(windows())
                for h in live - done:
                    tag_window(h)
                done = live
            except Exception:                             # noqa: BLE001
                pass
            time.sleep(every)
    threading.Thread(target=run, name="taskbar-icon", daemon=True).start()
