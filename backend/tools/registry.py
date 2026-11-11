"""Registry of callable tools.

Every tool carries the JSON schema handed to an AI provider and a permission
level: "auto" tools run immediately, "confirm" tools need the user's approval.
"""

AUTO = "auto"
CONFIRM = "confirm"


class ToolRegistry:

    def __init__(self):

        self.tools = {}

    def register(
        self,
        name,
        handler,
        description="",
        schema=None,
        permission=AUTO,
        category="general",
        examples=None,
    ):

        if permission not in (AUTO, CONFIRM):
            raise ValueError(f"Unknown permission level: {permission}")

        self.tools[name] = {
            "name": name,
            "handler": handler,
            "description": description,
            "schema": schema or {"type": "object", "properties": {}},
            "permission": permission,
            "category": category,
            "examples": examples or [],
        }

        return self.tools[name]

    def get(self, name):

        return self.tools.get(name)

    def exists(self, name):

        return name in self.tools

    def all(self):

        return self.tools

    def by_category(self, category):

        return [
            tool for tool in self.tools.values()
            if tool["category"] == category
        ]

    def schemas(self):
        """OpenAI-style tool definitions for a provider request."""

        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["schema"],
                },
            }
            for tool in self.tools.values()
        ]

    def metadata(self):

        return [
            {
                "name": tool["name"],
                "description": tool["description"],
                "schema": tool["schema"],
                "permission": tool["permission"],
                "category": tool["category"],
                "examples": tool["examples"],
            }
            for tool in self.tools.values()
        ]
