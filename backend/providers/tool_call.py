"""Native function calling for the OpenAI-compatible providers.

OpenAI, Groq, z.ai and OpenRouter all expose the same
`client.chat.completions.create` shape, so one mixin covers them.
"""

import json


MAX_TOOL_RESULT_CHARS = 4000


def assistant_message(message) -> dict:
    """Convert an SDK message object into a plain dict for the next request."""

    payload = {
        "role": "assistant",
        "content": message.content or "",
    }

    calls = getattr(message, "tool_calls", None)

    if calls:

        payload["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {
                    "name": call.function.name,
                    "arguments": call.function.arguments or "{}",
                },
            }
            for call in calls
        ]

    return payload


def parsed_calls(message) -> list:

    calls = []

    for call in getattr(message, "tool_calls", None) or []:

        try:

            arguments = json.loads(call.function.arguments or "{}")

        except (TypeError, ValueError):

            arguments = {}

        if not isinstance(arguments, dict):

            arguments = {}

        calls.append({
            "id": call.id,
            "name": call.function.name,
            "arguments": arguments,
        })

    return calls


class OpenAIToolMixin:

    supports_tools = True

    def chat_with_tools(self, messages, tools):

        if not self.health():

            return {
                "success": False,
                "provider": self.name(),
                "error": f"{self.name()} is not configured.",
            }

        try:

            response = self.client.chat.completions.create(
                # Providers that know their reachable models can answer here.
                model=(
                    self.resolve_model()
                    if hasattr(self, "resolve_model")
                    else self.model
                ),
                messages=messages,
                tools=tools,
                tool_choice="auto",
            )

        except Exception as error:

            return {
                "success": False,
                "provider": self.name(),
                "error": str(error),
            }

        message = response.choices[0].message

        return {
            "success": True,
            "provider": self.name(),
            "model": getattr(response, "model", "") or "",
            "message": assistant_message(message),
            "tool_calls": parsed_calls(message),
            "content": message.content or "",
        }


def tool_result_message(call_id, result) -> dict:

    return {
        "role": "tool",
        "tool_call_id": call_id,
        "content": json.dumps(result, default=str)[:MAX_TOOL_RESULT_CHARS],
    }
