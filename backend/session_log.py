import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


SESSION_LOG_DIR = Path(__file__).resolve().parent.parent / "logs" / "sessions"


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_session_event(log_path: Path, event: dict) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"ts": now_utc_iso(), **event}
    with log_path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def session_log_name() -> str:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{stamp}-{uuid.uuid4().hex[:8]}.jsonl"


def new_session_log_path() -> Path:
    return SESSION_LOG_DIR / session_log_name()


def list_session_logs(current_log_path: Optional[Path] = None, limit: int = 10) -> list[Path]:
    if not SESSION_LOG_DIR.exists():
        return []
    logs = sorted(SESSION_LOG_DIR.glob("*.jsonl"), key=lambda path: path.stat().st_mtime, reverse=True)
    if current_log_path is not None:
        current_resolved = current_log_path.resolve()
        logs = [path for path in logs if path.resolve() != current_resolved]
    return logs[:limit]


def resolve_session_log(ref: str, current_log_path: Path) -> Optional[Path]:
    ref = ref.strip()
    if not ref or ref.lower() == "latest":
        logs = list_session_logs(current_log_path=current_log_path, limit=1)
        return logs[0] if logs else None
        
    # Support index-based resolution (e.g., "/resume 1")
    if ref.isdigit():
        idx = int(ref) - 1
        logs = list_session_logs(current_log_path=current_log_path, limit=20)
        if 0 <= idx < len(logs):
            return logs[idx]
        return None
        
    candidate = Path(ref.strip("\"'"))
    if candidate.exists():
        return candidate
    candidate = SESSION_LOG_DIR / ref
    if candidate.exists():
        return candidate
    if not candidate.name.endswith(".jsonl"):
        candidate = SESSION_LOG_DIR / f"{ref}.jsonl"
        if candidate.exists():
            return candidate
    return None


def get_session_metadata(log_path: Path) -> dict:
    """Parses a session JSONL file to extract turn counts, last active timestamp, and query preview."""
    meta = {
        "path": log_path,
        "name": log_path.name,
        "last_active": "Unknown",
        "turns": 0,
        "preview": "No messages"
    }
    
    try:
        # Fallback to file system modification time
        mtime = log_path.stat().st_mtime
        meta["last_active"] = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
    except Exception:
        pass

    try:
        messages = []
        last_ts = None
        with log_path.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    event = json.loads(line)
                except Exception:
                    continue
                
                if "ts" in event:
                    last_ts = event["ts"]
                    
                if event.get("type") == "message":
                    role = event.get("role")
                    content = event.get("content")
                    if role in {"user", "model", "assistant"} and isinstance(content, str):
                        messages.append({"role": role, "content": content})
                        
        if last_ts:
            try:
                # Parse UTC ISO and convert to clean local timezone representation
                dt = datetime.fromisoformat(last_ts)
                meta["last_active"] = dt.astimezone().strftime("%Y-%m-%d %H:%M")
            except Exception:
                pass
                
        user_msgs = [m for m in messages if m["role"] == "user"]
        meta["turns"] = len(user_msgs)
        
        if user_msgs:
            first_user_content = user_msgs[0]["content"].strip()
            # Clean agent prompts by stripping up to "Goal:\n"
            if "Goal:\n" in first_user_content:
                first_user_content = first_user_content.split("Goal:\n", 1)[1]
            
            preview = first_user_content.replace("\n", " ").strip()
            if len(preview) > 40:
                preview = preview[:37] + "..."
            meta["preview"] = f'"{preview}"'
            
    except Exception:
        pass
        
    return meta


def load_session_messages(log_path: Path) -> list[dict]:
    messages = []
    with log_path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") == "message":
                role = event.get("role")
                content = event.get("content")
                if role in {"user", "model", "assistant"} and isinstance(content, str):
                    messages.append({"role": role, "content": content})
    return messages
