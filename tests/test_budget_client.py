"""Offline evidence only: every HTTP response below is a local mock."""

from __future__ import annotations

from decimal import Decimal
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
import unittest
import unittest.mock
import urllib.error

from code_agent.budget import BudgetError, BudgetLedger, Pricing, normalize_usage
from code_agent.model_client import API_URL, CancelledError, DeepSeekClient, ModelError


MESSAGES = [{"role": "system", "content": "Return a JSON object."},
            {"role": "user", "content": "Create a desktop project."}]
USAGE = {"prompt_tokens": 100, "prompt_cache_hit_tokens": 40,
         "prompt_cache_miss_tokens": 60, "completion_tokens": 200,
         "completion_tokens_details": {"reasoning_tokens": 80}, "total_tokens": 300}


def completion(**changes):
    obj = {"id": "chatcmpl-offline-test", "model": "deepseek-v4-pro",
           "usage": dict(USAGE), "choices": [{"finish_reason": "stop", "message": {"content": '{"files": []}'}}]}
    obj.update(changes)
    return obj


class FakeResponse(io.BytesIO):
    def __init__(self, data):
        super().__init__(json.dumps(data).encode("utf-8"))


class FakeOpener:
    def __init__(self, value=None, error=None, during=None):
        self.value = completion() if value is None else value
        self.error, self.during = error, during
        self.requests = []

    def open(self, request, timeout):
        self.requests.append((request, timeout))
        if self.during:
            self.during()
        if self.error:
            raise self.error
        return FakeResponse(self.value)


