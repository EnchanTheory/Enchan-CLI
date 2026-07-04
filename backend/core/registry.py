from typing import Callable, Any, Dict, TypeVar

F = TypeVar('F', bound=Callable[..., Any])

class CLICommand:
    def __init__(self, trigger: str, desc: str, handler: Callable, usage: str = ""):
        self.trigger = trigger
        self.desc = desc
        self.handler = handler
        self.usage = usage

class ZenRegistry:
    """Zen-like Registry for CLI commands."""
    def __init__(self):
        self.commands: Dict[str, CLICommand] = {}

    def command(self, trigger: str, desc: str, usage: str = "") -> Callable[[F], F]:
        """Decorator to register a CLI Slash Command."""
        def decorator(func: F) -> F:
            self.commands[trigger] = CLICommand(trigger, desc, func, usage)
            return func
        return decorator

registry = ZenRegistry()
