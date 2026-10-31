"""Input handling tests; no network calls or generated code execution."""

import hashlib
from pathlib import Path
import tempfile
import unittest

from code_agent.input_loader import InputError, MAX_INPUT_BYTES, load_inputs
from code_agent.requirements import normalize_inputs


class InputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.a = self.root / "Architecture_Documentation.md"
        self.v = self.root / "Architecture_View.md"
        self.a.write_text("# Architecture\nA sixth-grade learning tool.\nOAuth2 authentication and PostgreSQL persistence.\n", encoding="utf8")
        self.v.write_text('actor EndUser\nusecase "Play Game" as (Play)\nclass Question {\n}\nstate Playing\nstate Paused\nPlaying --> Paused : pause()\n', encoding="utf8")

    def test_preserves_text_hash_and_hides_parent_path(self):
        bundle = load_inputs(self.a, self.v)
        self.assertEqual(bundle["sources"][0]["text"], self.a.read_bytes().decode("utf8"))
        self.assertEqual(bundle["sources"][0]["sha256"], hashlib.sha256(self.a.read_bytes()).hexdigest())
        self.assertNotIn(str(self.root), str(bundle))

    def test_normalized_evidence_keeps_sources_and_requirements(self):
        result = normalize_inputs(load_inputs(self.a, self.v))
        self.assertEqual(result["features"][0]["name"], "Play Game")
        self.assertEqual(result["features"][0]["evidence"][0]["line"], 2)
        self.assertEqual([x["name"] for x in result["states"]], ["Playing", "Paused"])
        self.assertTrue(result["interfaces"])
        self.assertTrue(result["persistence"])
        self.assertIn("OAuth2", result["sources"][0]["text"])
        self.assertIn("deepseek-v4-pro", str(result["delivery_constraints"]))

    def test_empty_invalid_utf8_oversize_and_binary_rejected(self):
        for content in [b" \n", b"\xff", b"x" * (MAX_INPUT_BYTES + 1), b"a\x00b"]:
            with self.subTest(content_size=len(content)):
                self.a.write_bytes(content)
                with self.assertRaises(InputError):
                    load_inputs(self.a, self.v)

    def test_missing_wrong_extension_and_identical_paths_rejected(self):
        for path in [self.root / "missing.md", self.root / "source.txt", self.v]:
            with self.subTest(path=path.name):
                with self.assertRaises(InputError):
                    load_inputs(path, self.v)

    def test_utf8_bom_and_original_source_conflicts(self):
        self.a.write_bytes(b"\xef\xbb\xbfweb-based microservices cloud-based\nSLO: 99.99% uptime\nError budget: 1%\nsql/question_ddl.sql\nCREATE TABLE games (\n")
        self.v.write_text("class Question {\n}\nGame->>Question: check answer\n", encoding="utf8")
        result = normalize_inputs(load_inputs(self.a, self.v))
        self.assertFalse(result["sources"][0]["text"].startswith("\ufeff"))
        self.assertEqual({x["id"] for x in result["conflicts"]}, {"desktop-vs-cloud", "question-check-contract", "slo-error-budget", "question-vs-game-schema"})

    def test_supplied_sources_all_views_retained(self):
        root = Path(__file__).resolve().parents[1]
        result = normalize_inputs(load_inputs(root / "inputs/Architecture_Documentation.md", root / "inputs/Architecture_View.md"))
        original = result["sources"][1]["text"]
        self.assertEqual(original.count("@startuml"), 13)
        self.assertEqual(len(result["components"]), 4)
        self.assertEqual({x["name"] for x in result["classes"]}, {"Game", "Question", "User", "Admin"})
        self.assertEqual({x["name"] for x in result["features"]}, {"Play Game", "View Score", "Update Questions", "View Help"})


if __name__ == "__main__":
    unittest.main()
