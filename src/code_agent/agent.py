"""Plan -> generate -> materialize -> check -> bounded repair -> evidence."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import threading
import uuid

from .input_loader import load_inputs
from .requirements import normalize_inputs
from .prompts import generation_messages, repair_messages
from .workspace_tools import parse_manifest, materialize, ensure_regular_tree
from .contracts import GAME_CONTRACT
from .validator import static_validate, run_tests, startup_check


@dataclass
class RunConfig:
    architecture: Path
    views: Path
    output: Path
    offline: bool = False
    max_tokens: int = 16000
    max_repairs: int = 2


def save_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class CodeAgent:
    def __init__(self, client, ledger=None, log=None, cancel_event=None):
        self.client, self.ledger = client, ledger
        self.log = log or (lambda text: None)
        self.cancel_event = cancel_event or threading.Event()
        self.pending = None

    def _check_cancel(self):
        if self.cancel_event.is_set():
            raise InterruptedError("Run cancelled; completed output is preserved")

    def _summary(self, status, validation=None, error=None):
        p = self.pending
        if error:
            for private in (str(p["root"].absolute()), str(p["config"].output.absolute()),
                            str(p["config"].architecture.absolute()), str(p["config"].views.absolute()),
                            str(Path.home())):
                error = error.replace(private, "<local-path>")
        p["status"] = status
        summary = {"schema_version": 1, "run_id": p["id"], "mode": "offline_mock" if p["config"].offline else "live_deepseek",
                   "status": status, "model": "OFFLINE MOCK" if p["config"].offline else "deepseek-v4-pro",
                   "started_at": p["started"], "updated_at": datetime.now(timezone.utc).isoformat(),
                   "repairs_used": p["repairs"], "max_repairs": p["config"].max_repairs,
                   "max_output_tokens": p["config"].max_tokens,
                   "validation": validation, "error": error,
                   "inputs": [{k: s[k] for k in ("name", "sha256")} for s in p["bundle"]["sources"]],
                   "files": [{"path": f["path"], "sha256": hashlib.sha256(f["content"].encode()).hexdigest()}
                             for f in p.get("manifest", {}).get("files", [])],
                   "requests": p["requests"], "budget": self.ledger.snapshot() if self.ledger else None,
                   "manual_adjustments": p.get("manual_adjustments", []),
                   "limitations": ["Separate process and static checks are not a security sandbox.",
                                   "Cloud deployment/OAuth2 remain unimplemented in the desktop adaptation.",
                                   "Clean Windows without Python must be tested separately."]}
        if p["config"].offline:
            summary["limitations"].insert(0, "Mocked diagnostic only: no real generation or game claim.")
        save_json(p["root"] / "run_summary.json", summary)
        return {**summary, "run_dir": p["root"], "project_dir": p["project"]}

    def _complete(self, messages):
        self._check_cancel()
        p = self.pending
        self.log("Requesting full project JSON" if not p["requests"] else "Requesting bounded repair")
        response = self.client.complete(messages, max_tokens=p["config"].max_tokens,
                                        run_id=p["id"], cancel_event=self.cancel_event)
        p["requests"].append({"request_id": response.request_id, "usage": response.usage,
                              "model": response.model})
        self._check_cancel()
        return parse_manifest(response.content)

    def _write(self, manifest):
        p = self.pending
        previous = p.get("manifest")
        if previous and not {f["path"] for f in previous["files"]} <= {f["path"] for f in manifest["files"]}:
            raise ValueError("Repair cannot silently delete existing project files")
        materialize(p["project"], manifest, repair=previous is not None)
        p["manifest"] = manifest
        save_json(p["root"] / f"manifest_{p['repairs']}.json", manifest)
        save_json(p["root"] / "manifest.json", manifest)

    def _repair(self, errors):
        p = self.pending
        if p["repairs"] >= p["config"].max_repairs:
            return False
        self._check_cancel()
        p["repairs"] += 1
        self.log(f"Repair {p['repairs']}/{p['config'].max_repairs}")
        report = json.dumps(errors)
        contract = GAME_CONTRACT if "independent_fraction_rules" in report else None
        self._write(self._complete(repair_messages(p["manifest"], report, contract)))
        return True

    def _static(self):
        while True:
            self._check_cancel()
            check = static_validate(self.pending["project"])
            save_json(self.pending["root"] / "static_result.json", check)
            save_json(self.pending["root"] / f"static_result_{self.pending['repairs']}.json", check)
            if check["ok"]:
                self.log(f"Static check passed ({check['python_files']} Python files)")
                return check
            self.log("Static check found issues; retaining diagnostics")
            if not self._repair(check):
                return check

    def run(self, config: RunConfig) -> dict:
        if not 0 <= config.max_repairs <= 2 or not 1000 <= config.max_tokens <= 24000:
            raise ValueError("Repairs must be 0–2 and output cap 1000–24000 tokens")
        bundle = load_inputs(config.architecture, config.views)
        normalized = normalize_inputs(bundle)
        ensure_regular_tree(config.output)
        config.output.mkdir(parents=True, exist_ok=True)
        ident = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:8]
        root = config.output / ("offline_" if config.offline else "run_") / ident
        root.mkdir(parents=True, exist_ok=False)
        self.pending = {"id": ident, "root": root, "project": root / "project", "config": config,
                        "bundle": bundle, "normalized": normalized, "repairs": 0, "requests": [],
                        "started": datetime.now(timezone.utc).isoformat()}
        save_json(root / "normalized_requirements.json", normalized)
        self._summary("generating")
        self.log("Both inputs loaded, hashed and normalized")
        try:
            self._write(self._complete(generation_messages(normalized)))
            check = self._static()
            if not check["ok"]:
                return self._summary("validation_failed", check)
            if config.offline:
                return self.verify()
            self.log("Source ready. Review it before running generated tests.")
            return self._summary("review_required", check)
        except Exception as exc:
            return self._summary("cancelled" if self.cancel_event.is_set() else "failed", error=str(exc))

    def verify(self, review_findings: list[str] | None = None) -> dict:
        """Called after the human reviews source; changed repairs need review again."""
        if not self.pending or "manifest" not in self.pending:
            raise ValueError("Generate a project first")
        p = self.pending
        try:
            if review_findings is not None and (not isinstance(review_findings, list)
                    or len(review_findings) > 20 or any(not isinstance(item, str) or len(item) > 1500 for item in review_findings)):
                raise ValueError("Review findings exceed the supported bounded format")
            self._check_cancel()
            self.assert_unchanged()
            check = static_validate(p["project"])
            if not check["ok"]:
                return self._summary("validation_failed", check)
            self.log("Running bounded tests in the bundled worker")
            result = run_tests(p["project"], self.cancel_event, contract=not p["config"].offline)
            if result["ok"] and not p["config"].offline:
                self.log("Tests passed; opening the generated app briefly to check startup")
                startup = startup_check(p["project"], self.cancel_event)
                if not startup["ok"]:
                    self.log("Startup check failed: the app crashed or hung when opened")
                    result = {**startup, "tests_run": result.get("tests_run"), "tests_passed_before_startup": True}
            if review_findings:
                result["tests_ok"] = result["ok"]
                result["review_findings"] = review_findings
                result["review_ok"] = False
                result["ok"] = False
            save_json(p["root"] / "test_result.json", result)
            save_json(p["root"] / f"test_result_{p['repairs']}.json", result)
            self._check_cancel()
            if result["ok"]:
                self.assert_unchanged()
                status = "offline_verified" if p["config"].offline else "tests_passed"
                self.log("OFFLINE diagnostic passed — real game still required" if p["config"].offline else "Generated and independent game tests passed")
                return self._summary(status, result)
            if self._repair(result):
                check = self._static()
                if check["ok"]:
                    self.log("Repaired source is ready for another review")
                    return self._summary("review_required", check)
            return self._summary("validation_failed", result)
        except Exception as exc:
            return self._summary("cancelled" if self.cancel_event.is_set() else "failed", error=str(exc))

    def assert_unchanged(self):
        """Keep the reviewed manifest, tested files and launch evidence consistent."""
        if not self.pending or "manifest" not in self.pending:
            raise ValueError("No generated manifest is available")
        p = self.pending
        ensure_regular_tree(p["project"])
        expected = {f["path"] for f in p["manifest"]["files"]}
        actual = {path.relative_to(p["project"]).as_posix() for path in p["project"].rglob("*") if path.is_file()}
        if expected != actual:
            raise ValueError("Unexpected or missing files: source must match the reviewed manifest")
        for item in p["manifest"]["files"]:
            if (p["project"] / item["path"]).read_text(encoding="utf-8") != item["content"]:
                raise ValueError("Project changed since generation; regenerate or review changes separately")

    def apply_reviewed_patch(self, patches: dict[str, str], reason: str) -> dict:
        """Apply disclosed operator edits without another model call or hiding its output."""
        if (not isinstance(patches, dict) or not 1 <= len(patches) <= 10 or
                not isinstance(reason, str) or not 1 <= len(reason) <= 2000):
            raise ValueError("A bounded patch and an explicit review reason are required")
        self.assert_unchanged()
        p = self.pending
        previous = p["manifest"]
        updated = json.loads(json.dumps(previous))
        files = {item["path"]: item for item in updated["files"]}
        changes = []
        for path, content in patches.items():
            if not isinstance(content, str):
                raise ValueError("Reviewed patch content must be text")
            before = files.get(path, {}).get("content")
            changes.append({"path": path, "before_sha256": hashlib.sha256(before.encode()).hexdigest() if before is not None else None,
                            "after_sha256": hashlib.sha256(content.encode()).hexdigest()})
            if path in files:
                files[path]["content"] = content
            else:
                updated["files"].append({"path": path, "content": content})
        updated = parse_manifest(json.dumps(updated))
        number = len(p.get("manual_adjustments", [])) + 1
        record = {"revision": number, "reviewer": "Operator (AI-assisted) acting for the project owner",
                  "timestamp_utc": datetime.now(timezone.utc).isoformat(), "reason": reason, "files": changes,
                  "additional_model_calls": 0}
        save_json(p["root"] / f"manual_patch_{number}_before.json", previous)
        materialize(p["project"], updated, repair=True)
        p["manifest"] = updated
        p.setdefault("manual_adjustments", []).append(record)
        save_json(p["root"] / f"manual_patch_{number}.json", record)
        save_json(p["root"] / f"manifest_manual_{number}.json", updated)
        save_json(p["root"] / "manifest.json", updated)
        return self._summary("review_required", static_validate(p["project"]))
