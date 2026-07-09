import sys
from typing import Optional

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.completion import Completer, Completion
    PROMPT_TOOLKIT_AVAILABLE = True
except ImportError:
    PROMPT_TOOLKIT_AVAILABLE = False

from backend.ui_theme import make_prompt_style
from backend.slash_commands import COMMAND_COMPLETIONS


class EnchanCompleter(Completer):
    def __init__(self):
        self.completions = COMMAND_COMPLETIONS

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        if not text.startswith("/"):
            return

        parts = text.split()
        if not parts:
            return

        if len(parts) == 1 and not text.endswith(" "):
            word = parts[0]
            for cmd, (desc, _) in self.completions.items():
                if cmd.startswith(word):
                    yield Completion(cmd, start_position=-len(word), display_meta=desc)
        elif len(parts) >= 1:
            cmd = parts[0]
            if cmd in self.completions:
                _, sub_dict = self.completions[cmd]
                if sub_dict:
                    word = parts[1] if (len(parts) > 1 and not text.endswith(" ")) else ""
                    start_pos = -len(word) if word else 0
                    for sub, (sub_desc, _) in sub_dict.items():
                        if not word or sub.startswith(word):
                            yield Completion(sub, start_position=start_pos, display_meta=sub_desc)


def create_interactive_session(slash_commands: tuple) -> Optional[PromptSession]:
    """Builds and returns a PromptSession configured with keybindings and autocomplete completer."""
    if not PROMPT_TOOLKIT_AVAILABLE:
        return None

    kb = KeyBindings()

    @kb.add('/')
    def _(event):
        buffer = event.current_buffer
        start_of_input = not buffer.document.text_before_cursor
        buffer.insert_text('/')
        if start_of_input:
            buffer.start_completion(select_first=False)

    @kb.add('enter')
    def _(event):
        buffer = event.current_buffer
        if buffer.complete_state and buffer.complete_state.current_completion:
            completion = buffer.complete_state.current_completion
            buffer.apply_completion(completion)
            if str(completion.text).startswith("/"):
                buffer.validate_and_handle()
            return

        text = buffer.text.strip()
        if text.startswith("/") and " " not in text:
            matches = [cmd for cmd in slash_commands if cmd.startswith(text)]
            if len(matches) == 1 and matches[0] != text:
                buffer.text = matches[0]
                buffer.cursor_position = len(buffer.text)
                buffer.validate_and_handle()
                return

        import ctypes
        is_shift = False
        try:
            is_shift = (ctypes.windll.user32.GetAsyncKeyState(0x10) & 0x8000) != 0
        except Exception:
            pass

        if is_shift:
            buffer.insert_text('\n')
        else:
            buffer.validate_and_handle()

    @kb.add('escape', 'enter')
    def _(event):
        """Insert a newline for Alt/Option+Enter terminals that send ESC+Enter."""
        event.current_buffer.insert_text('\n')

    @kb.add('tab')
    def _(event):
        buffer = event.current_buffer
        if buffer.complete_state and buffer.complete_state.current_completion:
            buffer.apply_completion(buffer.complete_state.current_completion)
        else:
            buffer.start_completion(select_first=True)

    @kb.add('c-j')
    def _(event):
        event.current_buffer.insert_text('\n')

    style = make_prompt_style()
    completer = EnchanCompleter()

    return PromptSession(
        key_bindings=kb,
        style=style,
        completer=completer,
        complete_while_typing=True,
        reserve_space_for_menu=6
    )