"""Boundary and repair evidence using explicitly mocked diagnostic projects."""

from __future__ import annotations

from copy import deepcopy
import io
import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from threading import Event
import unittest
from unittest.mock import patch
import urllib.error

from code_agent.agent import CodeAgent, RunConfig
from code_agent.budget import BudgetLedger
from code_agent.model_client import DeepSeekClient
from code_agent.offline import OfflineClient, OfflineResult
from code_agent.validator import clean_environment, run_tests, startup_check, static_validate
from code_agent.workspace_tools import ManifestError, ensure_regular_tree, materialize, parse_manifest, safe_path


ROOT = Path(__file__).resolve().parents[1]
ARCHITECTURE = ROOT / "inputs" / "Architecture_Documentation.md"
VIEWS = ROOT / "inputs" / "Architecture_View.md"


def diagnostic():
    return json.loads(OfflineClient(broken_first=False).complete([]).content)


def replace_file(manifest, name, text):
    result = deepcopy(manifest)
    next(item for item in result["files"] if item["path"] == name)["content"] = text
    return result


class SequenceClient:
    def __init__(self, responses, during=None):
        self.responses = responses
        self.calls = 0
        self.messages = []
        self.during = during

    def complete(self, messages, **kwargs):
        self.messages.append(messages)
        item = self.responses[min(self.calls, len(self.responses) - 1)]
        self.calls += 1
        if self.during:
            self.during()
        return OfflineResult(item if isinstance(item, str) else json.dumps(item), {})


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_traversal_drives_unc_and_windows_names_rejected(self):
        for name in ("../escape.py", "/absolute.py", "C:/drive.py", "\\\\server\\share.py",
                     "nested\\backslash.py", "a/../../escape.py", "a//empty.py",
                     "a/./dot.py", "CON.py", "aux .md", "LPT1.txt", "file.py.",
                     "trailing /file.py", "a\x00.py", "script.ps1", "file.py:stream"):
            with self.subTest(name=name):
                with self.assertRaises(ManifestError):
                    safe_path(name)

    def test_case_duplicate_and_duplicate_json_keys_rejected(self):
        manifest = diagnostic()
        manifest["files"].append({"path": "MAIN.PY", "content": "pass\n"})
        with self.assertRaises(ManifestError):
            parse_manifest(json.dumps(manifest))
        with self.assertRaises(ManifestError):
            parse_manifest('{"project_name":"a","project_name":"b","summary":"s","files":[]}')

    def test_file_parent_collision_rejected_before_any_write(self):
        manifest = diagnostic()
        manifest["files"] += [{"path": "data.json", "content": "{}"},
                              {"path": "DATA.JSON/nested.py", "content": "pass"}]
        project = self.root / "project"
        with self.assertRaises(ManifestError):
            materialize(project, manifest)
        self.assertFalse(project.exists())

    def test_unrelated_output_preserved_and_dependencies_never_installed(self):
        project = self.root / "project"
        project.mkdir()
        (project / "keep.txt").write_text("unrelated work", encoding="utf-8")
        with self.assertRaises(ManifestError):
            materialize(project, diagnostic())
        self.assertEqual((project / "keep.txt").read_text(), "unrelated work")
        self.assertEqual(len(list(project.iterdir())), 1)
        manifest = replace_file(diagnostic(), "requirements.txt", "requests\n")
        with self.assertRaises(ManifestError):
            materialize(self.root / "other", manifest)
        self.assertFalse((self.root / "other").exists())

    def test_missing_tests_and_truncated_json_rejected(self):
        manifest = diagnostic()
        manifest["files"][-1] = {"path": "notes.md", "content": "No tests"}
        with self.assertRaises(ManifestError):
            parse_manifest(json.dumps(manifest))
        with self.assertRaises(ManifestError):
            parse_manifest(json.dumps(diagnostic())[:-8])

    def test_junction_escape_and_linked_output_ancestor_rejected(self):
        outside = self.root / "outside"
        project = self.root / "project"
        outside.mkdir()
        project.mkdir()
        link = project / "escape"
        if os.name == "nt":
            result = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(outside)],
                                    capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode:
                self.skipTest("This Windows account cannot create a test junction")
            self.addCleanup(lambda: link.rmdir() if link.exists() else None)
        else:
            link.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ManifestError):
            ensure_regular_tree(project)
        with self.assertRaises(ManifestError):
            materialize(link / "nested", diagnostic())
        self.assertEqual(list(outside.iterdir()), [])

    def test_static_validation_rejects_syntax_shell_and_third_party_imports(self):
        project = self.root / "project"
        materialize(project, diagnostic())
        for code in ("def broken(:\n", "import subprocess\n", "import requests\n",
                     "import os\nos.system('arbitrary command')\n"):
            with self.subTest(code=code):
                (project / "main.py").write_text(code, encoding="utf-8")
                self.assertFalse(static_validate(project)["ok"])

    def test_static_check_accepts_regex_compilation_and_list_removal(self):
        project = self.root / "project"
        materialize(project, diagnostic())
        (project / "main.py").write_text(
            "import re\nfrom re import compile as make_pattern\n"
            "pattern = re.compile(r'^[0-9]+/[0-9]+$')\n"
            "other = make_pattern(r'^[0-9]+$')\n"
            "questions = ['old', 'new']\nquestions.remove('old')\n",
            encoding="utf-8")
        result = static_validate(project)
        self.assertTrue(result["ok"], result["errors"])

    def test_static_check_rejects_process_and_file_deletion_import_aliases(self):
        project = self.root / "project"
        materialize(project, diagnostic())
        for code in (
            "import os as x\nx.system('arbitrary command')\n",
            "import os as x\nx.remove('file.txt')\n",
            "from os import system as run\nrun('arbitrary command')\n",
            "from os import remove as erase\nerase('file.txt')\n",
            "from os import *\nremove('file.txt')\n",
        ):
            with self.subTest(code=code):
                (project / "main.py").write_text(code, encoding="utf-8")
                self.assertFalse(static_validate(project)["ok"])

    def test_static_check_rejects_dynamic_execution_builtins_and_aliases(self):
        project = self.root / "project"
        materialize(project, diagnostic())
        for code in (
            "eval('1+1')\n", "exec('value=1')\n", "compile('x=1', 'x', 'exec')\n",
            "__import__('os')\n", "import builtins as b\nb.compile('x=1', 'x', 'exec')\n",
            "from builtins import eval as calculate\ncalculate('1+1')\n",
        ):
            with self.subTest(code=code):
                (project / "main.py").write_text(code, encoding="utf-8")
                self.assertFalse(static_validate(project)["ok"])

    def test_worker_cancellation_before_launch_and_environment_has_no_key(self):
        event = Event()
        event.set()
        with patch("code_agent.validator.subprocess.Popen") as popen:
            result = run_tests(self.root, event)
        popen.assert_not_called()
        self.assertFalse(result["ok"])
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "should-never-be-in-worker", "OTHER_SECRET": "private"}):
            env = clean_environment()
        self.assertNotIn("DEEPSEEK_API_KEY", env)
        self.assertNotIn("OTHER_SECRET", env)

    def test_worker_timeout_terminates_hanging_generated_tests(self):
        manifest = replace_file(diagnostic(), "tests/test_fixture.py", "while True:\n    pass\n")
        project = self.root / "project"
        materialize(project, manifest)
        result = run_tests(project, timeout=.3, contract=False)
        self.assertFalse(result["ok"])
        self.assertIn("timed out", str(result["errors"]))


class AgentLoopTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(prefix="agent spaces 测试-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def config(self, **kwargs):
        return RunConfig(ARCHITECTURE, VIEWS, self.root / "runs", offline=True, **kwargs)

    def test_real_worker_detects_mock_syntax_error_and_repair_passes(self):
        client = OfflineClient(broken_first=True)
        result = CodeAgent(client).run(self.config())
        self.assertEqual(result["status"], "offline_verified")
        self.assertEqual(client.calls, 2)
        self.assertEqual(result["repairs_used"], 1)
        self.assertTrue(result["validation"]["ok"])
        self.assertFalse(result["validation"]["independent_contract"])
        summary = json.loads((result["run_dir"] / "run_summary.json").read_text(encoding="utf8"))
        self.assertEqual(summary["mode"], "offline_mock")
        self.assertIn("Mocked diagnostic", " ".join(summary["limitations"]))

    def test_failed_runtime_test_is_repaired_then_checked_again(self):
        manifest = diagnostic()
        broken = replace_file(manifest, "game_core.py", "MARKER = 'wrong'\n")
        client = SequenceClient([broken, manifest])
        agent = CodeAgent(client)
        first = agent.run(self.config(max_repairs=1))
        self.assertEqual(first["status"], "review_required")
        self.assertEqual(client.calls, 2)
        self.assertIn("AssertionError", str(client.messages[1]))
        final = agent.verify()
        self.assertEqual(final["status"], "offline_verified")
        self.assertEqual(client.calls, 2)

    def test_repeated_failure_stops_at_configured_repair_bound(self):
        broken = replace_file(diagnostic(), "main.py", "def broken(:\n")
        client = SequenceClient([broken])
        result = CodeAgent(client).run(self.config(max_repairs=2))
        self.assertEqual(result["status"], "validation_failed")
        self.assertEqual(client.calls, 3)
        self.assertEqual(result["repairs_used"], 2)

    def test_source_review_can_trigger_repair_without_fabricating_test_failure(self):
        client = SequenceClient([diagnostic(), diagnostic()])
        agent = CodeAgent(client)
        first = agent.run(self.config(max_repairs=1))
        self.assertEqual(first["status"], "offline_verified")
        result = agent.verify(review_findings=["Improve the reviewed local fixture documentation."])
        self.assertEqual(result["status"], "review_required")
        self.assertEqual(client.calls, 2)
        evidence = json.loads((result["run_dir"] / "test_result_0.json").read_text())
        self.assertTrue(evidence["tests_ok"])
        self.assertFalse(evidence["review_ok"])
        self.assertFalse(evidence["ok"])
        self.assertIn("Improve the reviewed", str(client.messages[1]))

    def test_manual_patch_preserves_model_output_and_discloses_origin_without_calls(self):
        client = SequenceClient([diagnostic()])
        agent = CodeAgent(client)
        initial = agent.run(self.config(max_repairs=0))
        original = (initial["run_dir"] / "manifest_0.json").read_bytes()
        result = agent.apply_reviewed_patch({"README.md": "# OFFLINE fixture\nReviewed documentation correction.\n"},
                                             "Correct the diagnostic documentation without attributing the change to the model.")
        self.assertEqual(client.calls, 1)
        self.assertEqual(result["status"], "review_required")
        self.assertEqual((initial["run_dir"] / "manifest_0.json").read_bytes(), original)
        self.assertEqual(result["manual_adjustments"][0]["additional_model_calls"], 0)
        self.assertNotEqual(result["manual_adjustments"][0]["files"][0]["before_sha256"],
                            result["manual_adjustments"][0]["files"][0]["after_sha256"])
        self.assertEqual(agent.verify()["status"], "offline_verified")

    def test_cancellation_after_response_does_not_materialize_or_repair(self):
        event = Event()
        client = SequenceClient([diagnostic()], during=event.set)
        result = CodeAgent(client, cancel_event=event).run(self.config())
        self.assertEqual(result["status"], "cancelled")
        self.assertEqual(client.calls, 1)
        self.assertFalse(result["project_dir"].exists())

    def test_malformed_response_preserves_failure_report(self):
        result = CodeAgent(SequenceClient(['{"files": ['])).run(self.config())
        self.assertEqual(result["status"], "failed")
        self.assertFalse(result["project_dir"].exists())
        self.assertTrue((result["run_dir"] / "run_summary.json").is_file())

    def test_new_runs_do_not_overwrite_previous_project(self):
        first = CodeAgent(OfflineClient(False)).run(self.config())
        sentinel = first["project_dir"] / "README.md"
        sentinel.write_text("keep my first run", encoding="utf8")
        second = CodeAgent(OfflineClient(False)).run(self.config())
        self.assertNotEqual(first["project_dir"], second["project_dir"])
        self.assertEqual(sentinel.read_text(), "keep my first run")

    def test_added_unreviewed_test_is_rejected_before_worker_execution(self):
        agent = CodeAgent(OfflineClient(False))
        result = agent.run(self.config())
        injected = result["project_dir"] / "tests" / "test_unreviewed.py"
        injected.write_text("raise RuntimeError('unreviewed test must never execute')\n", encoding="utf8")
        with patch("code_agent.agent.run_tests") as worker:
            checked = agent.verify()
        worker.assert_not_called()
        self.assertEqual(checked["status"], "failed")
        self.assertIn("Unexpected", checked["error"])

    def test_edited_source_is_rejected_before_worker_execution(self):
        agent = CodeAgent(OfflineClient(False))
        result = agent.run(self.config())
        (result["project_dir"] / "game_core.py").write_text("MARKER='unreviewed edit'\n", encoding="utf8")
        with patch("code_agent.agent.run_tests") as worker:
            checked = agent.verify()
        worker.assert_not_called()
        self.assertEqual(checked["status"], "failed")
        self.assertIn("changed", checked["error"])

    def test_credential_is_not_written_in_failure_summary_logs_or_ledger(self):
        secret = "sk-UNIQUE-FAKE-CREDENTIAL-MUST-NEVER-APPEAR"
        class RejectingOpener:
            def open(self, *args, **kwargs):
                raise urllib.error.HTTPError("https://api.deepseek.com/chat/completions", 401,
                                             secret, {}, io.BytesIO(secret.encode()))
        ledger = BudgetLedger(self.root / "ledger.sqlite3")
        messages = []
        agent = CodeAgent(DeepSeekClient(secret, ledger, opener=RejectingOpener()), ledger, log=messages.append)
        config = self.config()
        config.offline = False
        result = agent.run(config)
        self.assertEqual(result["status"], "failed")
        evidence = "\n".join(path.read_text(encoding="utf8") for path in result["run_dir"].rglob("*.json"))
        self.assertNotIn(secret, evidence + str(messages) + json.dumps(ledger.export()))
        # A rejected key is refused before generation: no lock-up and nothing reserved.
        self.assertFalse(ledger.snapshot()["uncertain"])
        self.assertEqual(ledger.snapshot()["reserved_usd"], "0")

    def test_budget_preflight_stops_generation_before_any_mock_http_request(self):
        class NeverOpen:
            def open(self, *args, **kwargs):
                self.fail("Preflight must prevent this request")
        opener = NeverOpen()
        opener.fail = self.fail
        ledger = BudgetLedger(self.root / "ledger.sqlite3", cap_usd=".001")
        client = DeepSeekClient("sk-offline-test-not-real", ledger, opener=opener)
        config = self.config()
        config.offline = False
        result = CodeAgent(client, ledger).run(config)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(ledger.snapshot()["request_count"], 0)
        self.assertIn("budget", result["error"])


if __name__ == "__main__":
    unittest.main()


class StartupCheckTests(unittest.TestCase):
    """Logic tests never open the GUI; the startup check must catch launch crashes."""

    def project(self, folder, main):
        root = Path(folder) / "project"
        root.mkdir()
        (root / "main.py").write_text(main, encoding="utf-8")
        return root

    def test_window_that_crashes_on_launch_fails_with_traceback(self):
        with TemporaryDirectory() as folder:
            root = self.project(folder, "import tkinter as tk\nroot = tk.Tk()\n"
                                        "tk.Canvas(root).create_oval(0, 0, 9, 9, fill='#silver')\nroot.mainloop()\n")
            result = startup_check(root)
            self.assertFalse(result["ok"])
            self.assertIn("invalid color name", result["output"])

    def test_normal_window_opens_and_closes_by_itself(self):
        with TemporaryDirectory() as folder:
            root = self.project(folder, "import tkinter as tk\nroot = tk.Tk()\n"
                                        "tk.Label(root, text='ok').pack()\nroot.mainloop()\n")
            self.assertTrue(startup_check(root)["ok"])


class RepairPromptTests(unittest.TestCase):
    def test_host_contract_failure_ships_the_contract_source_to_the_repair(self):
        from code_agent.contracts import GAME_CONTRACT
        from code_agent.prompts import repair_messages
        manifest = {"project_name": "x", "summary": "x", "files": []}
        failure = "FAIL: test_score_once_and_states (independent_fraction_rules...) True is not false"
        content = repair_messages(manifest, failure, GAME_CONTRACT)[-1]["content"]
        self.assertIn("self.assertFalse(game.submit(\"2/3\"))", content)
        self.assertNotIn("independent_fraction_rules.py, read-only", repair_messages(manifest, "SyntaxError")[-1]["content"])


class StartupDialogTests(unittest.TestCase):
    def test_first_run_modal_dialog_is_not_reported_as_a_hang(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "project"
            root.mkdir()
            (root / "main.py").write_text(
                "import tkinter as tk\nfrom tkinter import simpledialog, messagebox\n"
                "root = tk.Tk()\nname = simpledialog.askstring('Setup', 'Admin name:', parent=root)\n"
                "messagebox.showinfo('Done', 'ok')\nroot.mainloop()\n", encoding="utf-8")
            self.assertTrue(startup_check(root)["ok"])


class LoadRunTests(unittest.TestCase):
    def test_a_patched_saved_run_loads_and_launch_guard_accepts_it(self):
        """A run patched on disk must be loadable instead of failing as 'changed since generation'."""
        from code_agent.agent import CodeAgent, RunConfig
        with TemporaryDirectory() as folder:
            base = Path(folder)
            agent = CodeAgent(OfflineClient(), BudgetLedger(base / "l.sqlite3"))
            inputs = Path(__file__).resolve().parents[1] / "inputs"
            config = RunConfig(inputs / "Architecture_Documentation.md", inputs / "Architecture_View.md", base / "out", offline=True)
            result = agent.run(config)
            summary_path = result["run_dir"] / "run_summary.json"
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            summary["mode"] = "live_deepseek"  # load_run only accepts live runs
            summary_path.write_text(json.dumps(summary), encoding="utf-8")
            loaded = CodeAgent(OfflineClient(), BudgetLedger(base / "l.sqlite3")).load_run(result["run_dir"], config)
            self.assertEqual(loaded["run_id"], result["run_id"])
