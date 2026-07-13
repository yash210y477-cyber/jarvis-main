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

        category="general"

    ):

        self.tools[name] = {

            "handler": handler,

            "description": description,

            "arguments": arguments or [],

            "permission": permission,

            "category": category

        }

    def get(self, name):

        return self.tools.get(name)

    def exists(self, name):

        return name in self.tools

    def all(self):

        return self.tools