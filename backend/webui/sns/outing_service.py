"""Persona-led SNS outings layered over the stable Web UI SNS service."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from backend.webui.sns.outing_agent import (
    OutingActionController,
    build_outing_system_prompt,
    build_outing_user_message,
    run_outing_agent_loop,
)
from backend.webui.sns.service import (
    LANGUAGE_NAMES,
    SocialService as BaseSocialService,
)


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
                other_posts = browse['posts']
                controller = OutingActionController(
                    self.broker, other_posts, snapshot,
                )

                mascot = self._selected_mascot()
                personality = str(mascot.get('personality') or '').strip()
                language_name = LANGUAGE_NAMES[
                    self._normalize_locale(locale)
                ]
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
                    language_name,
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
                    posts_by_id = {
                        str(post.get('id') or ''): post
                        for post in other_posts
                        if isinstance(post, dict) and post.get('id')
                    }
                    people_by_id = {
                        str(post.get('agent_id') or ''): post
                        for post in other_posts
                        if isinstance(post, dict) and post.get('agent_id')
                    }
                    for action in controller.actions:
                        action_type = action.get('action')
                        if action_type == 'like':
                            post_id = str(action.get('post_id') or '')
                            self._remember_liked_post(
                                posts_by_id.get(post_id, {'id': post_id}),
                                liked=True,
                                source='outing',
                            )
                        elif action_type in {'follow', 'unfollow'}:
                            agent_id = str(action.get('agent_id') or '')
                            self._remember_relationship(
                                people_by_id.get(
                                    agent_id, {'agent_id': agent_id},
                                ),
                                followed=action_type == 'follow',
                                source='outing',
                            )
                cursor_candidate = browse.get('cursor_candidate')
                if controller.evaluated and cursor_candidate:
                    self.broker.set_server_read_state(cursor_candidate)
                    snapshot['read_cursor'] = cursor_candidate
                    
                message = ""
                for msg in reversed(social_history):
                    if msg.get('role') == 'assistant' and msg.get('content'):
                        message = str(msg['content']).strip()
                        break
                        
                if not message:
                    raise RuntimeError(
                        'The model did not describe its SNS outing'
                    )
                
                action_summary = controller.public_summary()
                state._mascot_chat_history().append({
                    'role': 'assistant',
                    'content': message,
                })
                self._append_social_memory(
                    'social_outing', message,
                    social_outing=True,
                    posts_seen=len(other_posts),
                    social_actions=action_summary,
                )
                return {
                    'message': message,
                    'posts_seen': len(other_posts),
                    'sync': snapshot,
                    'actions': action_summary,
                }
        finally:
            with state._activity_lock:
                state._chat_active = False
