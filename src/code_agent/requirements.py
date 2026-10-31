"""Deterministic, evidence-linked input indexing; never a replacement for text.

This is a lightweight normalization pass, not a semantic completeness claim.
The original documents accompany every normalized request so the model can
inspect requirements that the index does not recognize.
"""

from __future__ import annotations

import re


def _evidence(source: dict, number: int, line: str) -> dict:
    return {"source": source["name"], "line": number, "text": line.strip()}


def normalize_inputs(bundle: dict) -> dict:
    """Return original sources plus a structured, line-referenced index."""
    sources = bundle.get("sources")
    if not isinstance(sources, list) or len(sources) != 2:
        raise ValueError("Normalization requires documentation and views.")
    indexed = [
        (source, number, line)
        for source in sources
        for number, line in enumerate(source["text"].splitlines(), start=1)
        if line.strip()
    ]

    def matching(pattern: str) -> list[dict]:
        return [
            _evidence(source, number, line)
            for source, number, line in indexed
            if re.search(pattern, line, re.IGNORECASE)
        ]

    def named(pattern: str) -> list[dict]:
        found: dict[str, dict] = {}
        for source, number, line in indexed:
            match = re.search(pattern, line)
            if match:
                name = match.group(1)
                if name not in found:
                    found[name] = {"name": name, "evidence": []}
                found[name]["evidence"].append(_evidence(source, number, line))
        return list(found.values())

    text = "\n".join(source["text"] for source in sources)
    conflicts: list[dict] = []
    if re.search(r"web-based|cloud-based|microservices", text, re.I):
        conflicts.append({
            "id": "desktop-vs-cloud",
            "source_evidence": matching(r"web-based|cloud-based|microservices"),
            "decision": "Provisional modular local desktop implementation; cloud topology remains unimplemented pending clarification.",
            "approved_by_professor": False,
        })
    if "check answer" in text and not re.search(r"\+\s*check", text):
        conflicts.append({
            "id": "question-check-contract",
            "source_evidence": matching(r"check answer|class Question"),
            "decision": "Add an explicit answer-checking method to complete the interaction contract.",
            "approved_by_professor": False,
        })
    if "99.99%" in text and re.search(r"Error budget:\s*1%", text):
        conflicts.append({
            "id": "slo-error-budget",
            "source_evidence": matching(r"99\.99%|Error budget"),
            "decision": "Record inconsistent source targets; make no production availability claim.",
            "approved_by_professor": False,
        })
    if "sql/question_ddl.sql" in text and "CREATE TABLE games" in text:
        conflicts.append({
            "id": "question-vs-game-schema",
            "source_evidence": matching(r"sql/question_ddl\.sql|CREATE TABLE games|sql/game_ddl\.sql"),
            "decision": "Document both source artifacts and request explicit question and score persistence in the desktop project.",
            "approved_by_professor": False,
        })

    return {
        "schema_version": 1,
        "normalization": "Deterministic index with full original source text retained; not a complete semantic parser.",
        "sources": sources,
        "purpose": matching(r"sixth-grade|learning tool|fraction-solving|Executive Summary"),
        "features": named(r'\busecase\s+"([^"]+)"'),
        "narrative_features": matching(r"introductory movie|main menu|ending scene|display result|submit answer"),
        "actors": named(r"^\s*actor\s+(\w+)"),
        "classes": named(r"^\s*class\s+(\w+)"),
        "components": named(r"(?:^\s*artifact\s+|^\s*\*\s*)(\w+Component)"),
        "states": named(r"^\s*state\s+(\w+)"),
        "state_transitions": matching(r"-->.*(?:pause\(|resume\(|gameOver\()"),
        "persistence": matching(r"persist|CREATE TABLE|PostgreSQL|replication|backup|data durability"),
        "interfaces": matching(r"RESTful|OAuth2|openapi:|rpc\s|service GameService|/play:|check answer|updateQuestions"),
        "constraints": matching(r"NFR-|ASR-|SLO:|Error budget:|RTO:|RPO:|1000 users|1 hour per session|security|authentication|authorization"),
        "artifacts": matching(r"architecture\.md|openapi\.yaml|internal\.proto|k8s/|sql/|traceability_matrix\.csv"),
        "source_sections": matching(r"^#{1,3}\s"),
        "conflicts": conflicts,
        "delivery_constraints": [
            {"requirement": "Windows desktop agent as a double-click executable without pre-installed Python.", "source": "Task1-EN.docx"},
            {"requirement": "Use official DeepSeek API and exact model deepseek-v4-pro.", "source": "Task1-EN.docx"},
            {"requirement": "Generated game has a desktop UI.", "source": "Professor follow-up email screenshot"},
            {"requirement": "Cumulative paid API cost conservatively limited to USD 1.", "source": "Professor follow-up email screenshot; cumulative scope is a provisional assumption"},
        ],
        "implementation_assumptions": [
            "Use a modular Python/Tkinter desktop target with local persistence as a provisional adaptation, not an approved cloud replacement.",
            "Use original multiple-choice fraction questions, exact rational comparison, one point per correct answer, and no duplicate scoring.",
            "Use an original short animated introduction with skip; no supplied movie asset exists.",
            "Keep player and administrator responsibilities separate; local password roles are not OAuth2.",
            "Do not claim 1000-user scalability, cloud high availability, or production SLO verification.",
        ],
    }
