#!/usr/bin/env python3
"""Agent Skill wrapper for The Non-AI Writer API.

Reads workflow context JSON, compiles it through /v1/briefs, optionally creates a
paid draft through /v1/drafts, then polls until the draft is complete.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_POLL_INTERVAL_SECONDS = 4.0
DEFAULT_TIMEOUT_SECONDS = 600.0
MAX_CLIENT_CONTEXT_CHARS = 120_000


class NonAiWriterError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        code: str | None = None,
        retryable: bool = False,
        payload: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.retryable = retryable
        self.payload = payload or {}


def main() -> int:
    args = parse_args()
    try:
        payload = load_payload(args)
        if args.dry_run:
            emit({"ok": True, "mode": "dry_run", "payload": payload})
            return 0

        client = NonAiWriterClient(
            base_url=args.base_url or env_required("NON_AI_WRITER_API_BASE_URL"),
            api_key=args.api_key or env_required("NON_AI_WRITER_API_KEY"),
            timeout_seconds=args.request_timeout,
        )
        brief = client.create_brief(payload)
        if args.brief_only or not brief.get("ready"):
            emit({"ok": bool(brief.get("ready")), "mode": "brief", "brief": brief})
            return 0 if brief.get("ready") else 2

        draft_request = brief.get("draft_request")
        if not isinstance(draft_request, dict):
            raise NonAiWriterError("Brief did not include a draft_request.", code="missing_draft_request")

        run = client.create_draft(draft_request)
        run_id = as_nonempty_string(run.get("id"))
        if not run_id:
            raise NonAiWriterError("Draft response did not include an id.", code="missing_run_id", payload=run)

        final = client.poll_draft(
            run_id,
            timeout_seconds=args.timeout,
            interval_seconds=args.poll_interval,
        )
        emit({
            "ok": final.get("status") == "succeeded",
            "mode": "draft",
            "brief": brief,
            "run": final,
        })
        return 0 if final.get("status") == "succeeded" else 3
    except NonAiWriterError as exc:
        emit_error(exc)
        return 1
    except Exception as exc:  # defensive CLI boundary
        emit_error(NonAiWriterError(str(exc), code="wrapper_error", retryable=False))
        return 1


class NonAiWriterClient:
    def __init__(self, *, base_url: str, api_key: str, timeout_seconds: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key.strip()
        self.timeout_seconds = timeout_seconds
        if not self.base_url:
            raise NonAiWriterError("NON_AI_WRITER_API_BASE_URL is empty.", code="missing_base_url")
        if not self.api_key:
            raise NonAiWriterError("NON_AI_WRITER_API_KEY is empty.", code="missing_api_key")

    def create_brief(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request_json("POST", "/v1/briefs", payload)

    def create_draft(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request_json("POST", "/v1/drafts", payload)

    def get_draft(self, run_id: str) -> dict[str, Any]:
        return self._request_json("GET", f"/v1/drafts/{run_id}", None)

    def poll_draft(
        self,
        run_id: str,
        *,
        timeout_seconds: float,
        interval_seconds: float,
    ) -> dict[str, Any]:
        deadline = time.monotonic() + timeout_seconds
        while True:
            result = self.get_draft(run_id)
            status = result.get("status")
            if status in {"succeeded", "failed"}:
                return result
            if time.monotonic() >= deadline:
                raise NonAiWriterError(
                    f"Timed out waiting for draft {run_id}.",
                    code="poll_timeout",
                    retryable=True,
                    payload={"id": run_id, "last_status": status},
                )
            time.sleep(interval_seconds)

    def _request_json(self, method: str, path: str, payload: dict[str, Any] | None) -> dict[str, Any]:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=body,
            method=method,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "non-ai-writer-agent-skill/0.1",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return parse_json_response(response.read(), status=response.status)
        except urllib.error.HTTPError as exc:
            payload = parse_json_response(exc.read(), status=exc.code)
            error = payload.get("error") if isinstance(payload.get("error"), dict) else {}
            message = as_nonempty_string(error.get("message")) or f"HTTP {exc.code}"
            code = as_nonempty_string(error.get("code")) or "http_error"
            retryable = bool(error.get("retryable"))
            raise NonAiWriterError(
                message,
                status=exc.code,
                code=code,
                retryable=retryable,
                payload=payload,
            ) from exc
        except urllib.error.URLError as exc:
            raise NonAiWriterError(
                f"Could not reach The Non-AI Writer API: {exc.reason}",
                code="network_error",
                retryable=True,
            ) from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run The Non-AI Writer from agent workflow context.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--stdin", action="store_true", help="Read JSON payload from stdin.")
    source.add_argument("--input", type=Path, help="Read JSON payload from a file.")
    parser.add_argument("--brief-only", action="store_true", help="Only call /v1/briefs and print the result.")
    parser.add_argument("--dry-run", action="store_true", help="Validate and print the normalized input payload.")
    parser.add_argument("--base-url", help="API base URL. Defaults to NON_AI_WRITER_API_BASE_URL.")
    parser.add_argument("--api-key", help="API key. Defaults to NON_AI_WRITER_API_KEY.")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS, help="Total polling timeout.")
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=DEFAULT_POLL_INTERVAL_SECONDS,
        help="Seconds between draft status polls.",
    )
    parser.add_argument("--request-timeout", type=float, default=30.0, help="Per-request timeout.")
    return parser.parse_args()


def load_payload(args: argparse.Namespace) -> dict[str, Any]:
    raw = sys.stdin.read() if args.stdin else args.input.read_text(encoding="utf-8")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise NonAiWriterError(f"Input is not valid JSON: {exc}", code="invalid_json") from exc
    if not isinstance(payload, dict):
        raise NonAiWriterError("Input JSON must be an object.", code="invalid_payload")
    return normalize_payload(payload)


def normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    if value := as_nonempty_string(payload.get("desired_output")):
        normalized["desired_output"] = value[:500]

    messages = normalize_messages(payload.get("messages"))
    if messages:
        normalized["messages"] = messages

    tool_outputs = normalize_tool_outputs(payload.get("tool_outputs"))
    if tool_outputs:
        normalized["tool_outputs"] = tool_outputs

    if notes := as_nonempty_string(payload.get("notes")):
        normalized["notes"] = notes[:60_000]

    options = payload.get("options")
    if isinstance(options, dict):
        normalized["options"] = normalize_options(options)
    else:
        normalized["options"] = {"target_words": "auto", "output_format": "markdown"}

    metadata = payload.get("metadata")
    normalized["metadata"] = metadata if isinstance(metadata, dict) else {}
    normalized["metadata"].setdefault("source", "agent_skill")

    total_context_chars = (
        len(normalized.get("notes", ""))
        + sum(len(message["content"]) for message in normalized.get("messages", []))
        + sum(len(output["content"]) for output in normalized.get("tool_outputs", []))
    )
    if total_context_chars > MAX_CLIENT_CONTEXT_CHARS:
        raise NonAiWriterError(
            f"Context is too large for one request ({total_context_chars} chars). Summarize first.",
            code="context_too_large",
        )
    if total_context_chars == 0:
        raise NonAiWriterError("No usable context was provided.", code="empty_context")
    return normalized


def normalize_messages(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    messages: list[dict[str, str]] = []
    for item in value[:80]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        if role == "system":
            continue
        if role not in {"user", "assistant", "tool"}:
            continue
        content = as_nonempty_string(item.get("content"))
        if not content:
            continue
        message = {"role": role, "content": content[:20_000]}
        if name := as_nonempty_string(item.get("name")):
            message["name"] = name[:120]
        messages.append(message)
    return messages


def normalize_tool_outputs(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    outputs: list[dict[str, str]] = []
    for index, item in enumerate(value[:20]):
        if isinstance(item, str):
            content = item
            output = {"name": f"tool_output_{index + 1}", "content": content[:50_000]}
        elif isinstance(item, dict):
            content = as_nonempty_string(item.get("content"))
            if not content:
                continue
            output = {"content": content[:50_000]}
            if name := as_nonempty_string(item.get("name")):
                output["name"] = name[:120]
            if output_type := as_nonempty_string(item.get("type")):
                output["type"] = output_type[:80]
        else:
            continue
        outputs.append(output)
    return outputs


def normalize_options(value: dict[str, Any]) -> dict[str, Any]:
    target_words = value.get("target_words", "auto")
    if target_words != "auto":
        try:
            target_words = int(target_words)
        except (TypeError, ValueError):
            target_words = "auto"
        else:
            target_words = max(250, min(target_words, 900))
    output_format = value.get("output_format", "markdown")
    if output_format not in {"markdown", "plain_text"}:
        output_format = "markdown"
    return {"target_words": target_words, "output_format": output_format}


def parse_json_response(raw: bytes, *, status: int) -> dict[str, Any]:
    text = raw.decode("utf-8", errors="replace").strip()
    if not text:
        return {"status": status}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise NonAiWriterError(f"API returned non-JSON response: {text[:500]}", status=status) from exc
    if not isinstance(parsed, dict):
        raise NonAiWriterError("API returned a non-object JSON response.", status=status)
    return parsed


def as_nonempty_string(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def env_required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise NonAiWriterError(f"Missing required environment variable: {name}", code=f"missing_{name.lower()}")
    return value


def emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def emit_error(error: NonAiWriterError) -> None:
    emit({
        "ok": False,
        "error": {
            "code": error.code or "error",
            "message": str(error),
            "status": error.status,
            "retryable": error.retryable,
            "payload": error.payload,
        },
    })


if __name__ == "__main__":
    raise SystemExit(main())
