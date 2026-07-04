from backend.core import registry

# Explicitly import all command modules to trigger decorator evaluation and self-registration.
import backend.commands.general
import backend.commands.session
import backend.commands.model
import backend.commands.agent

__all__ = ["registry"]
