"""Optional developer handoff: masked key entry and Windows user-bound encryption.

The desktop agent's normal key field remains session-only. This separate helper
lets the project operator configure a key locally without sending it through chat.
Its encrypted file is outside the repository and is removed after the live task.
DPAPI reference: https://learn.microsoft.com/windows/win32/api/dpapi/
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path


PURPOSE = "Task1CodeAgent-local-live-key-v1"


def key_path() -> Path:
    return Path(os.environ["LOCALAPPDATA"]) / "Task1CodeAgent" / "live_key.dpapi"


def validate_key(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Enter an API key in the masked local field.")
    value = value.strip()
    if not 8 <= len(value) <= 512 or not value.isascii() or any(c.isspace() or ord(c) < 33 for c in value):
        raise ValueError("The API key format is invalid; check the local field.")
    return value


class _Blob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


def _crypt(raw: bytes, *, decrypt: bool) -> bytes:
    if os.name != "nt" or not raw or len(raw) > 8192:
        raise ValueError("Windows user-protected key storage is unavailable.")
    crypt = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    pointer = ctypes.POINTER(_Blob)
    crypt.CryptProtectData.argtypes = [pointer, wintypes.LPCWSTR, pointer, ctypes.c_void_p,
                                      ctypes.c_void_p, wintypes.DWORD, pointer]
    crypt.CryptProtectData.restype = wintypes.BOOL
    crypt.CryptUnprotectData.argtypes = [pointer, ctypes.c_void_p, pointer, ctypes.c_void_p,
                                        ctypes.c_void_p, wintypes.DWORD, pointer]
    crypt.CryptUnprotectData.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    buffer = (ctypes.c_ubyte * len(raw)).from_buffer_copy(raw)
    incoming, outgoing = _Blob(len(raw), buffer), _Blob()
    try:
        if decrypt:
            ok = crypt.CryptUnprotectData(ctypes.byref(incoming), None, None, None, None,
                                         1, ctypes.byref(outgoing))
        else:
            ok = crypt.CryptProtectData(ctypes.byref(incoming), PURPOSE, None, None, None,
                                       1, ctypes.byref(outgoing))
        if not ok:
            raise ValueError("The protected key could not be accessed by this Windows account.")
        return ctypes.string_at(outgoing.pbData, outgoing.cbData)
    finally:
        ctypes.memset(buffer, 0, len(raw))
        if outgoing.pbData:
            ctypes.memset(outgoing.pbData, 0, outgoing.cbData)
            kernel.LocalFree(ctypes.cast(outgoing.pbData, ctypes.c_void_p))


def save_key(value: str, path: Path | None = None) -> None:
    value = validate_key(value)
    protected = _crypt(json.dumps({"purpose": PURPOSE, "key": value}).encode("utf-8"), decrypt=False)
    destination = path or key_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".dpapi.tmp")
    temporary.write_bytes(protected)
    temporary.replace(destination)


def load_key(path: Path | None = None) -> str:
    try:
        source = path or key_path()
        if source.stat().st_size > 8192:
            raise ValueError("Protected key file is too large.")
        payload = json.loads(_crypt(source.read_bytes(), decrypt=True).decode("utf-8"))
        if payload.get("purpose") != PURPOSE:
            raise ValueError("Unexpected protected-key purpose.")
        return validate_key(payload["key"])
    except Exception:
        raise ValueError("No usable local key is configured. Use the masked setup window.") from None


def main():
    import tkinter as tk
    from tkinter import ttk
    root = tk.Tk()
    root.title("DeepSeek key setup — Task 1")
    root.geometry("660x350")
    root.minsize(620, 330)
    root.configure(bg="#10182a")
    frame = tk.Frame(root, bg="#10182a", padx=28, pady=24)
    frame.pack(fill="both", expand=True)
    tk.Label(frame, text="DeepSeek key setup", bg="#10182a", fg="#70e0c4",
             font=("Segoe UI", 21, "bold")).pack(anchor="w")
    tk.Label(frame, text="Paste your key here. Do not send it in chat.", bg="#10182a", fg="white",
             font=("Segoe UI", 12)).pack(anchor="w", pady=(12, 8))
    value = tk.StringVar()
    entry = ttk.Entry(frame, textvariable=value, show="●", font=("Segoe UI", 12))
    entry.pack(fill="x", pady=5)
    tk.Label(frame, text="Stored encrypted for your Windows account, outside the project.\n"
             "Used only for this project's official DeepSeek calls within the USD 1 cap.\n"
             "The encrypted handoff will be removed after the live task.",
             bg="#10182a", fg="#b5c3db", justify="left", font=("Segoe UI", 10)).pack(anchor="w", pady=12)
    status = tk.StringVar(value="Waiting for your local key. Saving does not send a paid request.")
    tk.Label(frame, textvariable=status, bg="#10182a", fg="#70e0c4", wraplength=590,
             justify="left", font=("Segoe UI", 10)).pack(anchor="w", pady=4)
    def submit():
        try:
            save_key(value.get())
            value.set("")
            entry.configure(state="disabled")
            button.configure(state="disabled")
            status.set("Key configured securely. Return to chat; the agent can continue.")
        except Exception:
            status.set("Could not save the key. Check the field and try again; no key was logged.")
    button = ttk.Button(frame, text="Use key for this project", command=submit)
    button.pack(anchor="w", pady=(10, 0))
    root.protocol("WM_DELETE_WINDOW", lambda: (value.set(""), root.destroy()))
    entry.focus_set()
    root.mainloop()


if __name__ == "__main__":
    main()