class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.path = Path(self.tmp.name) / "ledger.sqlite3"
        self.ledger = BudgetLedger(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    @unittest.mock.patch("code_agent.budget.time_factor", lambda created_at: Decimal(1))
    def test_precise_cache_accounting_and_no_reasoning_double_charge(self):
        ident = self.ledger.reserve("offline", MESSAGES, 300)
        totals = self.ledger.settle(ident, USAGE)
        expected = (Decimal(40) * Decimal(".044") + Decimal(60) * Decimal("1.32") + Decimal(200) * Decimal("3.96")) / Decimal(1000000)
        self.assertEqual(Decimal(totals["spent_usd"]), expected)
        self.assertEqual(totals["tokens"]["reasoning_tokens"], 80)
        self.assertEqual(totals["tokens"]["total_tokens"], 300)
        self.assertEqual(Decimal(totals["reserved_usd"]), 0)

    def test_persisted_cumulative_spending_and_no_cap_increase(self):
        ledger = BudgetLedger(self.path, cap_usd=".50")
        ledger.settle(ledger.reserve("first", MESSAGES, 300), USAGE)
        reopened = BudgetLedger(self.path)
        self.assertEqual(reopened.snapshot()["request_count"], 1)
        self.assertEqual(Decimal(reopened.snapshot()["cap_usd"]), Decimal(".50"))
        self.assertGreater(Decimal(reopened.snapshot()["spent_usd"]), 0)

    def test_budget_boundary_prevents_network_reservation(self):
        ledger = BudgetLedger(self.path, cap_usd=".001")
        with self.assertRaises(BudgetError):
            ledger.reserve("cannot-fit", MESSAGES, 100)
        self.assertEqual(ledger.snapshot()["request_count"], 0)

    def test_oversized_context_rejected(self):
        with self.assertRaises(BudgetError):
            self.ledger.reserve("oversized", [{"role": "user", "content": "x" * 500000}], 100)

    def test_pending_call_blocks_other_process_or_restart(self):
        self.ledger.reserve("one", MESSAGES, 100)
        other = BudgetLedger(self.path)
        with self.assertRaises(BudgetError):
            other.reserve("two", MESSAGES, 100)

    def test_uncertain_usage_retains_money_and_blocks_restart(self):
        ident = self.ledger.reserve("one", MESSAGES, 100)
        reserved = self.ledger.snapshot()["reserved_usd"]
        with self.assertRaises(BudgetError):
            self.ledger.settle(ident, {})
        self.assertTrue(self.ledger.snapshot()["uncertain"])
        self.assertEqual(self.ledger.snapshot()["reserved_usd"], reserved)
        with self.assertRaises(BudgetError):
            BudgetLedger(self.path).reserve("again", MESSAGES, 100)
        # Reconciliation requires independently confirmed provider token totals.
        self.ledger.settle(ident, USAGE)
        self.assertFalse(self.ledger.snapshot()["uncertain"])

    def test_missing_cache_detail_conservatively_uses_miss_rate(self):
        normalized = normalize_usage({"prompt_tokens": 10, "completion_tokens": 4})
        self.assertEqual(normalized["prompt_cache_miss_tokens"], 10)
        self.assertEqual(normalized["prompt_cache_hit_tokens"], 0)

    def test_inconsistent_or_negative_usage_rejected(self):
        for usage in ({**USAGE, "total_tokens": 0}, {**USAGE, "prompt_cache_hit_tokens": 1000},
                      {**USAGE, "completion_tokens": -1}, {**USAGE, "prompt_tokens": True}):
            with self.subTest(usage=usage):
                with self.assertRaises(BudgetError):
                    normalize_usage(usage)

    def test_unverified_pricing_disabled(self):
        with self.assertRaises(BudgetError):
            BudgetLedger(self.path, pricing=Pricing(verified=False))

    def test_unsubmitted_cancellation_releases_reservation(self):
        ident = self.ledger.reserve("one", MESSAGES, 100)
        self.ledger.release_unsubmitted(ident)
        self.assertEqual(Decimal(self.ledger.snapshot()["reserved_usd"]), 0)
        self.ledger.reserve("two", MESSAGES, 100)


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.ledger = BudgetLedger(Path(self.tmp.name) / "ledger.sqlite3")
        self.secret = "sk-NEVER-LOG-THIS-TEST-KEY"

    def tearDown(self):
        self.tmp.cleanup()

    def client(self, opener):
        return DeepSeekClient(self.secret, self.ledger, opener=opener)

    def test_fixed_official_endpoint_model_json_and_bounded_output(self):
        opener = FakeOpener()
        client = self.client(opener)
        result = client.complete(MESSAGES, max_tokens=400, run_id="mock")
        request = opener.requests[0][0]
        payload = json.loads(request.data)
        self.assertEqual(request.full_url, API_URL)
        self.assertEqual(payload["model"], "deepseek-v4-pro")
        self.assertEqual(payload["response_format"], {"type": "json_object"})
        self.assertEqual(payload["thinking"], {"type": "disabled"})
        self.assertEqual(payload["max_tokens"], 400)
        self.assertEqual(result.request_id, "chatcmpl-offline-test")
        self.assertNotIn(self.secret, repr(client))
        self.assertNotIn(self.secret, json.dumps(self.ledger.export()))

    def test_auth_rate_limit_and_server_errors_are_sanitized_no_retries(self):
        for status in (401, 402, 403, 429, 500):
            unbilled = status != 500
            with self.subTest(status=status):
                with TemporaryDirectory() as folder:
                    ledger = BudgetLedger(Path(folder) / "ledger.sqlite3")
                    error = urllib.error.HTTPError(API_URL, status, self.secret, {}, io.BytesIO(self.secret.encode()))
                    opener = FakeOpener(error=error)
                    with self.assertRaises(ModelError) as caught:
                        DeepSeekClient(self.secret, ledger, opener=opener).complete(MESSAGES)
                    self.assertNotIn(self.secret, str(caught.exception))
                    self.assertEqual(len(opener.requests), 1)
                    snapshot = ledger.snapshot()
                    self.assertEqual(snapshot["uncertain"], not unbilled)
                    if unbilled:
                        self.assertEqual(Decimal(snapshot["reserved_usd"]), 0)
                        self.assertEqual(Decimal(snapshot["spent_usd"]), 0)
                        # A corrected key can be retried immediately after a pre-generation refusal.
                        DeepSeekClient(self.secret, ledger, opener=FakeOpener()).complete(MESSAGES)
                        self.assertGreater(Decimal(ledger.snapshot()["spent_usd"]), 0)

    def test_network_failure_retains_reservation_and_no_retry(self):
        opener = FakeOpener(error=urllib.error.URLError(self.secret))
        with self.assertRaises(ModelError) as caught:
            self.client(opener).complete(MESSAGES)
        self.assertNotIn(self.secret, str(caught.exception))
        self.assertTrue(self.ledger.snapshot()["uncertain"])
        self.assertEqual(len(opener.requests), 1)
        with self.assertRaises(BudgetError):
            self.client(opener).complete(MESSAGES)
        self.assertEqual(len(opener.requests), 1)

    def test_missing_usage_blocks_future_calls(self):
        with self.assertRaises(ModelError):
            self.client(FakeOpener(completion(usage=None))).complete(MESSAGES)
        self.assertTrue(self.ledger.snapshot()["uncertain"])

    def test_truncation_is_billed_but_rejected(self):
        value = completion(choices=[{"finish_reason": "length", "message": {"content": '{"broken":'}}])
        with self.assertRaisesRegex(ModelError, "truncated"):
            self.client(FakeOpener(value)).complete(MESSAGES)
        self.assertGreater(Decimal(self.ledger.snapshot()["spent_usd"]), 0)
        self.assertFalse(self.ledger.snapshot()["uncertain"])

    def test_empty_json_content_is_not_success(self):
        value = completion(choices=[{"finish_reason": "stop", "message": {"content": "  "}}])
        with self.assertRaisesRegex(ModelError, "empty"):
            self.client(FakeOpener(value)).complete(MESSAGES)

    def test_cancel_before_send_spends_nothing(self):
        event, opener = Event(), FakeOpener()
        event.set()
        with self.assertRaises(CancelledError):
            self.client(opener).complete(MESSAGES, cancel_event=event)
        self.assertEqual(len(opener.requests), 0)
        self.assertEqual(self.ledger.snapshot()["request_count"], 0)

    def test_cancel_during_response_still_settles_known_usage(self):
        event = Event()
        with self.assertRaises(CancelledError):
            self.client(FakeOpener(during=event.set)).complete(MESSAGES, cancel_event=event)
        self.assertFalse(self.ledger.snapshot()["uncertain"])
        self.assertGreater(Decimal(self.ledger.snapshot()["spent_usd"]), 0)

    def test_wrong_model_rejected_without_silent_fallback(self):
        with self.assertRaisesRegex(ModelError, "invalid completion"):
            self.client(FakeOpener(completion(model="different-model"))).complete(MESSAGES)

    def test_json_instruction_required_before_reserving(self):
        with self.assertRaisesRegex(ModelError, "JSON"):
            self.client(FakeOpener()).complete([{"role": "user", "content": "plain text only"}])
        self.assertEqual(self.ledger.snapshot()["request_count"], 0)


if __name__ == "__main__":
    unittest.main()


class PeakPricingTests(unittest.TestCase):
    def test_off_peak_requests_settle_at_half_the_peak_rate(self):
        from code_agent.budget import time_factor
        self.assertEqual(time_factor("2026-10-30T07:32:00+00:00"), 1)       # Friday 07:32 UTC: peak
        self.assertEqual(time_factor("2026-11-02T12:45:00+00:00"), Decimal("0.5"))  # Monday 12:45 UTC
        self.assertEqual(time_factor("2026-11-01T07:00:00+00:00"), Decimal("0.5"))  # Sunday
        self.assertEqual(time_factor("not a time"), 1)                      # unknown: assume peak


class PerRunCapTests(unittest.TestCase):
    def test_each_run_has_its_own_cap_and_history_is_kept(self):
        with TemporaryDirectory() as folder:
            ledger = BudgetLedger(Path(folder) / "ledger.sqlite3", cap_usd=".01")
            ledger.settle(ledger.reserve("run-1", MESSAGES, 300), USAGE)
            first = Decimal(ledger.snapshot("run-1")["spent_usd"])
            # Spending enough in run-1 to block it must not block a fresh run-2.
            with self.assertRaises(BudgetError):
                for _ in range(100):
                    ledger.settle(ledger.reserve("run-1", MESSAGES, 300), USAGE)
            ledger.settle(ledger.reserve("run-2", MESSAGES, 300), USAGE)
            self.assertEqual(Decimal(ledger.snapshot("run-2")["spent_usd"]), first)
            self.assertGreater(Decimal(ledger.snapshot()["spent_usd"]), Decimal(ledger.snapshot("run-1")["spent_usd"]))
            self.assertEqual(ledger.latest_run_id(), "run-2")
