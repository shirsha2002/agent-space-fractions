"""Validate a bounded file manifest before touching a fresh project directory."""
from __future__ import annotations

import json
import os
import re
import stat
from pathlib import Path, PurePosixPath


class ManifestError(ValueError):
    pass


REQUIRED = {"main.py", "game_core.py", "storage.py", "README.md", "requirements.txt"}
RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(10)),
            *(f"LPT{i}" for i in range(10))}
SUFFIXES = {".py", ".md", ".txt", ".json", ".csv", ".yaml", ".yml", ".proto", ".sql"}


def safe_path(name: str) -> str:
    if not isinstance(name, str) or not name or len(name) > 180:
        raise ManifestError("Invalid project filename")
    if "\\" in name or ":" in name or name.startswith("/") or "\x00" in name:
        raise ManifestError("Absolute, drive, UNC and backslash paths are forbidden")
    parts = name.split("/")
    if len(parts) > 8:
        raise ManifestError("Project path too deep")
    for part in parts:
        if (part in {"", ".", ".."} or part.endswith((" ", "."))
                or not re.fullmatch(r"[A-Za-z0-9_ .-]+", part)
                or part.split(".")[0].rstrip(" .").upper() in RESERVED):
            raise ManifestError("Unsafe or Windows-reserved path component")
    if PurePosixPath(name).suffix.lower() not in SUFFIXES:
        raise ManifestError("Unsupported file type")
    return name


def parse_manifest(content: str) -> dict:
    if not isinstance(content, str) or len(content.encode("utf-8")) > 800_000:
        raise ManifestError("Response exceeds the manifest size limit")
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ManifestError("Duplicate JSON object key")
            value[key] = item
        return value
    try:
        data = json.loads(content, object_pairs_hook=unique)
    except (ValueError, TypeError) as exc:
        raise ManifestError("Model response is not a complete JSON object") from exc
    if not isinstance(data, dict) or set(data) != {"project_name", "summary", "files"}:
        raise ManifestError("Expected project_name, summary, files only")
    if not isinstance(data["project_name"], str) or not 1 <= len(data["project_name"]) <= 80:
        raise ManifestError("Invalid project name")
    if not isinstance(data["summary"], str) or len(data["summary"]) > 4000:
        raise ManifestError("Invalid project summary")
    files = data["files"]
    if not isinstance(files, list) or not 6 <= len(files) <= 50:
        raise ManifestError("Expected between 6 and 50 complete project files")
    seen, total = set(), 0
    for item in files:
        if not isinstance(item, dict) or set(item) != {"path", "content"}:
            raise ManifestError("Each file needs path and content only")
        name = safe_path(item["path"])
        if name.casefold() in seen:
            raise ManifestError("Duplicate filename (case insensitive)")
        seen.add(name.casefold())
        if not isinstance(item["content"], str):
            raise ManifestError("File content must be text")
        size = len(item["content"].encode("utf-8"))
        if size > 180_000:
            raise ManifestError("A generated file is too large")
        total += size
    if total > 600_000:
        raise ManifestError("Project exceeds 600 KB")
    paths = {f["path"] for f in files}
    folded_paths = {name.casefold() for name in paths}
    for name in paths:
        parts = name.casefold().split("/")
        if any("/".join(parts[:i]) in folded_paths for i in range(1, len(parts))):
            raise ManifestError("A project file cannot also be a parent directory")
    if not REQUIRED <= paths or not any(p.startswith("tests/test_") and p.endswith(".py") for p in paths):
        raise ManifestError("Missing source, dependency manifest, README or tests")
    deps = next(f["content"] for f in files if f["path"] == "requirements.txt")
    if any(line.strip() and not line.lstrip().startswith("#") for line in deps.splitlines()):
        raise ManifestError("This runner supports standard-library-only projects; dependencies rejected")
    return data


def ensure_regular_tree(root: Path) -> None:
    """Reject junctions/reparse points as well as symbolic links, including ancestors."""
    root = Path(root).absolute()
    for part in [root, *root.parents]:
        if part.exists() or part.is_symlink():
            info = part.lstat()
            if part.is_symlink() or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                raise ManifestError("Linked/reparse output paths are forbidden")
    if root.exists():
        for current, directories, files in os.walk(root, followlinks=False):
            for name in directories + files:
                path = Path(current) / name
                info = path.lstat()
                if path.is_symlink() or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                    raise ManifestError("Output contains a linked/reparse entry")
                if not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):
                    raise ManifestError("Output contains a non-regular entry")


def materialize(root: Path, manifest: dict, *, repair: bool = False) -> None:
    # Revalidate even callers that constructed a dictionary directly.
    manifest = parse_manifest(json.dumps(manifest))
    root = Path(root).absolute()
    ensure_regular_tree(root)
    if root.exists() and any(root.iterdir()) and not repair:
        raise ManifestError("Output project is not empty")
    root.mkdir(parents=True, exist_ok=True)
    for item in manifest["files"]:
        target = root.joinpath(*item["path"].split("/"))
        if not target.resolve().is_relative_to(root.resolve()):
            raise ManifestError("Output escaped project directory")
        target.parent.mkdir(parents=True, exist_ok=True)
        ensure_regular_tree(root)
        # O_NOFOLLOW is unavailable on Windows. Reparse checks reduce risk but
        # cannot eliminate a concurrent same-user filesystem substitution.
        target.write_text(item["content"], encoding="utf-8", newline="\n")
