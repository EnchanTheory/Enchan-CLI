import inspect
from typing import Callable, Any, Dict, Optional, TypeVar, List

F = TypeVar('F', bound=Callable[..., Any])

class CLICommand:
    def __init__(self, trigger: str, desc: str, handler: Callable, usage: str = ""):
        self.trigger = trigger
        self.desc = desc
        self.handler = handler
        self.usage = usage

class AgentTool:
    def __init__(self, name: str, desc: str, handler: Callable, schema: Optional[Dict[str, Any]] = None):
        self.name = name
        self.desc = desc
        self.handler = handler
        self.schema = schema or self._generate_schema(handler)

    def _generate_schema(self, func: Callable) -> Dict[str, Any]:
        """Type Hinting and Docstrings to automatically generate AI-compatible JSON Schema."""
        sig = inspect.signature(func)
        doc = inspect.getdoc(func) or ""
        
        parameters = {}
        required = []
        
        for name, param in sig.parameters.items():
            if name in ("self", "ctx"):  # Skip special contextual params
                continue
            
            # Simple PyType to JsonType mapper
            py_type = param.annotation
            json_type = "string"
            if py_type is int:
                json_type = "integer"
            elif py_type is float:
                json_type = "number"
            elif py_type is bool:
                json_type = "boolean"
            elif py_type is list:
                json_type = "array"
            elif py_type is dict:
                json_type = "object"
                
            parameters[name] = {
                "type": json_type,
                "description": f"Argument '{name}'"
            }
            if param.default is inspect.Parameter.empty:
                required.append(name)
                
        return {
            "name": self.name,
            "description": doc.split("\n")[0] if doc else self.desc,
            "parameters": {
                "type": "object",
                "properties": parameters,
                "required": required
            }
        }

class ZenRegistry:
    """Zen-like Unified Registry for Commands and Agent Tools."""
    def __init__(self):
        self.commands: Dict[str, CLICommand] = {}
        self.tools: Dict[str, AgentTool] = {}

    def command(self, trigger: str, desc: str, usage: str = "") -> Callable[[F], F]:
        """Decorator to register a CLI Slash Command."""
        def decorator(func: F) -> F:
            self.commands[trigger] = CLICommand(trigger, desc, func, usage)
            return func
        return decorator

    def tool(self, name: str, desc: str) -> Callable[[F], F]:
        """Decorator to register an Agent Tool."""
        def decorator(func: F) -> F:
            self.tools[name] = AgentTool(name, desc, func)
            return func
        return decorator

registry = ZenRegistry()
