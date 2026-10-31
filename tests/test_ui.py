"""Application-level Tk integration checks; no network or native input injection."""
import os
from pathlib import Path
import tempfile
import time
import tkinter as tk
import unittest
from unittest.mock import patch

from code_agent.ui import AgentWindow


class UIIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"LOCALAPPDATA": self.tmp.name})
        self.env.start()
        self.root = tk.Tk()
        self.root.withdraw()
        self.window = AgentWindow(self.root)
        self.window.output.set(str(Path(self.tmp.name) / "runs"))

    def tearDown(self):
        self.root.destroy()
        self.env.stop()
        self.tmp.cleanup()

    def pump(self, done, timeout=8):
        deadline = time.monotonic() + timeout
        while not done() and time.monotonic() < deadline:
            self.root.update()
            time.sleep(.01)
        self.root.update()
        self.assertTrue(done(), "UI work did not finish within bounded time")

    def test_offline_flow_keeps_event_loop_alive_and_labels_output(self):
        heartbeat = []
        self.root.after(1, lambda: heartbeat.append(True))
        with patch("code_agent.ui.DeepSeekClient") as network:
            self.window._start()
            self.assertTrue(self.window.busy)
            self.pump(lambda: not self.window.busy)
            network.assert_not_called()
        self.assertTrue(heartbeat)
        self.assertEqual(self.window.result["status"], "offline_verified")
        self.assertEqual(self.window.launch_btn.cget("text"), "Launch diagnostic")
        self.assertEqual(self.window.ledger.snapshot()["request_count"], 0)

    def test_live_authorization_missing_blocks_client_construction(self):
        self.window.mode.set("live")
        with patch("code_agent.ui.messagebox.showerror") as error, patch("code_agent.ui.DeepSeekClient") as client:
            self.window._start()
            error.assert_called_once()
            client.assert_not_called()
        self.assertFalse(self.window.busy)

    def test_review_gate_blocks_execution(self):
        with patch("code_agent.ui.messagebox.showinfo") as notice, patch("code_agent.ui.CodeAgent.verify") as verify:
            self.window._verify()
            notice.assert_called_once()
            verify.assert_not_called()


if __name__ == "__main__":
    unittest.main()
