"""Heuristic static checks followed by explicitly requested bounded execution.

Import aliases are resolved for common dangerous calls. This is not a security
sandbox or full control-flow analysis; source review remains necessary.
"""
from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time

from .workspace_tools import ensure_regular_tree

DENIED_IMPORTS = {"subprocess", "ctypes", "socket", "urllib", "http", "ftplib",
                 "requests", "winreg", "importlib", "pickle", "marshal", "multiprocessing"}
DENIED_BUILTINS = {"eval", "exec", "__import__", "compile"}
DENIED_METHODS = {"system", "popen", "spawnl", "spawnv", "unlink", "rmdir", "rmtree", "chmod", "chown"}


def _import_aliases(tree: ast.AST) -> dict[str, str]:
    """Resolve explicit import spellings without claiming dynamic alias analysis."""
    aliases = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                aliases[alias.asname or alias.name.split(".")[0]] = alias.name if alias.asname else alias.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            for alias in node.names:
                if alias.name != "*":
                    aliases[alias.asname or alias.name] = node.module + "." + alias.name
    return aliases


def _call_name(node: ast.AST, aliases: dict[str, str]) -> str:
    if isinstance(node, ast.Name):
        return aliases.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        prefix = _call_name(node.value, aliases)
        return prefix + "." + node.attr if prefix else node.attr
    return ""


def _denied_call(symbol: str) -> bool:
    if symbol in DENIED_BUILTINS or symbol in {"builtins." + name for name in DENIED_BUILTINS}:
        return True
    # Keep destructive/process methods blocked, while allowing re.compile and
    # list.remove. Imported OS functions are recognized through their aliases.
    if symbol.rsplit(".", 1)[-1] in DENIED_METHODS:
        return True
    return symbol.startswith("os.") and symbol.rsplit(".", 1)[-1] == "remove"


def static_validate(project: Path) -> dict:
    errors = []
    ensure_regular_tree(project)
    sources = list(project.rglob("*.py"))
    local = {p.stem for p in sources} | {p.parent.name for p in sources}
    for path in sources:
        name = path.relative_to(project).as_posix()
        try:
            if path.stat().st_size > 180000:
                raise ValueError("Source file exceeds size limit")
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=name)
            aliases = _import_aliases(tree)
            for node in ast.walk(tree):
                imports = []
                if isinstance(node, ast.Import):
                    imports = [alias.name.split(".")[0] for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports = [node.module.split(".")[0]]
                    for alias in node.names:
                        symbol = node.module + "." + alias.name
                        if (not node.level and _denied_call(symbol)) or (
                            alias.name == "*" and node.module in {"os", "builtins", "shutil"}
                        ):
                            errors.append(f"{name}:{node.lineno}: disallowed import {symbol}")
                for module in imports:
                    if module in DENIED_IMPORTS or (module not in sys.stdlib_module_names and module not in local):
                        errors.append(f"{name}:{node.lineno}: unsupported import {module}")
                if isinstance(node, ast.Call):
                    called = _call_name(node.func, aliases)
                    if _denied_call(called):
                        errors.append(f"{name}:{node.lineno}: disallowed call {called}")
        except (SyntaxError, UnicodeError, ValueError) as exc:
            line = getattr(exc, "lineno", 0)
            detail = getattr(exc, "msg", type(exc).__name__)
            errors.append(f"{name}:{line}: {detail}")
    return {"ok": not errors, "phase": "static", "python_files": len(sources), "errors": errors}


def worker_command(project: Path, mode: str, report: Path, *, contract: bool = True) -> list[str]:
    args = ["--worker", str(project.resolve()), mode, str(report.resolve())]
    if not contract:
        args += ["--no-contract"]
    if getattr(sys, "frozen", False):
        return [sys.executable, *args]
    return [sys.executable, str(Path(__file__).resolve().parents[2] / "launcher.py"), *args]


def clean_environment() -> dict:
    allowed = {"SYSTEMROOT", "WINDIR", "TEMP", "TMP", "LOCALAPPDATA", "APPDATA", "USERPROFILE", "LANG"}
    env = {k: v for k, v in os.environ.items() if k.upper() in allowed}
    env.update(PYTHONIOENCODING="utf-8", PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1")
    return env


def run_tests(project: Path, cancel_event: threading.Event | None = None,
              *, timeout: float = 30, contract: bool = True) -> dict:
    if cancel_event and cancel_event.is_set():
        return {"ok": False, "phase": "tests", "errors": ["Cancelled before test execution"]}
    if not isinstance(timeout, (int, float)) or not 0 < timeout <= 300:
        return {"ok": False, "phase": "tests", "errors": ["Invalid test timeout"]}
    ensure_regular_tree(project)
    with tempfile.TemporaryDirectory(prefix="code-agent-check-") as tmp:
        report = Path(tmp) / "result.json"
        process = subprocess.Popen(worker_command(project, "test", report, contract=contract),
                                   cwd=project, env=clean_environment(), stdin=subprocess.DEVNULL,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        began = time.monotonic()
        while process.poll() is None:
            if (cancel_event and cancel_event.is_set()) or time.monotonic() - began > timeout:
                process.kill()
                process.wait(timeout=5)
                return {"ok": False, "phase": "tests", "errors": [
                    "Cancelled" if cancel_event and cancel_event.is_set() else "Test execution timed out"]}
            time.sleep(.05)
        if not report.exists() or report.stat().st_size > 100_000:
            return {"ok": False, "phase": "tests", "errors": ["Worker returned no valid bounded report"]}
        try:
            result = json.loads(report.read_text(encoding="utf-8"))
            if (not isinstance(result, dict) or not isinstance(result.get("ok"), bool)
                    or result.get("phase") != "test" or not isinstance(result.get("errors"), list)
                    or not isinstance(result.get("output"), str)
                    or (result["ok"] and (type(result.get("tests_run")) is not int or result["tests_run"] < 1))):
                raise ValueError("Invalid worker result schema")
            if process.returncode != 0:
                result["ok"] = False
            return result
        except (ValueError, OSError):
            return {"ok": False, "phase": "tests", "errors": ["Invalid worker report"]}


def launch_project(project: Path) -> subprocess.Popen:
    ensure_regular_tree(project)
    report = project.parent / "launch_result.json"
    return subprocess.Popen(worker_command(project, "run", report), cwd=project,
                            env=clean_environment(), stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
