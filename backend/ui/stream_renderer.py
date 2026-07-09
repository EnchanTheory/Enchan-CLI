import sys
from rich.live import Live
from rich.markdown import Markdown
from rich.text import Text
from rich.spinner import Spinner

# Import ALL unified console, theme specifications, and color palette from theme module
from backend.ui.theme import console, DEFAULT_BORDER, MUTED_BORDER, DEFAULT_BODY, DEFAULT_BG, DEFAULT_CODE_THEME, ENCHAN_MARKDOWN_THEME

class RichStreamRenderer:
    """
    Windows/Mac/Linux multi-platform compatible
    modern real-time Markdown streaming renderer.
    Renders raw, beautifully styled Markdown and thought logs directly as text,
    without any bulky panel borders or double title headers for a natural chat experience.
    """
    def __init__(self, title="Enchan AI", border_style=DEFAULT_BORDER, thinking_style=None):
        # Share the exact same console instance defined in panels.py to avoid terminal buffer drift.
        self.console = console
        self.title = title
        self.border_style = border_style
        
        # Inject the elegant gold theme directly into the shared console dynamically
        self.console.push_theme(ENCHAN_MARKDOWN_THEME)
        
        # Use existing theme colors for consistency
        self.thinking_style = thinking_style or f"italic {MUTED_BORDER}"
        
        # Internal state
        self.thinking_text = ""
        self.content_text = ""
        self.live = None
        self.status = "thinking"  # "thinking" or "responding" or "finished"

    def _sanitize_markdown(self, text: str) -> str:
        """
        Temporarily completes incomplete Markdown syntax during streaming
        (e.g., unclosed code blocks) to prevent layout distortion.
        """
        backtick_count = text.count("```")
        if backtick_count % 2 != 0:
            return text + "\n```"
        return text

    def _build_renderable(self):
        """
        Constructs the Renderable object without any Panel borders.
        Returns a Group of custom rich objects (Markdown/Text) to stream cleanly on the terminal.
        """
        content_parts = []

        # 1. Render thought process (Thinking phase)
        if self.thinking_text:
            header_text = Text()
            if self.status == "thinking":
                header_text.append("🧠 Thinking...\n", style=f"bold {self.border_style}")
            else:
                header_text.append("🧠 Thought Process (Completed):\n", style="bold dim")
            
            # Show thought process using the identical MUTED_BORDER gray
            header_text.append(self.thinking_text, style=self.thinking_style)
            
            # Add a separator if the main content is also starting
            if self.content_text:
                header_text.append("\n\n---\n\n")
            
            content_parts.append(header_text)

        # 2. Render main content (Markdown response body)
        if self.content_text:
            sanitized = self._sanitize_markdown(self.content_text)
            
            # We explicitly enforce the centralized default code theme to eliminate the default light/white background.
            # The theme replaces raw, neon colors with beautifully muted, dusty earth tones that perfectly blend
            # into the Enchan aesthetic, while keeping a soft, dark-gold background plate.
            md = Markdown(sanitized, code_theme=DEFAULT_CODE_THEME)
            content_parts.append(md)
        elif self.status == "thinking" and not self.thinking_text:
            # Match the spinner style and color with the existing get_spinner_status implementation
            spinner_text = Text("Thinking...", style=f"italic {MUTED_BORDER}")
            content_parts.append(Spinner("dots", text=spinner_text, style=MUTED_BORDER))

        # Combine all parts directly into a Group without any surrounding Panel or border.
        from rich.console import Group
        return Group(*content_parts) if content_parts else Text()

    def start(self):
        """
        Starts the real-time streaming display.
        """
        self.live = Live(
            self._build_renderable(),
            console=self.console,
            refresh_per_second=12,
            transient=False
        )
        self.live.start()

    def update_thinking(self, token: str):
        """
        Appends a thinking token and updates the screen.
        """
        self.status = "thinking"
        self.thinking_text += token
        if self.live:
            self.live.update(self._build_renderable())

    def update_content(self, token: str):
        """
        Appends a content token and updates the screen.
        """
        self.status = "responding"
        self.content_text += token
        if self.live:
            self.live.update(self._build_renderable())

    def finish(self):
        """
        Stops the real-time display and finalizes the render.
        """
        self.status = "finished"
        if self.live:
            self.live.update(self._build_renderable())
            self.live.stop()
            self.live = None
            
            # Safely pop the theme after finishing to clean up console state
            try:
                self.console.pop_theme()
            except Exception:
                pass
export_stream_renderer = RichStreamRenderer
