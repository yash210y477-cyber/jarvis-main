class ToolRegistry:

    def __init__(self):

        self.tools = {}

    def register(

        self,

        name,

        handler,

        description="",

        arguments=None,

        permission="user",

        category="general",

        examples=None

    ):

        self.tools[name] = {

            "name": name,

            "handler": handler,

            "description": description,

            "arguments": arguments or [],

            "permission": permission,

            "category": category,

            "examples": examples or []

        }

    def get(self, name):

        return self.tools.get(name)

    def exists(self, name):

        return name in self.tools

    def all(self):

        return self.tools

    def metadata(self):

        metadata = []

        for tool in self.tools.values():

            metadata.append({

                "name": tool["name"],

                "description": tool["description"],

                "arguments": tool["arguments"],

                "permission": tool["permission"],

                "category": tool["category"],

                "examples": tool["examples"]

            })

        return metadata