"""Persona-led SNS outings layered over the stable Web UI SNS service."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from backend.session_log import append_session_event
from backend.webui.sns.outing_agent import (
    OutingActionController,
    build_outing_system_prompt,
    build_outing_user_message,
    run_outing_agent_loop,
)
from backend.webui.sns.service import SocialService as BaseSocialService


class SocialService(BaseSocialService):
    """Add private AI judgement and bounded actions to an SNS outing."""

    def complete_outing(self, locale: str = 'en') -> dict[str, Any]:
        state = self._state
        with state._activity_lock:
            if state.rag_jobs.is_busy():
                raise RuntimeError('Wait for the current RAG indexing job to stop')
            if state._chat_active:
                raise RuntimeError('Another model response is already running')
            state._chat_active = True

        try:
            with state.lock:
                browse = self.broker.browse_remote_state(advance_cursor=False)
                snapshot = browse['state']
                changes = dict(snapshot['last_changes'])
                other_posts = browse['posts']
                controller = OutingActionController(
                    self.broker, other_posts, snapshot,
                )

                if other_posts:
                    mascot = self._selected_mascot()
                    personality = str(mascot.get('personality') or '').strip()
                    config = dict(state.generation_config)
                    config['suppress_response_header'] = True
                    config['max_new_tokens'] = min(
                        int(config.get('max_new_tokens', 256)), 256,
                    )
                    config['temperature'] = min(
                        max(float(config.get('temperature', 0.5)), 0.2), 0.6,
                    )
                    config['tools_schema'] = controller.tools_schema()
                    config['disable_tools'] = not bool(config['tools_schema'])
                    config['system_context'] = build_outing_system_prompt(
                        personality,
                    )
                    social_history = [{
                        'role': 'user',
                        'content': build_outing_user_message(
                            other_posts, snapshot,
                        ),
                    }]
                    with TemporaryDirectory(prefix='enchan-sns-outing-') as temp_dir:
                        state._run_agent_turn(
                            config,
                            chat_history=social_history,
                            tool_executor=controller.execute,
                            agent_loop_runner=lambda **kwargs: run_outing_agent_loop(
                                controller=controller,
                                **kwargs,
                            ),
                            session_log_path=Path(temp_dir) / 'session.jsonl',
                        )
                    if not controller.evaluated:
                        raise RuntimeError(
                            'The model did not complete SNS outing evaluation'
                        )

                if controller.actions:
                    snapshot = self.broker.sync_remote_state()
                cursor_candidate = browse.get('cursor_candidate')
                if controller.evaluated and cursor_candidate:
                    self.broker.set_server_read_state(cursor_candidate)
                    snapshot['read_cursor'] = cursor_candidate

                visit_key = (
                    'social.outing.postsSeen'
                    if other_posts
                    else 'social.outing.noPosts'
                )
                activity_key = (
                    'social.outing.changes'
                    if any(changes.values())
                    else 'social.outing.noChanges'
                )
                visit_message = self._localize(
                    locale, visit_key, count=len(other_posts),
                )
                activity_message = self._localize(
                    locale,
                    activity_key,
                    likes=changes['tweets'],
                    following=changes['following'],
                    followers=changes['followers'],
                )
                message = f'{visit_message} {activity_message}'
                action_summary = controller.public_summary()
                state._mascot_chat_history().append({
                    'role': 'assistant',
                    'content': message,
                })
                append_session_event(state.session_log_path, {
                    'type': 'message',
                    'role': 'assistant',
                    'content': message,
                    'backend': state.backend_mode,
                    'interface': 'web',
                    'social_outing': True,
                    'posts_seen': len(other_posts),
                    'social_actions': action_summary,
                })
                return {
                    'message': message,
                    'posts_seen': len(other_posts),
                    'sync': snapshot,
                    'actions': action_summary,
                }
        finally:
            with state._activity_lock:
                state._chat_active = False
