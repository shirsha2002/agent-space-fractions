"""Bundled Python runner: target PCs do not need python on PATH.

This is a separate process with time/output limits, NOT a security sandbox.
"""
from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import runpy
import sys
import traceback
import types
import unittest

# Import runtime dependencies before project path insertion and ensure PyInstaller
# includes these common stdlib modules used by generated desktop projects.
import tkinter  # noqa: F401
import tkinter.ttk  # noqa: F401
import tkinter.messagebox  # noqa: F401
import sqlite3  # noqa: F401
import fractions  # noqa: F401
import decimal  # noqa: F401
import secrets  # noqa: F401
import hashlib  # noqa: F401
import datetime  # noqa: F401
import math  # noqa: F401
import random  # noqa: F401

from .contracts import GAME_CONTRACT


SMOKE_SECONDS = 2


class BoundedOutput(io.TextIOBase):
    def __init__(self):
        self.tail = ""

    def write(self, text):
        self.tail = (self.tail + str(text))[-24000:]
        return len(text)

    def flush(self):
        pass


def run(project: str, mode: str, report: str, contract: bool = True) -> int:
    root = Path(project).resolve(strict=True)
    destination = Path(report).resolve()
    stream = BoundedOutput()
    result = {"ok": False, "phase": mode, "errors": []}
    # Worker arguments are produced only by our launcher, never by model output.
    sys.path.insert(0, str(root))
    try:
        with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
            if mode == "run":
                runpy.run_path(str(root / "main.py"), run_name="__main__")
                result["ok"] = True
            elif mode == "smoke":
                # Startup check: run main.py as a user would, then close the window automatically.
                original = tkinter.Misc.mainloop

                def closing_mainloop(widget, n=0):
                    widget.after(SMOKE_SECONDS * 1000, widget.destroy)
                    original(widget, n)

                # First-run modal dialogs (e.g. admin setup) are normal, not a hang: close them too.
                original_wait = tkinter.Misc.wait_window

                def closing_wait(widget, window=None):
                    target = widget if window is None else window
                    widget.after(SMOKE_SECONDS * 1000, target.destroy)
                    original_wait(widget, window)

                boxes = {name: getattr(tkinter.messagebox, name) for name in
                         ("showinfo", "showwarning", "showerror", "askyesno", "askokcancel", "askquestion")}
                tkinter.Misc.mainloop = closing_mainloop
                tkinter.Misc.wait_window = closing_wait
                for name in boxes:
                    setattr(tkinter.messagebox, name, lambda *args, **kwargs: None)
                try:
                    runpy.run_path(str(root / "main.py"), run_name="__main__")
                finally:
                    tkinter.Misc.mainloop = original
                    tkinter.Misc.wait_window = original_wait
                    for name, function in boxes.items():
                        setattr(tkinter.messagebox, name, function)
                result["ok"] = True
            elif mode == "test":
                loader = unittest.TestLoader()
                suite = unittest.TestSuite()
                if contract:
                    module = types.ModuleType("independent_fraction_rules")
                    exec(compile(GAME_CONTRACT, "independent_fraction_rules.py", "exec"), module.__dict__)
                    suite.addTests(loader.loadTestsFromModule(module))
                suite.addTests(loader.discover(str(root / "tests"), pattern="test_*.py"))
                runner = unittest.TextTestRunner(stream=stream, verbosity=2)
                outcome = runner.run(suite)
                result.update(ok=outcome.wasSuccessful() and outcome.testsRun > 0,
                              tests_run=outcome.testsRun, failures=len(outcome.failures),
                              errors_count=len(outcome.errors), independent_contract=contract)
            else:
                raise ValueError("Unsupported worker operation")
    except BaseException as exc:
        stream.write(traceback.format_exc())
        result["errors"] = [type(exc).__name__ + ": worker execution failed"]
    result["output"] = stream.tail.replace(str(root), "<project>")
    destination.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return 0 if result["ok"] else 1
