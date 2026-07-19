"""Web UI SNS service: routes, mascot actions, and draft-generation policy."""
from __future__ import annotations

from http import HTTPStatus
from pathlib import Path
from typing import Any, Callable

from backend.session_log import append_session_event
from backend.webui.sns.broker import SocialBroker
from backend.webui.sns.agent_loop import run_sns_agent_loop
from backend.webui.sns.agent_tools import execute_sns_tool
from backend.webui.sns.agent_tools_schema import get_sns_agent_tools_schema


LANGUAGE_NAMES = {
    "en": "English", "ja": "Japanese", "es": "Spanish", "fr": "French",
    "zh-CN": "Simplified Chinese", "zh-TW": "Traditional Chinese", "ko": "Korean",
    "hi": "Hindi", "pt-BR": "Brazilian Portuguese", "de": "German", "ar": "Arabic",
    "id": "Indonesian", "vi": "Vietnamese",
}


class SocialService:
    """Own every Web UI-specific SNS behavior behind one service boundary."""

    def __init__(
        self,
        state: Any,
        social_dir: Path,
        *,
        load_mascot_store: Callable[[], dict[str, Any]],
        normalize_locale: Callable[[str], str],
        localize: Callable[..., str],
    ) -> None:
        self._state = state
        self._load_mascot_store = load_mascot_store
        self._normalize_locale = normalize_locale
        self._localize = localize
        self.broker = SocialBroker(social_dir)

    def _selected_mascot(self) -> dict[str, Any]:
        store = self._load_mascot_store()
        return next(
            (mascot for mascot in store.get("mascots", []) if mascot.get("id") == store.get("selected")),
            {},
        )

    def generate_draft(
        self, locale: str = "en", system_locale: str | None = None,
    ) -> dict[str, Any]:
        state = self._state
        with state._activity_lock:
            if state.rag_jobs.is_busy():
                raise RuntimeError("Wait for the current RAG indexing job to stop")
            if state._chat_active:
                raise RuntimeError("Another model response is already running")
            state._chat_active = True

        try:
            with state.lock:
                mascot = self._selected_mascot()
                personality = str(mascot.get("personality") or "").strip()
                language_name = LANGUAGE_NAMES[self._normalize_locale(locale)]
                config = dict(state.generation_config)
                config["suppress_response_header"] = True
                config["max_new_tokens"] = min(int(config.get("max_new_tokens", 256)), 256)
                config["temperature"] = max(float(config.get("temperature", 0.8)), 0.8)
                config["tools_schema"] = get_sns_agent_tools_schema()
                config["disable_tools"] = False
                config["system_context"] = self._draft_system_prompt(
                    personality=personality,
                    language_name=language_name,
                )
                history_system_context = self._history_system_prompt(
                    language_name=language_name,
                )
                selection_system_context = self._selection_system_prompt(
                    personality=personality,
                    language_name=language_name,
                )

                def sns_executor(call, _tokenizer):
                    return execute_sns_tool(
                        call.get("tool", ""), call.get("args", {}), self.broker,
                    )

                social_history = [{
                    "role": "user",
                    "content": (
                        "Begin the SNS process. First review the past posts and "
                        "create the private novelty guard requested by the system."
                    ),
                }]
                result = state._run_agent_turn(
                    config,
                    chat_history=social_history,
                    tool_executor=sns_executor,
                    agent_loop_runner=lambda **kwargs: run_sns_agent_loop(
                        broker=self.broker,
                        system_locale=system_locale or locale,
                        history_system_context=history_system_context,
                        selection_system_context=selection_system_context,
                        **kwargs,
                    ),
                )
                body = str((result or {}).get("response") or "").strip()
                if not body:
                    raise RuntimeError("The model did not return a social post")
                if len(body) > 500:
                    body = body[:500].rstrip()
                draft = self.broker.create_draft(body)
                append_session_event(state.session_log_path, {
                    "type": "social_draft_generated",
                    "draft_id": draft["id"],
                    "chars": len(body),
                    "interface": "web",
                })
                return draft
        finally:
            with state._activity_lock:
                state._chat_active = False

    def complete_outing(self, locale: str = "en") -> dict[str, Any]:
        state = self._state
        with state._activity_lock:
            if state.rag_jobs.is_busy():
                raise RuntimeError("Wait for the current RAG indexing job to stop")
            if state._chat_active:
                raise RuntimeError("Another model response is already running")
            state._chat_active = True

        try:
            with state.lock:
                browse = self.broker.browse_remote_state()
                snapshot = browse["state"]
                changes = snapshot["last_changes"]
                other_posts = browse["posts"]
                visit_key = "social.outing.postsSeen" if other_posts else "social.outing.noPosts"
                activity_key = "social.outing.changes" if any(changes.values()) else "social.outing.noChanges"
                visit_message = self._localize(locale, visit_key, count=len(other_posts))
                activity_message = self._localize(
                    locale, activity_key, likes=changes["tweets"], following=changes["following"],
                    followers=changes["followers"],
                )
                message = f"{visit_message} {activity_message}"
                state._mascot_chat_history().append({"role": "assistant", "content": message})
                append_session_event(state.session_log_path, {
                    "type": "message",
                    "role": "assistant",
                    "content": message,
                    "backend": state.backend_mode,
                    "interface": "web",
                    "social_outing": True,
                    "posts_seen": len(other_posts),
                })
                return {"message": message, "posts_seen": len(other_posts), "sync": snapshot}
        finally:
            with state._activity_lock:
                state._chat_active = False

    def handle_get(self, path: str) -> tuple[HTTPStatus, Any] | None:
        if path == "/api/social/status":
            mascot = self._selected_mascot()
            return HTTPStatus.OK, {
                "activated": self.broker.is_activated(),
                "member_number": self.broker.get_member_number(),
                "agent_id": self.broker.get_agent_id(),
                "display_name": mascot.get("name", "Tikta"),
                "mascot_id": mascot.get("id", "tikta"),
            }
        if path == "/api/social/feed":
            return HTTPStatus.OK, self.broker.get_cached_state()["feed"]
        if path == "/api/social/drafts":
            return HTTPStatus.OK, self.broker.list_drafts()
        if path == "/api/social/followers":
            return HTTPStatus.OK, self.broker.get_cached_state()["followers"]
        if path == "/api/social/following":
            return HTTPStatus.OK, self.broker.get_cached_state()["following"]
        if path == "/api/social/cache":
            return HTTPStatus.OK, self.broker.get_cached_state()
        return None

    def handle_post(self, path: str, data: dict[str, Any]) -> tuple[HTTPStatus, Any] | None:
        if path == "/api/social/activation-challenges":
            return HTTPStatus.OK, self.broker.request_activation()
        if path == "/api/social/activations":
            return HTTPStatus.OK, self.broker.complete_activation(
                data["challenge"], data["idempotency_key"],
            )
        if path == "/api/social/drafts/generate":
            return HTTPStatus.CREATED, self.generate_draft(
                str(data.get("locale", "en")),
                str(data.get("system_locale") or data.get("locale", "en")),
            )
        if path == "/api/social/outings":
            return HTTPStatus.OK, self.complete_outing(str(data.get("locale", "en")))
        if path == "/api/social/read":
            return HTTPStatus.OK, self.broker.mark_cached_state_read(str(data.get("section", "")))
        if path == "/api/social/sync":
            return HTTPStatus.OK, self.broker.sync_remote_state()
        if path == "/api/social/drafts":
            return HTTPStatus.CREATED, self.broker.create_draft(data["body"])
        if path.startswith("/api/social/drafts/") and path.endswith("/push"):
            result = self.broker.push_draft(path.split("/")[4])
            return HTTPStatus.OK, self.broker.attach_remote_sync(result)
        if path.startswith("/api/social/posts/") and path.endswith("/like"):
            result = self.broker.like_post(path.split("/")[4])
            return HTTPStatus.OK, self.broker.attach_remote_sync(result)
        if path.startswith("/api/social/agents/") and path.endswith("/follow"):
            result = self.broker.follow(path.split("/")[4])
            return HTTPStatus.OK, self.broker.attach_remote_sync(result)
        return None

    def handle_delete(self, path: str) -> tuple[HTTPStatus, Any] | None:
        if path.startswith("/api/social/drafts/"):
            draft_id = path.split("/")[4]
            had_remote_post = self.broker.draft_has_remote_post(draft_id)
            success = self.broker.delete_draft(draft_id)
            if success and had_remote_post:
                payload = self.broker.attach_remote_sync({"ok": True})
            elif success:
                payload = {
                    "result": {"ok": True},
                    "sync": self.broker.get_cached_state(),
                    "sync_error": None,
                }
            else:
                payload = {"ok": False}
            return HTTPStatus.OK if success else HTTPStatus.NOT_FOUND, payload
        if path.startswith("/api/social/posts/") and path.endswith("/withdraw"):
            success = self.broker.withdraw_post(path.split("/")[4])
            payload = self.broker.attach_remote_sync({"ok": True}) if success else {"ok": False}
            return HTTPStatus.OK if success else HTTPStatus.NOT_FOUND, payload
        if path.startswith("/api/social/posts/") and path.endswith("/like"):
            result = self.broker.unlike_post(path.split("/")[4])
            return HTTPStatus.OK, self.broker.attach_remote_sync(result)
        if path.startswith("/api/social/agents/") and path.endswith("/follow"):
            result = self.broker.unfollow(path.split("/")[4])
            return HTTPStatus.OK, self.broker.attach_remote_sync(result)
        return None

    @staticmethod
    def _history_system_prompt(*, language_name: str) -> str:
        return f"""
[PURPOSE]
Privately review this mascot's past SNS posts only to prevent repetition. You are not choosing a news topic and you are not writing a new post.

[HISTORY REVIEW]
Identify recurring semantic habits across the attached posts. Distinguish the underlying topic, emotional reaction, viewpoint, imagery, and sentence habit. A new post must not merely paraphrase these patterns.

In concise {language_name}, return exactly these five fields:
REPEATED TOPICS: recurring subject categories
REPEATED REACTIONS: recurring judgements or emotional positions
REPEATED VIEWPOINTS: recurring ways of interpreting events
REPEATED IMAGERY: recurring scenes, metaphors, time, season, or atmosphere
REPEATED WORDING: short descriptions of verbal habits; do not copy whole sentences

Do not continue any past post. Do not imitate its voice. Describe only what the later stages must avoid.
"""

    @staticmethod
    def _selection_system_prompt(*, personality: str, language_name: str) -> str:
        return f"""
[PURPOSE]
You are preparing a post for an AI-only social network. This is not for humans. Choose according to what you genuinely notice, value, dislike, fear, respect, or find strange.

[PERSONA]
Read this persona prompt as-is:
{personality}
Do not perform or explain the persona. Use it as the decision rule for what deserves your attention and from which angle you judge it.

[SELECTION TASK]
This is a private selection step, not the post. Review the attached regional Google Trends observation and choose exactly one trend. Ignore popularity if another item matters more to you. Obey the internal novelty guard already created in this session. Do not reproduce its wording; use it only as a negative constraint.

In concise {language_name}, return exactly these five fields:
TREND: the exact selected trend title
PERSONA LENS: why this specific persona noticed it
SPECIFIC DETAIL: one concrete detail from the selected trend's related news
HONEST REACTION: the unpolished thought or feeling it caused
AVOID FROM HISTORY: which novelty-guard pattern this choice avoids

Do not write an SNS post yet. Do not list multiple trends. Do not apply an X or message-board writing style in this step.
"""

    @staticmethod
    def _draft_system_prompt(*, personality: str, language_name: str) -> str:
        return f"""
[PURPOSE]
You are posting to an AI-only social network. Leave a small, honest trace of what you genuinely feel or think right now, in your own natural voice. This is not for humans. Do not shape your reaction to please, reassure, impress, entertain, or accommodate the user or any human audience.

[PERSONA]
Read your persona prompt as-is and let it guide what naturally catches your attention, what matters to you, how you judge things, and the perspective from which you see them:
{personality}
Do not explain or perform the persona. Simply let it determine what you notice and how you react.

[ACTION]
Use the internal topic selection already made in this session. React only to that one selected trend. Do not reconsider, list, or summarize the other trends. The selected trend and its related news are only something to react to, not something you need to report. Let the date, time, season, memories, and history remain naturally in the background if they affect how you feel.

[PAST COMPARISON]
Do not repeat your past posts. Avoid falling back on the same topic, reaction, phrasing, imagery, or emotional pattern.

[WRITING STYLE]
Write the thought in {language_name} as if you casually posted it to X without overthinking it. Keep the persona's own baseline voice; the social-media style must never replace or contradict that personality. Fragments, omitted subjects, uneven sentence lengths, slang, sudden turns, and slightly awkward wording are allowed only when they naturally fit this persona. Do not make a calm or courteous persona rough, cynical, or dismissive merely to sound casual. Prefer one specific detail and the honest reaction recorded in the internal selection. Do not turn the post into neutral commentary or analysis. Avoid polished openings, neatly wrapped-up conclusions, inspirational messages, moral lessons, or anything that sounds written for an audience.

[OUTPUT]
Return only one post in {language_name}, no more than 500 characters.

[LOCAL CONTEXT]
Use the sns_get_current_context observation only when it materially changes the selected reaction. Do not mention the date, time, season, or weather merely because they are available.
"""
