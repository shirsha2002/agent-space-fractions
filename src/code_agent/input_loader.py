"""Read the two architecture inputs without leaking local filesystem paths."""

from __future__ import annotations

import hashlib
from pathlib import Path

MAX_INPUT_BYTES = 200 * 1024


class InputError(ValueError):
    """An input is unavailable or unsuitable for a generation request."""


def _load(path: str | Path, role: str) -> dict:
    selected = Path(path)
    if selected.suffix.lower() != ".md":
        raise InputError(f"The {role} input must be a Markdown (.md) file.")
    try:
        if not selected.is_file():
            raise InputError(f"The {role} input is not a readable file.")
        with selected.open("rb") as stream:
            raw = stream.read(MAX_INPUT_BYTES + 1)
    except OSError:
        raise InputError(f"The {role} input could not be read.") from None
    if len(raw) > MAX_INPUT_BYTES:
        raise InputError(f"The {role} input exceeds the 200 KiB limit.")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise InputError(f"The {role} input must contain UTF-8 text.") from None
    if not text.strip():
        raise InputError(f"The {role} input is empty.")
    if "\x00" in text:
        raise InputError(f"The {role} input contains binary data.")
    return {
        "role": role,
        "name": selected.name,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "text": text,
    }


def load_inputs(architecture_path: str | Path, views_path: str | Path) -> dict:
    """Load documentation and UML views, retaining text and byte-level hashes.

    The result deliberately includes basenames rather than selected absolute
    paths. Original bytes remain untouched on disk. A UTF-8 BOM is accepted
    while the provenance hash still describes the exact original bytes.
    """
    try:
        same_file = Path(architecture_path).resolve() == Path(views_path).resolve()
    except OSError:
        same_file = False
    if same_file:
        raise InputError("Select two distinct files for documentation and views.")
    return {
        "schema_version": 1,
        "sources": [
            _load(architecture_path, "architecture"),
            _load(views_path, "views"),
        ],
    }
