from typing import Dict, Any

class ToolRegistry:
    """KidOS Core: Tool Execution Environment Control."""
    def __init__(self):
        self._tools: Dict[str, Any] = {}
        
    def register(self, tool_name: str, tool_instance: Any) -> None:
        """Mount a software component as an accessible environment tool."""
        self._tools[tool_name] = tool_instance
        
    def get_tool(self, tool_name: str) -> Any:
        """Locally fetch attached software components."""
        if tool_name not in self._tools:
            if tool_name == "comfyui":
                from kidos.tools.comfyui_tool import ComfyUITool
                self._tools[tool_name] = ComfyUITool()
            elif tool_name == "tts":
                from kidos.tools.tts_tool import TTSTool
                self._tools[tool_name] = TTSTool()
        return self._tools.get(tool_name)

tool_registry = ToolRegistry()
