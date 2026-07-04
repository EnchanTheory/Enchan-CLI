from typing import Protocol, Generator, List, Dict, Any

class BackendProvider(Protocol):
    """Structural interface definition for all inference engines (Ollama, llama.cpp, etc.)."""
    
    def generate_stream(self, prompt: str, config: Any) -> Generator[str, None, None]:
        """Generates raw text tokens from a prompt in a streaming fashion."""
        ...

    def tokenize(self, text: str) -> List[int]:
        """Converts raw text into a sequence of token IDs."""
        ...

    def detokenize(self, tokens: List[int]) -> str:
        """Converts token IDs back into raw text."""
        ...
        
    def get_status(self) -> Dict[str, Any]:
        """Retrieves runtime engine status and active loaded model metadata."""
        ...
