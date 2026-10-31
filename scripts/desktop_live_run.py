"""Operator-assisted live run through the real desktop UI, with no key arguments.

Only --authorized-live-run starts generation. Source review/validation remains a
separate operator action through run_live.py; this window displays saved results.
"""
import argparse
import json
from pathlib import Path
import sys
import tkinter as tk

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from code_agent.ui import AgentWindow
from code_agent.workspace_tools import parse_manifest
from local_key_setup import load_key


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authorized-live-run", action="store_true")
    args = parser.parse_args()
    if not args.authorized_live_run:
        parser.error("Explicit bounded live-run authorization is required")
    api_key = load_key()
    root = tk.Tk()
    window = AgentWindow(root)
    window.mode.set("live")
    window._mode()
    window.key.set(api_key)
    api_key = None
    window.authorization.set(True)
    window.tokens.set(24000)
    window.output.set(str(ROOT / "runs"))
    last_status = None

    def sync():
        nonlocal last_status
        if window.agent and window.agent.pending:
            pending = window.agent.pending
            run = pending["root"]
            (ROOT / "runs/active_live_run.json").write_text(json.dumps({
                "run_directory": str(run.relative_to(ROOT)), "mode": "live_deepseek"}), encoding="utf-8")
            if not window.busy and window.result:
                window.start_btn.configure(state="disabled")
                window.verify_btn.configure(state="disabled")
                try:
                    summary = json.loads((run / "run_summary.json").read_text(encoding="utf-8"))
                    state = (summary["status"], summary["repairs_used"])
                    if state != last_status:
                        manifest = parse_manifest((run / "manifest.json").read_text(encoding="utf-8"))
                        pending.update(manifest=manifest, repairs=summary["repairs_used"], requests=summary["requests"])
                        window.result = {**summary, "run_dir": run, "project_dir": run / "project"}
                        window.status.set(summary["status"].replace("_", " ").capitalize())
                        window.launch_btn.configure(state="normal" if summary["status"] == "tests_passed" else "disabled", text="Launch game")
                        if last_status is not None:
                            window._log("Reviewed validation result: " + summary["status"].replace("_", " "))
                        last_status = state
                except (OSError, ValueError, KeyError):
                    pass  # A summary may be in the middle of an atomic-sized write.
            window._budget()
        if root.winfo_exists():
            root.after(1000, sync)

    root.after(500, window._start)
    root.after(1000, sync)
    root.mainloop()


if __name__ == "__main__":
    main()
