"""Persistent, conservative accounting for the assignment's cumulative USD 1 cap.

Prices are application estimates at the published peak rates, not provider bills.
Reasoning tokens are part of completion_tokens and are never charged twice.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import sqlite3
from typing import Any
import uuid


MODEL = "deepseek-v4-pro"
MILLION = Decimal(1_000_000)


class BudgetError(RuntimeError):
    """A paid request cannot safely fit the remaining assignment budget."""


@dataclass(frozen=True)
class Pricing:
    input_cache_hit_per_million: str = "0.044"
    input_cache_miss_per_million: str = "1.32"
    output_per_million: str = "3.96"
    version: str = "deepseek-v4-pro-peak-verified-2026-10-31"
    source_url: str = "https://api-docs.deepseek.com/quick_start/pricing/"
    currency: str = "USD"
    verified: bool = True

    def rates(self) -> tuple[Decimal, Decimal, Decimal]:
        try:
            rates = tuple(Decimal(v) for v in (
                self.input_cache_hit_per_million,
                self.input_cache_miss_per_million,
                self.output_per_million,
            ))
        except (InvalidOperation, ValueError) as exc:
            raise BudgetError("Invalid pricing configuration.") from exc
        if not self.verified or self.currency != "USD" or any(
            not r.is_finite() or r < 0 for r in rates
        ) or rates[1] < rates[0]:
            raise BudgetError("Verified USD pricing is required before paid calls.")
        return rates


# DeepSeek refuses these before running the model, so no tokens are charged.
UNBILLED_REJECTIONS = frozenset({401, 402, 403, 429})


def is_peak(moment: datetime) -> bool:
    """DeepSeek peak: 01:00-04:00 and 06:00-10:00 UTC, Monday-Friday (public holidays treated as peak)."""
    moment = moment.astimezone(timezone.utc)
    return moment.weekday() < 5 and (1 <= moment.hour < 4 or 6 <= moment.hour < 10)


def time_factor(created_at: str) -> Decimal:
    """Settled charges use the rate in force when the request was sent; off-peak is half price.
    Reservations still assume peak, so the pre-call bound stays conservative."""
    try:
        moment = datetime.fromisoformat(created_at)
    except (TypeError, ValueError):
        return Decimal(1)
    return Decimal(1) if is_peak(moment) else Decimal("0.5")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _token_count(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise BudgetError(f"Missing or invalid {name}; billing remains uncertain.")
    return value


def normalize_usage(usage: Any) -> dict[str, int]:
    """Require provider totals and reconcile cache buckets without double counting."""
    if not isinstance(usage, dict):
        raise BudgetError("Response usage is missing; billing remains uncertain.")
    prompt = _token_count(usage.get("prompt_tokens"), "prompt_tokens")
    output = _token_count(usage.get("completion_tokens"), "completion_tokens")
    hit_raw, miss_raw = usage.get("prompt_cache_hit_tokens"), usage.get("prompt_cache_miss_tokens")
    if hit_raw is None and miss_raw is None:
        hit, miss = 0, prompt  # Missing cache detail is charged at the higher rate.
    elif hit_raw is None:
        miss = _token_count(miss_raw, "prompt_cache_miss_tokens")
        hit = prompt - miss
    elif miss_raw is None:
        hit = _token_count(hit_raw, "prompt_cache_hit_tokens")
        miss = prompt - hit
    else:
        hit = _token_count(hit_raw, "prompt_cache_hit_tokens")
        miss = _token_count(miss_raw, "prompt_cache_miss_tokens")
    if min(hit, miss) < 0 or hit + miss != prompt:
        raise BudgetError("Inconsistent cache usage; billing remains uncertain.")
    total = usage.get("total_tokens", prompt + output)
    if _token_count(total, "total_tokens") != prompt + output:
        raise BudgetError("Inconsistent total usage; billing remains uncertain.")
    detail = usage.get("completion_tokens_details") or {}
    reasoning = _token_count(detail.get("reasoning_tokens", 0), "reasoning_tokens") if isinstance(detail, dict) else 0
    if reasoning > output:
        raise BudgetError("Inconsistent reasoning usage; billing remains uncertain.")
    return {"prompt_tokens": prompt, "completion_tokens": output,
            "prompt_cache_hit_tokens": hit, "prompt_cache_miss_tokens": miss,
            "reasoning_tokens": reasoning, "total_tokens": prompt + output}


def conservative_input_bound(messages: list[dict[str, str]]) -> int:
    """A deliberately loose byte bound, not an exact provider-tokenizer count.

    Two tokens per UTF-8 byte plus 256/message and 1024 framing tokens leave
    generous room for chat serialization. No tokenizer-based precision is claimed.
    """
    if not isinstance(messages, list) or not messages:
        raise BudgetError("At least one text message is required.")
    size = 0
    for msg in messages:
        if not isinstance(msg, dict) or set(msg) != {"role", "content"}:
            raise BudgetError("Only role/content text messages are supported.")
        if msg["role"] not in {"system", "user", "assistant"} or not isinstance(msg["content"], str):
            raise BudgetError("Invalid text message.")
        size += len(msg["content"].encode("utf-8"))
    return size * 2 + len(messages) * 256 + 1024


class BudgetLedger:
    """SQLite reservations survive restarts; unresolved calls block new requests.

    Keep one ledger for the entire assignment. Calls made outside this application
    must be reconciled separately; this ledger cannot discover external spending.
    """

    def __init__(self, path: str | Path, cap_usd: float | str = "1.00", pricing: Pricing | None = None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.pricing = pricing or Pricing()
        self.pricing.rates()
        try:
            cap = Decimal(str(cap_usd))
        except (InvalidOperation, ValueError):
            raise BudgetError("The assignment cap must be a valid USD amount.") from None
        if not cap.is_finite() or not Decimal("0") < cap <= Decimal("1"):
            raise BudgetError("The assignment cap must be greater than zero and at most USD 1.")
        with self._connection() as db:
            db.execute("CREATE TABLE IF NOT EXISTS settings (name TEXT PRIMARY KEY, value TEXT NOT NULL)")
            db.execute("""CREATE TABLE IF NOT EXISTS requests (
                id TEXT PRIMARY KEY, run_id TEXT NOT NULL, created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL, model TEXT NOT NULL, status TEXT NOT NULL,
                reserved_usd TEXT NOT NULL, estimated_charge_usd TEXT,
                input_bound INTEGER NOT NULL, max_tokens INTEGER NOT NULL,
                pricing_json TEXT NOT NULL, usage_json TEXT, request_id TEXT, note TEXT
            )""")
            row = db.execute("SELECT value FROM settings WHERE name='cap_usd'").fetchone()
            cap = min(cap, Decimal(row[0])) if row else cap
            db.execute("INSERT OR REPLACE INTO settings VALUES ('cap_usd',?)", (str(cap),))

    @contextmanager
    def _connection(self):
        db = sqlite3.connect(str(self.path), timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA busy_timeout=10000")
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _totals(db) -> dict[str, Any]:
        cap = Decimal(db.execute("SELECT value FROM settings WHERE name='cap_usd'").fetchone()[0])
        rows = db.execute("SELECT * FROM requests ORDER BY created_at,id").fetchall()
        spent = sum((Decimal(r["estimated_charge_usd"] or "0") for r in rows), Decimal(0))
        reserved = sum((Decimal(r["reserved_usd"]) for r in rows if r["status"] in {"reserved", "uncertain"}), Decimal(0))
        tokens = {k: 0 for k in ("prompt_tokens", "completion_tokens", "prompt_cache_hit_tokens", "prompt_cache_miss_tokens", "reasoning_tokens", "total_tokens")}
        for row in rows:
            if row["usage_json"]:
                for key, value in json.loads(row["usage_json"]).items():
                    tokens[key] += value
        return {"cap_usd": str(cap), "spent_usd": str(spent), "reserved_usd": str(reserved),
                "remaining_usd": str(max(Decimal(0), cap - spent - reserved)),
                "uncertain": any(r["status"] == "uncertain" for r in rows),
                "pending": any(r["status"] == "reserved" for r in rows),
                "request_count": len(rows), "tokens": tokens,
                "cost_basis": "Application estimate at published peak/off-peak USD rates (reservations at peak); not a provider bill."}

    def snapshot(self) -> dict[str, Any]:
        with self._connection() as db:
            return self._totals(db)

    totals = snapshot

    def reserve(self, run_id: str, messages: list[dict[str, str]], max_tokens: int) -> str:
        if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or not 1 <= max_tokens <= 393216:
            raise BudgetError("Output token cap must be between 1 and 393216.")
        if not isinstance(run_id, str) or not run_id or len(run_id) > 128:
            raise BudgetError("A short nonempty run ID is required.")
        bound = conservative_input_bound(messages)
        if bound + max_tokens > 1_000_000:
            raise BudgetError("Conservative request bound exceeds the model context limit.")
        _, miss, output = self.pricing.rates()
        reservation = ((Decimal(bound) * miss + Decimal(max_tokens) * output) / MILLION) * Decimal("1.20")
        reservation += Decimal("0.001")
        ident, timestamp = uuid.uuid4().hex, _now()
        with self._connection() as db:
            totals = self._totals(db)
            if totals["pending"] or totals["uncertain"]:
                raise BudgetError("A previous request is pending or has uncertain billing. Reconcile it before another paid call.")
            if reservation > Decimal(totals["remaining_usd"]):
                raise BudgetError("The conservative request reservation exceeds the remaining USD 1 assignment budget.")
            db.execute("""INSERT INTO requests (id,run_id,created_at,updated_at,model,status,
                reserved_usd,input_bound,max_tokens,pricing_json) VALUES (?,?,?,?,?,'reserved',?,?,?,?)""",
                (ident, run_id, timestamp, timestamp, MODEL, str(reservation), bound, max_tokens, json.dumps(asdict(self.pricing))))
        return ident

    def settle(self, reservation_id: str, usage: dict[str, Any], request_id: str | None = None) -> dict[str, Any]:
        try:
            normalized = normalize_usage(usage)
        except BudgetError:
            self.mark_uncertain(reservation_id, "invalid_or_missing_usage")
            raise
        with self._connection() as db:
            row = db.execute("SELECT * FROM requests WHERE id=?", (reservation_id,)).fetchone()
            if row is None or row["status"] not in {"reserved", "uncertain"}:
                raise BudgetError("Only an outstanding reservation can be settled.")
            pricing = Pricing(**json.loads(row["pricing_json"]))
            hit, miss, output = pricing.rates()
            factor = time_factor(row["created_at"])
            charge = factor * (Decimal(normalized["prompt_cache_hit_tokens"]) * hit
                      + Decimal(normalized["prompt_cache_miss_tokens"]) * miss
                      + Decimal(normalized["completion_tokens"]) * output) / MILLION
            safe_id = request_id if isinstance(request_id, str) and len(request_id) < 200 else None
            db.execute("""UPDATE requests SET status='settled',updated_at=?,estimated_charge_usd=?,
                usage_json=?,request_id=?,note=NULL WHERE id=?""", (_now(), str(charge), json.dumps(normalized), safe_id, reservation_id))
            return self._totals(db)

    def mark_uncertain(self, reservation_id: str, reason: str = "transport_or_response_failure") -> None:
        allowed = {"transport_or_response_failure", "invalid_or_missing_usage", "http_rejection", "cancelled_in_flight", "invalid_response"}
        reason = reason if reason in allowed else "transport_or_response_failure"
        with self._connection() as db:
            db.execute("UPDATE requests SET status='uncertain',updated_at=?,note=? WHERE id=? AND status='reserved'", (_now(), reason, reservation_id))

    def release_rejected(self, reservation_id: str, status_code: int) -> None:
        """The provider refused the request before generation (auth, balance, access, rate limit): no tokens billed."""
        if status_code not in UNBILLED_REJECTIONS:
            raise ValueError("Only pre-generation rejections can release a reservation.")
        with self._connection() as db:
            db.execute("UPDATE requests SET status='rejected',updated_at=?,note=? WHERE id=? AND status='reserved'",
                       (_now(), f"http_{status_code}_rejected_unbilled", reservation_id))

    def release_unsubmitted(self, reservation_id: str) -> None:
        """Only use when no network request was attempted (for example pre-send cancellation)."""
        with self._connection() as db:
            db.execute("UPDATE requests SET status='not_sent',updated_at=?,note='cancelled_before_send' WHERE id=? AND status='reserved'", (_now(), reservation_id))

    def export(self) -> dict[str, Any]:
        with self._connection() as db:
            rows = [dict(r) for r in db.execute("SELECT * FROM requests ORDER BY created_at,id")]
            for row in rows:
                row["pricing"] = json.loads(row.pop("pricing_json"))
                raw_usage = row.pop("usage_json")
                row["usage"] = json.loads(raw_usage) if raw_usage else None
            return {"summary": self._totals(db), "requests": rows}
