"""Responsive Tkinter desktop front end; network work stays off the UI thread."""
from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .agent import MAX_REPAIRS, CodeAgent, RunConfig
from .budget import BudgetLedger
from .model_client import DeepSeekClient, ModelError
from .offline import OfflineClient
from .validator import launch_project

BG, PANEL, FG, MUTED, ACCENT = "#0c1220", "#141e31", "#edf3ff", "#9eafcb", "#70e0c4"


def resource_root():
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))


class AgentWindow:
    def __init__(self, root):
        self.root = root
        root.title("Task 1 · Desktop Code Agent")
        root.geometry("1140x850")
        root.minsize(1020, 780)
        root.configure(bg=BG)
        self.events = queue.Queue()
        self.cancel = threading.Event()
        self.busy = False
        self.closing = False
        self.result = None
        self.agent = None
        data = Path(os.getenv("LOCALAPPDATA", str(Path.home()))) / "Task1CodeAgent"
        self.ledger = BudgetLedger(data / "usage.sqlite3")
        self.mode = tk.StringVar(value="offline")
        self.key = tk.StringVar(value=os.getenv("DEEPSEEK_API_KEY", ""))
        self.architecture = tk.StringVar(value=str(resource_root() / "inputs" / "Architecture_Documentation.md"))
        self.views = tk.StringVar(value=str(resource_root() / "inputs" / "Architecture_View.md"))
        self.output = tk.StringVar(value=str(Path.home() / "Documents" / "Task1Runs"))
        self.authorization = tk.BooleanVar(value=False)
        self.reviewed = tk.BooleanVar(value=False)
        self.repairs = tk.IntVar(value=MAX_REPAIRS)
        self.tokens = tk.IntVar(value=16000)
        self.status = tk.StringVar(value="Ready · offline mode")
        self.budget_text = tk.StringVar()
        self._style()
        self._build()
        self._budget()
        root.after(100, self._poll)
        root.protocol("WM_DELETE_WINDOW", self._close)

    def _style(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("TFrame", background=BG)
        s.configure("Card.TFrame", background=PANEL)
        s.configure("TLabel", background=BG, foreground=FG, font=("Segoe UI", 10))
        s.configure("Muted.TLabel", foreground=MUTED)
        s.configure("Title.TLabel", font=("Segoe UI", 26, "bold"))
        s.configure("Section.TLabel", font=("Segoe UI", 12, "bold"))
        s.configure("TButton", background="#263752", foreground=FG, padding=(12, 8), font=("Segoe UI", 10))
        s.map("TButton", background=[("active", "#355071"), ("disabled", "#1b2639")], foreground=[("disabled", "#6d7c94")])
        s.configure("Accent.TButton", background=ACCENT, foreground=BG, font=("Segoe UI", 10, "bold"))
        s.map("Accent.TButton", background=[("active", "#a3efdf"), ("disabled", "#2a4a4d")])
        s.configure("TEntry", fieldbackground="#1a2941", foreground=FG, insertcolor=FG, padding=7)
        s.configure("TRadiobutton", background=BG, foreground=FG, font=("Segoe UI", 10))
        s.map("TRadiobutton", background=[("active", BG)], foreground=[("disabled", MUTED)])
        s.configure("TCheckbutton", background=BG, foreground=MUTED, font=("Segoe UI", 9))
        s.map("TCheckbutton", background=[("active", BG)])
        s.configure("TSpinbox", fieldbackground="#1a2941", foreground=FG, arrowcolor=FG, padding=4)
        s.configure("Horizontal.TProgressbar", background=ACCENT, troughcolor=PANEL)

    def _build(self):
        outer = ttk.Frame(self.root, padding=26)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="DOCUMENTS → CODE → DESKTOP", foreground=ACCENT,
                  font=("Segoe UI", 10, "bold")).pack(anchor="w")
        ttk.Label(outer, text="Build from architecture.", style="Title.TLabel").pack(anchor="w", pady=(5, 4))
        ttk.Label(outer, text="Task 1 Code Agent   /   DeepSeek V4 Pro   /   Windows", style="Muted.TLabel").pack(anchor="w")
        modes = ttk.Frame(outer)
        modes.pack(fill="x", pady=(19, 14))
        self.offline_radio = ttk.Radiobutton(modes, text="Offline pipeline check", variable=self.mode, value="offline", command=self._mode)
        self.offline_radio.pack(side="left")
        self.live_radio = ttk.Radiobutton(modes, text="Live DeepSeek generation", variable=self.mode, value="live", command=self._mode)
        self.live_radio.pack(side="left", padx=22)
        self.mode_note = ttk.Label(outer, text="OFFLINE: mocked diagnostic only. No API call; no generated game claim.", foreground=ACCENT)
        self.mode_note.pack(anchor="w", pady=(0, 14))
        body = ttk.Frame(outer)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)
        setup = ttk.Frame(body)
        setup.grid(row=0, column=0, sticky="nsew", padx=(0, 24))
        ttk.Label(setup, text="01  Configure the run", style="Section.TLabel").pack(anchor="w", pady=(0, 10))
        self.entries = []
        self.browse_buttons = []
        self._field(setup, "Architecture documentation", self.architecture, "file")
        self._field(setup, "Architecture views / UML", self.views, "file")
        self._field(setup, "Output parent folder · each run gets a fresh folder", self.output, "folder")
        ttk.Label(setup, text="Official DeepSeek API key · session only", style="Muted.TLabel").pack(anchor="w", pady=(3, 5))
        keyrow = ttk.Frame(setup)
        keyrow.pack(fill="x", pady=(0, 8))
        self.key_entry = ttk.Entry(keyrow, textvariable=self.key, show="●")
        self.key_entry.pack(side="left", fill="x", expand=True)
        self.check_btn = ttk.Button(keyrow, text="Check model", command=self._check_access)
        self.check_btn.pack(side="left", padx=(8, 0))
        controls = ttk.Frame(setup)
        controls.pack(fill="x", pady=(4, 8))
        ttk.Label(controls, text="Output token cap", style="Muted.TLabel").pack(side="left")
        self.token_spin = ttk.Spinbox(controls, from_=1000, to=24000, increment=1000, width=7, textvariable=self.tokens)
        self.token_spin.pack(side="left", padx=(8, 16))
        ttk.Label(controls, text="Repairs", style="Muted.TLabel").pack(side="left")
        self.repair_spin = ttk.Spinbox(controls, from_=0, to=MAX_REPAIRS, width=3, textvariable=self.repairs)
        self.repair_spin.pack(side="left", padx=8)
        self.paid_check = ttk.Checkbutton(setup, text="I authorize paid calls within the cumulative USD 1 cap.", variable=self.authorization)
        self.paid_check.pack(anchor="w", pady=5)
        ttk.Label(setup, text="Conservative reservations use peak rates. Uncertain billing blocks retries.",
                  style="Muted.TLabel", wraplength=500, font=("Segoe UI", 9)).pack(anchor="w")
        actions = ttk.Frame(setup)
        actions.pack(fill="x", pady=(14, 10))
        self.start_btn = ttk.Button(actions, text="Run offline check", style="Accent.TButton", command=self._start)
        self.start_btn.pack(side="left")
        self.cancel_btn = ttk.Button(actions, text="Cancel", state="disabled", command=self._cancel)
        self.cancel_btn.pack(side="left", padx=8)
        ttk.Checkbutton(setup, text="I reviewed this run's source before executing it.", variable=self.reviewed).pack(anchor="w", pady=5)
        self.verify_btn = ttk.Button(setup, text="Validate & repair reviewed source", state="disabled", command=self._verify)
        self.verify_btn.pack(anchor="w", pady=5)
        ttk.Label(setup, text="Generated code runs as your user. Static checks and process limits are not a security sandbox. Review first; use a disposable Windows environment for untrusted output.",
                  style="Muted.TLabel", wraplength=500, font=("Segoe UI", 9)).pack(anchor="w", pady=(6, 0))
        activity = ttk.Frame(body)
        activity.grid(row=0, column=1, sticky="nsew")
        ttk.Label(activity, text="02  Follow the evidence", style="Section.TLabel").pack(anchor="w", pady=(0, 10))
        self.logs = tk.Text(activity, bg=PANEL, fg=FG, insertbackground=FG, relief="flat",
                            font=("Consolas", 10), wrap="word", padx=14, pady=14, state="disabled", width=38, height=18)
        self.logs.pack(fill="both", expand=True)
        self._log("Ready. Start with the offline check.\nA real generated game requires a funded official DeepSeek account.")
        ttk.Label(outer, textvariable=self.status, foreground=ACCENT, font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(16, 7))
        self.progress = ttk.Progressbar(outer, mode="indeterminate")
        self.progress.pack(fill="x")
        footer = ttk.Frame(outer)
        footer.pack(fill="x", pady=(12, 0))
        ttk.Label(footer, textvariable=self.budget_text, style="Muted.TLabel").pack(side="left")
        self.open_btn = ttk.Button(footer, text="Open run", state="disabled", command=self._open)
        self.open_btn.pack(side="right")
        self.launch_btn = ttk.Button(footer, text="Launch output", state="disabled", command=self._launch)
        self.launch_btn.pack(side="right", padx=8)
        self.load_btn = ttk.Button(footer, text="Load run", command=self._load)
        self.load_btn.pack(side="right")
        self._mode()

    def _field(self, parent, label, variable, kind):
        ttk.Label(parent, text=label, style="Muted.TLabel").pack(anchor="w", pady=(0, 5))
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=(0, 12))
        entry = ttk.Entry(row, textvariable=variable)
        entry.pack(side="left", fill="x", expand=True)
        button = ttk.Button(row, text="Browse", command=lambda: self._browse(variable, kind))
        button.pack(side="left", padx=(8, 0))
        self.entries.append(entry)
        self.browse_buttons.append(button)

    def _browse(self, variable, kind):
        value = filedialog.askdirectory() if kind == "folder" else filedialog.askopenfilename(filetypes=[("Markdown documents", "*.md")])
        if value:
            variable.set(value)

    def _mode(self):
        live = self.mode.get() == "live"
        self.mode_note.configure(text="LIVE: official deepseek-v4-pro. Source review precedes execution." if live else "OFFLINE: mocked diagnostic only. No API call; no generated game claim.")
        self.start_btn.configure(text="Generate project" if live else "Run offline check")
        for control in (self.key_entry, self.check_btn, self.paid_check):
            control.configure(state="normal" if live else "disabled")

    def _budget(self):
        overall = self.ledger.snapshot()
        latest = self.ledger.latest_run_id()
        run = self.ledger.snapshot(latest) if latest else overall
        self.budget_text.set(f"This run ${float(run['spent_usd']):.4f} / $1  ·  Reserved ${float(run['reserved_usd']):.4f}"
                             f"  ·  All runs ${float(overall['spent_usd']):.4f}  ·  {overall['tokens']['total_tokens']:,} tokens")

    def _log(self, text):
        self.logs.configure(state="normal")
        self.logs.insert("end", datetime.now().strftime("%H:%M:%S") + "  " + str(text) + "\n")
        self.logs.see("end")
        self.logs.configure(state="disabled")

    def _set_busy(self, busy):
        self.busy = busy
        for item in [self.start_btn, self.load_btn, self.offline_radio, self.live_radio, self.token_spin,
                     self.repair_spin, *self.entries, *self.browse_buttons]:
            item.configure(state="disabled" if busy else "normal")
        self.cancel_btn.configure(state="normal" if busy else "disabled")
        self.verify_btn.configure(state="disabled")
        self.launch_btn.configure(state="disabled")
        self.open_btn.configure(state="normal" if self.result else "disabled")
        if busy:
            self.check_btn.configure(state="disabled")
            self.progress.start(12)
        else:
            self.progress.stop()
            self._mode()

    def _background(self, operation):
        def target():
            try:
                self.events.put(("done", operation()))
            except Exception as exc:
                self.events.put(("error", str(exc)))
        self._set_busy(True)
        threading.Thread(target=target, daemon=False).start()

    def _start(self):
        offline = self.mode.get() == "offline"
        try:
            if not offline and not self.authorization.get():
                raise ValueError("Authorize the bounded paid run using the checkbox first.")
            self.cancel.clear()
            config = RunConfig(Path(self.architecture.get()), Path(self.views.get()), Path(self.output.get()),
                               offline=offline, max_tokens=int(self.tokens.get()), max_repairs=int(self.repairs.get()))
            client = OfflineClient() if offline else DeepSeekClient(self.key.get(), self.ledger)
            self.agent = CodeAgent(client, self.ledger, log=lambda message: self.events.put(("log", message)), cancel_event=self.cancel)
            self.result = None
            self.reviewed.set(False)
            self.status.set("Generating · offline mock" if offline else "Generating · official request in progress")
            self._background(lambda: self.agent.run(config))
        except (ValueError, RuntimeError) as exc:
            messagebox.showerror("Run configuration", str(exc))

    def _load(self):
        folder = filedialog.askdirectory(title="Select a run folder (run_\<id>)", initialdir=self.output.get())
        if not folder:
            return
        try:
            # Repairs of a loaded run need the key; loading and validating alone do not.
            client = DeepSeekClient(self.key.get(), self.ledger) if self.key.get().strip() else _NoKeyClient()
            config = RunConfig(Path(self.architecture.get()), Path(self.views.get()), Path(self.output.get()),
                               offline=False, max_tokens=int(self.tokens.get()), max_repairs=int(self.repairs.get()))
            self.agent = CodeAgent(client, self.ledger, log=lambda message: self.events.put(("log", message)), cancel_event=self.cancel)
            self.reviewed.set(False)
            self.status.set("Loading saved run")
            self._background(lambda: self.agent.load_run(Path(folder), config))
        except (ValueError, RuntimeError) as exc:
            messagebox.showerror("Load run", str(exc))

    def _check_access(self):
        try:
            client = DeepSeekClient(self.key.get(), self.ledger)
            self.status.set("Checking official model access · no completion requested")
            self._background(lambda: {"access_check": client.check_model_access()})
        except (ValueError, RuntimeError) as exc:
            messagebox.showerror("Model access", str(exc))

    def _verify(self):
        if not self.reviewed.get():
            messagebox.showinfo("Source review", "Open the run folder and review the generated source, then select the review checkbox.")
            return
        self.cancel.clear()
        self.reviewed.set(False)
        self.status.set("Validating reviewed project")
        self._background(self.agent.verify)

    def _cancel(self):
        self.cancel.set()
        self.status.set("Cancellation requested · in-flight request may finish or time out before stopping")
        self._log("Cancellation requested. Received usage will still be accounted for.")

    def _open(self):
        if self.result:
            os.startfile(str(self.result["run_dir"]))

    def _launch(self):
        if self.result and self.result["status"] in {"tests_passed", "offline_verified"}:
            try:
                self.agent.assert_unchanged()
                launch_project(self.result["project_dir"])
                self._log("Output launched using the bundled runner")
            except Exception:
                self._log("Launch refused: output may have changed. Review source and run tests again.")

    def _poll(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "log":
                    self._log(value)
                    continue
                self._set_busy(False)
                self._budget()
                if kind == "error":
                    self.status.set("Stopped · see diagnostic")
                    self._log(value)
                elif "access_check" in value:
                    self.status.set("Required model is accessible" if value["access_check"] else "Required model not found for this account")
                    self._log(self.status.get())
                else:
                    self.result = value
                    label = value["status"].replace("_", " ")
                    self.status.set(label.capitalize())
                    self._log(label + (" · " + value["error"] if value.get("error") else ""))
                    self.open_btn.configure(state="normal")
                    self.verify_btn.configure(state="normal" if value["status"] == "review_required" else "disabled")
                    success = value["status"] in {"tests_passed", "offline_verified"}
                    self.launch_btn.configure(state="normal" if success else "disabled",
                                              text="Launch diagnostic" if value["mode"] == "offline_mock" else "Launch game")
        except queue.Empty:
            pass
        if self.closing and not self.busy:
            self.key.set("")
            self.root.destroy()
            return
        self.root.after(100, self._poll)

    def _close(self):
        if self.busy:
            self.closing = True
            self._cancel()
        else:
            self.key.set("")
            self.root.destroy()


class _NoKeyClient:
    def complete(self, *args, **kwargs):
        raise ModelError("Enter the API key before a repair request.")


def main():
    root = tk.Tk()
    AgentWindow(root)
    root.mainloop()
