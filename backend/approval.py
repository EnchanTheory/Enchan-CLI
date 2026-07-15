"""UI-independent approval requests for capability-bearing agent tools."""

from __future__ import annotations

import sys
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator, Mapping

from backend.session_log import append_session_event


@dataclass(frozen=True)
class ApprovalRequest:
    id: str
    tool: str
    summary: str
    details: Mapping[str, object]
    capability: str

    def public_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "tool": self.tool,
            "summary": self.summary,
            "details": dict(self.details),
            "capability": self.capability,
        }


@dataclass(frozen=True)
class ApprovalDecision:
    approved: bool
    reason: str


ApprovalHandler = Callable[[ApprovalRequest], bool | ApprovalDecision]

_handler: ContextVar[ApprovalHandler | None] = ContextVar("approval_handler", default=None)
_interface: ContextVar[str] = ContextVar("approval_interface", default="cui")
_session_log_path: ContextVar[Path | None] = ContextVar("approval_session_log_path", default=None)


def _safe_text(value: object, *, limit: int = 20_000) -> str:
    text = str(value if value is not None else "")
    text = "".join(char for char in text if char in "\n\t" or ord(char) >= 32)
    return text if len(text) <= limit else text[:limit] + "\n[truncated]"


def sanitize_details(details: Mapping[str, object]) -> dict[str, object]:
    """Bound approval payloads without attempting unsafe shell-string classification."""
    sanitized: dict[str, object] = {}
    for key, value in details.items():
        if value is None:
            continue
        sanitized[_safe_text(key, limit=80)] = _safe_text(value)
    return sanitized


def terminal_approval_handler(request: ApprovalRequest) -> ApprovalDecision:
    if not getattr(sys.stdin, "isatty", lambda: False)():
        return ApprovalDecision(False, "non_interactive")
    print("\n\x1b[38;2;190;170;120mSecurity approval required\x1b[0m")
    print(f"  Tool: {request.tool}")
    print(f"  Operation: {request.summary}")
    labels = {"cwd": "Working directory", "command": "Command", "path": "Target", "operation": "Type", "skill": "Skill"}
    for key, value in request.details.items():
        print(f"  {labels.get(key, key.replace('_', ' ').title())}: {value}")
    try:
        from backend.ui_theme import interactive_yes_no

        approved = bool(interactive_yes_no("Allow this action?", default_yes=False))
        return ApprovalDecision(approved, "user_approved" if approved else "user_denied")
    except (EOFError, KeyboardInterrupt, SystemExit):
        return ApprovalDecision(False, "input_cancelled")
    except Exception:
        return ApprovalDecision(False, "input_error")


@contextmanager
def approval_scope(
    *,
    handler: ApprovalHandler | None = None,
    interface: str | None = None,
    session_log_path: Path | None = None,
) -> Iterator[None]:
    tokens = []
    if handler is not None:
        tokens.append((_handler, _handler.set(handler)))
    if interface is not None:
        tokens.append((_interface, _interface.set(interface)))
    if session_log_path is not None:
        tokens.append((_session_log_path, _session_log_path.set(session_log_path)))
    try:
        yield
    finally:
        for variable, token in reversed(tokens):
            variable.reset(token)


def request_approval(tool: str, summary: str, details: Mapping[str, object], capability: str) -> bool:
    request = ApprovalRequest(
        id=str(uuid.uuid4()),
        tool=_safe_text(tool, limit=120),
        summary=_safe_text(summary, limit=300),
        details=sanitize_details(details),
        capability=_safe_text(capability, limit=120),
    )
    active_handler = _handler.get() or terminal_approval_handler
    try:
        raw_decision = active_handler(request)
        decision = raw_decision if isinstance(raw_decision, ApprovalDecision) else ApprovalDecision(bool(raw_decision), "user_approved" if raw_decision else "user_denied")
    except Exception:
        decision = ApprovalDecision(False, "handler_error")

    log_path = _session_log_path.get()
    if log_path is not None:
        append_session_event(log_path, {
            "type": "tool_approval",
            "tool": request.tool,
            "capability": request.capability,
            "approved": decision.approved,
            "interface": _interface.get(),
            "reason": decision.reason,
        })
    return decision.approved
