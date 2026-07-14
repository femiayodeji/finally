"""LLM call — LiteLLM → OpenRouter → Cerebras (per the cerebras-inference skill).

Requests structured output directly. If the provider doesn't strictly enforce
the schema, `ChatResponse.model_validate_json` raises and we retry once
before giving up gracefully (PLAN §9 *Structured Output Reliability*).
Honors `LLM_MOCK` for deterministic, network-free responses used in tests and
when no API key is configured.
"""

from __future__ import annotations

import json
import logging
import os
import re

from pydantic import ValidationError

from .schema import ChatResponse, Trade, WatchlistChange

logger = logging.getLogger(__name__)

MODEL = "openrouter/openai/gpt-oss-120b"
EXTRA_BODY = {"provider": {"order": ["cerebras"]}}

_MAX_ATTEMPTS = 2  # initial call + one retry on malformed structured output

_FALLBACK_MESSAGE = "Sorry, I had trouble processing that request. Please try again."

# --- mock-mode intent parsing -------------------------------------------------
# Deterministic pattern matching so LLM_MOCK=true still exercises the
# auto-execution path (E2E tests assert an inline trade/watchlist change).
_TRADE_RE = re.compile(
    r"\b(buy|sell)\b\s+(\d+(?:\.\d+)?)\s+(?:shares?\s+of\s+)?([a-zA-Z]{1,5})\b",
    re.IGNORECASE,
)
_WATCH_ADD_RE = re.compile(
    r"\badd\s+([a-zA-Z]{1,5})\b(?:\s+to\s+(?:the\s+|my\s+)?watchlist)?|\bwatch\s+([a-zA-Z]{1,5})\b",
    re.IGNORECASE,
)
_WATCH_REMOVE_RE = re.compile(
    r"\bremove\s+([a-zA-Z]{1,5})\b(?:\s+from\s+(?:the\s+|my\s+)?watchlist)?|\bunwatch\s+([a-zA-Z]{1,5})\b",
    re.IGNORECASE,
)


def _llm_mock() -> bool:
    try:
        from app.config import LLM_MOCK

        return bool(LLM_MOCK)
    except Exception:
        return os.environ.get("LLM_MOCK", "false").strip().lower() in ("1", "true", "yes")


def _openrouter_api_key() -> str:
    try:
        from app.config import OPENROUTER_API_KEY

        return OPENROUTER_API_KEY
    except Exception:
        return os.environ.get("OPENROUTER_API_KEY", "")


def complete_chat(system: str, messages: list[dict]) -> ChatResponse:
    """Call the LLM and return a validated `ChatResponse`.

    `messages` is prior conversation history plus the new user turn, each
    `{"role": "user"|"assistant", "content": str}`. `system` (system prompt +
    portfolio/watchlist context) is prepended as the system message.
    """
    if _llm_mock():
        return _mock_response(messages)

    full_messages = [{"role": "system", "content": system}, *messages]
    return _call_llm(full_messages)


def _call_llm(full_messages: list[dict]) -> ChatResponse:
    from litellm import completion

    api_key = _openrouter_api_key()
    if api_key:
        os.environ.setdefault("OPENROUTER_API_KEY", api_key)

    last_error: Exception | None = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            response = completion(
                model=MODEL,
                messages=full_messages,
                response_format=ChatResponse,
                reasoning_effort="low",
                extra_body=EXTRA_BODY,
            )
            content = response.choices[0].message.content
            return ChatResponse.model_validate_json(content)
        except (ValidationError, json.JSONDecodeError, ValueError) as exc:
            last_error = exc
            logger.warning("LLM structured output invalid (attempt %d/%d): %s",
                            attempt, _MAX_ATTEMPTS, exc)

    logger.error("LLM structured output failed after %d attempts: %s", _MAX_ATTEMPTS, last_error)
    return ChatResponse(message=_FALLBACK_MESSAGE)


def _mock_response(messages: list[dict]) -> ChatResponse:
    """Deterministic canned reply for `LLM_MOCK=true` — no network call."""
    last_user = next(
        (m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), ""
    )

    trades: list[Trade] = []
    match = _TRADE_RE.search(last_user)
    if match:
        side, quantity, ticker = match.group(1).lower(), float(match.group(2)), match.group(3)
        trades.append(Trade(ticker=ticker.upper(), side=side, quantity=quantity))

    watchlist_changes: list[WatchlistChange] = []
    add_match = _WATCH_ADD_RE.search(last_user)
    if add_match:
        ticker = (add_match.group(1) or add_match.group(2)).upper()
        watchlist_changes.append(WatchlistChange(ticker=ticker, action="add"))
    else:
        remove_match = _WATCH_REMOVE_RE.search(last_user)
        if remove_match:
            ticker = (remove_match.group(1) or remove_match.group(2)).upper()
            watchlist_changes.append(WatchlistChange(ticker=ticker, action="remove"))

    if trades:
        t = trades[0]
        message = f"Mock mode: executing {t.side} {t.quantity:g} {t.ticker}."
    elif watchlist_changes:
        w = watchlist_changes[0]
        verb = "Adding" if w.action == "add" else "Removing"
        prep = "to" if w.action == "add" else "from"
        message = f"Mock mode: {verb} {w.ticker} {prep} your watchlist."
    else:
        message = (
            "Mock mode: I'm FinAlly, your AI trading assistant. Ask me to analyze "
            "your portfolio, or say things like 'buy 5 AAPL' or 'add PYPL to my watchlist'."
        )

    return ChatResponse(message=message, trades=trades, watchlist_changes=watchlist_changes)
