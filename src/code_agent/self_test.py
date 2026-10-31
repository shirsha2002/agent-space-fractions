"""Offline packaged-runtime check with machine-readable evidence."""
import json
from pathlib import Path
import sys
import tkinter as tk
from tkinter import ttk

from .agent import CodeAgent, RunConfig
from .offline import OfflineClient


def main(args):
    if len(args) != 3:
        return 2
    architecture, views, output = map(Path, args)
    result = CodeAgent(OfflineClient()).run(RunConfig(architecture, views, output, offline=True))
    try:
        window = tk.Tk()
        window.withdraw()
        ttk.Label(window, text="Bundled Tcl/Tk runtime check").pack()
        window.update_idletasks()
        window.destroy()
        result["tkinter_runtime"] = "passed"
    except Exception:
        result["tkinter_runtime"] = "failed"
        result["status"] = "runtime_failed"
    report = output / "self_test_result.json"
    report.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    if sys.stdout:
        print(json.dumps(result, indent=2, default=str))
    return 0 if result["status"] == "offline_verified" else 1
