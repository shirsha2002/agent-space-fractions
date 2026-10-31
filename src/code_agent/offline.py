"""Tiny diagnostic fixture: NOT a generated Space Fractions submission."""
import json
from dataclasses import dataclass


@dataclass
class OfflineResult:
    content: str
    usage: dict
    request_id: str = "offline-fixture"
    model: str = "OFFLINE MOCK (no API)"


class OfflineClient:
    def __init__(self, broken_first: bool = True):
        self.calls = 0
        self.broken_first = broken_first

    def complete(self, messages, max_tokens=16000, run_id="offline", cancel_event=None):
        self.calls += 1
        main = '''import tkinter as tk
def main():
    root = tk.Tk()
    root.title("OFFLINE diagnostic — not Space Fractions")
    root.geometry("660x320")
    root.configure(bg="#10182a")
    tk.Label(root, text="OFFLINE PIPELINE CHECK", bg="#10182a", fg="#68ddc0",
             font=("Segoe UI", 22, "bold")).pack(pady=40)
    tk.Label(root, text="This is a mocked diagnostic fixture.\\nNo DeepSeek call was made.\\nA real generated game is still required.",
             bg="#10182a", fg="white", font=("Segoe UI", 12)).pack()
    tk.Button(root, text="Close", command=root.destroy).pack(pady=25)
    root.mainloop()
if __name__ == "__main__": main()
'''
        if self.broken_first and self.calls == 1:
            main = "def broken(:\n"
        manifest = {"project_name": "Offline diagnostic", "summary": "OFFLINE MOCK: pipeline evidence only, not a game.",
                    "files": [
                        {"path": "main.py", "content": main},
                        {"path": "game_core.py", "content": "# Offline fixture: game rules not implemented.\nMARKER = 'offline'\n"},
                        {"path": "storage.py", "content": "# Diagnostic fixture; no persistence claims.\n"},
                        {"path": "requirements.txt", "content": "# Standard library only\n"},
                        {"path": "README.md", "content": "# OFFLINE MOCK\nThis diagnostic is not a generated game. No paid calls.\n"},
                        {"path": "tests/test_fixture.py", "content": "import unittest\nfrom game_core import MARKER\nclass Diagnostic(unittest.TestCase):\n    def test_marker(self): self.assertEqual(MARKER, 'offline')\n"}]}
        return OfflineResult(json.dumps(manifest), {})
