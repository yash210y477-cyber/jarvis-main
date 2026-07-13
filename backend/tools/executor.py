from tools.registry import ToolRegistry


class ActionExecutor:

    def __init__(self, registry: ToolRegistry):

        self.registry = registry

    def execute(self, tool_name, **kwargs):

        tool = self.registry.get(tool_name)

        if tool is None:

            return {

                "success": False,

                "error": f"Tool '{tool_name}' not found."

            }

        handler = tool["handler"]

        try:

            result = handler(**kwargs)

            return {

                "success": True,

                "tool": tool_name,

                "result": result

            }

        except Exception as e:

            return {

                "success": False,

                "tool": tool_name,

                "error": str(e)

            }