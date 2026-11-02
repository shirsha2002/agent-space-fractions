"""Official DeepSeek client: fixed model/host, no retries, no secret-bearing errors."""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
import socket
from threading import Event
from typing import Any
import urllib.error
import urllib.request

from .budget import UNBILLED_REJECTIONS, BudgetError, BudgetLedger, MODEL, conservative_input_bound, normalize_usage


API_URL = "https://api.deepseek.com/chat/completions"
MODELS_URL = "https://api.deepseek.com/models"
MAX_RESPONSE_BYTES = 8 * 1024 * 1024


class ModelError(RuntimeError):
    """A sanitized transport, provider, or response error."""


class CancelledError(ModelError):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward Authorization to a redirect target.


@dataclass(frozen=True)
class CompletionResult:
    content: str
    usage: dict[str, Any]
    request_id: str
    model: str = MODEL
    reservation_id: str = ""
    finish_reason: str = "stop"


def _cancelled(event: Event | None) -> bool:
    return event is not None and event.is_set()


class DeepSeekClient:
    """API key lives only in memory; caller must not serialize this object.

    Cancellation before send spends nothing. In-flight urllib requests cannot be
    safely interrupted, so cancellation is honored after response/accounting or
    the bounded socket timeout. No background automatic retry is performed.
    """

    def __init__(self, api_key: str, ledger: BudgetLedger, timeout: float = 120, opener=None):
        if not isinstance(api_key, str) or not api_key.strip() or any(c.isspace() for c in api_key.strip()):
            raise ModelError("Enter a valid API key in the masked local field.")
        if not 1 <= timeout <= 120:
            raise ModelError("Request timeout must be between 1 and 120 seconds.")
        self._api_key = api_key.strip()
        self.ledger = ledger
        self.timeout = timeout
        self._opener = opener or urllib.request.build_opener(_NoRedirect())

    def __repr__(self) -> str:
        return "DeepSeekClient(model='deepseek-v4-pro', api_key=<redacted>)"

    def _request(self, url: str, data: bytes | None = None):
        request = urllib.request.Request(url, data=data, headers={
            "Authorization": "Bearer " + self._api_key,
            "Content-Type": "application/json", "Accept": "application/json",
            "User-Agent": "Task1-Code-Agent/1.0",
        }, method="POST" if data is not None else "GET")
        return self._opener.open(request, timeout=self.timeout)

    @staticmethod
    def _read_json(response) -> dict[str, Any]:
        raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ModelError("The provider response exceeded the safe size limit.")
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, dict):
            raise ModelError("The provider returned an invalid response object.")
        return value

    def check_model_access(self) -> bool:
        """Read-only model-list check; no chat-completion charge is requested."""
        try:
            with self._request(MODELS_URL) as response:
                data = self._read_json(response)
            return any(isinstance(item, dict) and item.get("id") == MODEL for item in data.get("data", []))
        except Exception:
            raise ModelError("Could not verify model access. Check the official account and network.") from None

    def complete(self, messages: list[dict[str, str]], max_tokens: int = 16000,
                 run_id: str = "generation", cancel_event: Event | None = None) -> CompletionResult:
        if _cancelled(cancel_event):
            raise CancelledError("Cancelled before the paid request was sent.")
        conservative_input_bound(messages)  # Validate before inspecting text or reserving money.
        # JSON-mode instructions must contain the word json per official guidance.
        if not any("json" in msg.get("content", "").lower() for msg in messages if isinstance(msg, dict)):
            raise ModelError("Generation instructions must explicitly request JSON output.")
        reservation = self.ledger.reserve(run_id, messages, max_tokens)
        if _cancelled(cancel_event):
            self.ledger.release_unsubmitted(reservation)
            raise CancelledError("Cancelled before the paid request was sent.")
        payload = json.dumps({
            "model": MODEL, "messages": messages, "max_tokens": max_tokens,
            "stream": False, "response_format": {"type": "json_object"},
            "thinking": {"type": "disabled"},
        }, ensure_ascii=False).encode("utf-8")
        try:
            with self._request(API_URL, payload) as response:
                data = self._read_json(response)
        except urllib.error.HTTPError as exc:
            if exc.code in UNBILLED_REJECTIONS:
                self.ledger.release_rejected(reservation, exc.code)
            else:
                self.ledger.mark_uncertain(reservation, "http_rejection")
            messages_by_status = {
                400: "The official API rejected the request parameters.",
                401: "The official API rejected the API key.",
                402: "The official DeepSeek account has insufficient balance.",
                403: "The account cannot access this request or required model.",
                404: "The required official endpoint or model is unavailable.",
                429: "The official API rate limit was reached.",
            }
            message = messages_by_status.get(exc.code, "The official API returned a server error.")
            if exc.code in UNBILLED_REJECTIONS:
                raise ModelError(message + " The request was refused before generation, so its reservation was released.") from None
            raise ModelError(message + " Billing is unresolved; automatic retries are blocked.") from None
        except (urllib.error.URLError, TimeoutError, socket.timeout, OSError):
            self.ledger.mark_uncertain(reservation)
            raise ModelError("The request timed out or the network failed. Billing is unresolved; automatic retries are blocked.") from None
        except Exception:
            self.ledger.mark_uncertain(reservation, "invalid_response")
            raise ModelError("The provider response could not be decoded. Billing is unresolved; automatic retries are blocked.") from None
        try:
            usage = data.get("usage")
            normalized = normalize_usage(usage)
            response_id = data.get("id", "")
            safe_id = response_id if isinstance(response_id, str) and re.fullmatch(r"[A-Za-z0-9._:-]{1,180}", response_id) else ""
            if self._api_key in safe_id:
                safe_id = ""
            self.ledger.settle(reservation, usage, request_id=safe_id or None)
        except BudgetError:
            self.ledger.mark_uncertain(reservation, "invalid_or_missing_usage")
            raise ModelError("The response omitted valid usage. The reservation is retained; reconcile billing before another paid call.") from None
        if _cancelled(cancel_event):
            raise CancelledError("Cancelled after the response arrived; its usage was accounted for.")
        try:
            model = data.get("model", MODEL)
            if not isinstance(model, str) or self._api_key in model or not (model == MODEL or model.startswith(MODEL + "-")):
                raise ValueError("Unexpected model")
            choices = data["choices"]
            choice = choices[0]
            finish = choice["finish_reason"]
            content = choice["message"]["content"]
            if finish != "stop":
                raise ModelError("The completion was truncated or stopped unexpectedly. Its usage was accounted for; no incomplete project was accepted.")
            if not isinstance(content, str) or not content.strip():
                raise ModelError("The model returned empty JSON content. Its usage was accounted for.")
            if self._api_key in content:
                raise ModelError("The response contained sensitive credential text and was rejected.")
            return CompletionResult(content, normalized, safe_id, model, reservation, finish)
        except ModelError:
            raise
        except (KeyError, IndexError, TypeError, ValueError):
            raise ModelError("The provider returned an invalid completion. Its usage was accounted for.") from None
