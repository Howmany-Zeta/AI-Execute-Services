from aiecs.tools import register_tool
from aiecs.tools.base_tool import BaseTool

@register_tool("search_api")
class SearchAPITool(BaseTool):
    def run(self, query):
        return f"[Search results for '{query}']"
