from typing import Dict, Any

class ModelRegistry:
    """KidOS Core: Process Model Registry."""
    def __init__(self):
        self._models: Dict[str, Any] = {}
        
    def register(self, name: str, model_instance: Any) -> None:
        """Register a new LLM interface."""
        self._models[name] = model_instance
        
    def get_model(self, model_name: str = "default") -> Any:
        """Fetch an LLM interface from OS configuration."""
        if model_name not in self._models:
            from kidos.tools.ollama_tool import OllamaTool
            self._models[model_name] = OllamaTool()
        return self._models[model_name]

model_registry = ModelRegistry()
