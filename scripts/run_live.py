"""Operator CLI for the authorized live run; never accepts keys as arguments.

Generate first, inspect the source, then invoke verify with --reviewed-source.
Uses the same official client, cumulative ledger and orchestration as the GUI.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from code_agent.agent import CodeAgent, RunConfig, save_json
from code_agent.budget import BudgetLedger
from code_agent.input_loader import load_inputs
from code_agent.model_client import DeepSeekClient
from code_agent.requirements import normalize_inputs
from local_key_setup import load_key


def ledger():
    return BudgetLedger(Path(os.environ["LOCALAPPDATA"]) / "Task1CodeAgent" / "usage.sqlite3")


def client(book):
    return DeepSeekClient(os.getenv("DEEPSEEK_API_KEY") or load_key(), book)


def account_preflight(api):
    if not api.check_model_access():
        raise RuntimeError("The required deepseek-v4-pro model is unavailable for this account.")
    try:
        with api._request("https://api.deepseek.com/user/balance") as response:
            balance = api._read_json(response)
        if balance.get("is_available") is not True:
            raise ValueError()
        return {"required_model_access": True, "account_balance_available": True,
                "balance_info": [{k: row[k] for k in ("currency", "total_balance") if k in row}
                                 for row in balance.get("balance_infos", []) if isinstance(row, dict)]}
    except Exception:
        raise RuntimeError("Official account balance is unavailable; no paid generation was started.") from None


def restore(api, book, run_directory, *, allow_patch=False):
    root = Path(run_directory).resolve(strict=True)
    summary = json.loads((root / "run_summary.json").read_text(encoding="utf-8"))
    if summary.get("mode") != "live_deepseek" or summary.get("model") != "deepseek-v4-pro":
        raise ValueError("Verification requires a genuine live run.")
    if summary.get("status") != "review_required" and not (allow_patch and summary.get("status") in {"validation_failed", "tests_passed"}):
        raise ValueError("This run is not waiting for source review.")
    bundle = load_inputs(ROOT / "inputs/Architecture_Documentation.md", ROOT / "inputs/Architecture_View.md")
    if summary["inputs"] != [{k: s[k] for k in ("name", "sha256")} for s in bundle["sources"]]:
        raise ValueError("Original input hashes changed; review provenance before continuing.")
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    config = RunConfig(ROOT / "inputs/Architecture_Documentation.md", ROOT / "inputs/Architecture_View.md",
                       ROOT / "runs", max_repairs=summary["max_repairs"],
                       max_tokens=summary.get("max_output_tokens", 16000))
    agent = CodeAgent(api, book, log=lambda message: print(message, flush=True))
    agent.pending = {"id": summary["run_id"], "root": root, "project": root / "project",
                     "config": config, "bundle": bundle, "normalized": normalize_inputs(bundle),
                     "repairs": summary["repairs_used"], "requests": summary["requests"],
                     "started": summary["started_at"], "manifest": manifest}
    agent.pending["manual_adjustments"] = summary.get("manual_adjustments", [])
    return agent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["preflight", "generate", "verify", "patch"])
    parser.add_argument("--run-directory", type=Path)
    parser.add_argument("--reviewed-source", action="store_true")
    parser.add_argument("--review-findings-file", type=Path)
    parser.add_argument("--patch-file", type=Path)
    parser.add_argument("--reason")
    options = parser.parse_args()
    book = ledger()
    api = client(book)
    if options.action in {"preflight", "generate"}:
        check = account_preflight(api)
        print(json.dumps({"required_model_access": True, "account_balance_available": True,
                          "budget": book.snapshot()}), flush=True)
        if options.action == "preflight":
            return 0
        agent = CodeAgent(api, book, log=lambda message: print(message, flush=True))
        result = agent.run(RunConfig(ROOT / "inputs/Architecture_Documentation.md",
                                    ROOT / "inputs/Architecture_View.md", ROOT / "runs", max_tokens=24000))
        save_json(result["run_dir"] / "account_preflight_private.json", check)
    else:
        if not options.reviewed_source or not options.run_directory:
            raise ValueError("Inspect source first, then supply --run-directory and --reviewed-source.")
        agent = restore(api, book, options.run_directory, allow_patch=options.action == "patch")
        save_json(agent.pending["root"] / f"source_review_{agent.pending['repairs']}.json",
                  {"reviewer": "Codex acting for the project owner", "reviewed_manifest_round": agent.pending["repairs"],
                   "statement": "Source inspected before generated-code execution; process limits are not a sandbox."})
        if options.action == "patch":
            if not options.patch_file or not options.reason:
                raise ValueError("A reviewed patch file and reason are required")
            result = agent.apply_reviewed_patch(json.loads(options.patch_file.read_text(encoding="utf-8")), options.reason)
        else:
            findings = json.loads(options.review_findings_file.read_text(encoding="utf-8")) if options.review_findings_file else None
            result = agent.verify(review_findings=findings)
    print(json.dumps({"status": result["status"], "run_directory": str(result["run_dir"].relative_to(ROOT)),
                      "repairs_used": result["repairs_used"], "error": result["error"],
                      "budget": book.snapshot()}), flush=True)
    return 0 if result["status"] in {"review_required", "tests_passed"} else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, RuntimeError, OSError):
        # Never print a credential, response body, or private local path.
        if sys.stderr:
            print("Live operation could not proceed. Check local key/account setup and saved run evidence; no automatic retry was made.", file=sys.stderr)
        raise SystemExit(1)
