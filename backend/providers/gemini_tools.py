"""Bridge between OpenAI-style tool schemas and Gemini function calling."""

import json

from google.generativeai import protos


TYPE_MAP = {
    "object": protos.Type.OBJECT,
    "string": protos.Type.STRING,
    "integer": protos.Type.INTEGER,
    "number": protos.Type.NUMBER,
    "boolean": protos.Type.BOOLEAN,
    "array": protos.Type.ARRAY,
}


def _schema(spec: dict):

    spec = spec or {}

    kwargs = {}

    schema_type = TYPE_MAP.get((spec.get("type") or "string").lower())

    if schema_type is not None:
        kwargs["type"] = schema_type

    if spec.get("description"):
        kwargs["description"] = spec["description"]

    if spec.get("enum"):
        kwargs["enum"] = [str(item) for item in spec["enum"]]

    properties = spec.get("properties")

    if properties:
        kwargs["properties"] = {
            name: _schema(value) for name, value in properties.items()
        }

    if spec.get("required"):
        kwargs["required"] = list(spec["required"])

    if spec.get("items"):
        kwargs["items"] = _schema(spec["items"])

    return protos.Schema(**kwargs)


def to_tools(schemas):

    declarations = []

    for entry in schemas:

        function = entry.get("function") or {}

        declarations.append(
            protos.FunctionDeclaration(
                name=function.get("name"),
                description=function.get("description") or "",
                parameters=_schema(
                    function.get("parameters") or {"type": "object"}
                ),
            )
        )

    return [protos.Tool(function_declarations=declarations)]


def to_contents(messages):

    """Convert the neutral message list into Gemini Content objects."""

    contents = []

    system_text = []

    names = {}

    for message in messages:

        for call in message.get("tool_calls") or []:

            names[call.get("id")] = (call.get("function") or {}).get("name")

    for message in messages:

        role = message.get("role")

        if role == "system":

            system_text.append(message.get("content") or "")

            continue

        if role == "user":

            text = message.get("content") or ""

            if system_text:

                text = "\n".join(system_text) + "\n\n" + text

                system_text = []

            contents.append(
                protos.Content(role="user", parts=[protos.Part(text=text)])
            )

            continue

        if role == "assistant":

            parts = []

            if message.get("content"):

                parts.append(protos.Part(text=message["content"]))

            for call in message.get("tool_calls") or []:

                function = call.get("function") or {}

                try:
                    arguments = json.loads(function.get("arguments") or "{}")
                except (TypeError, ValueError):
                    arguments = {}

                parts.append(
                    protos.Part(
                        function_call=protos.FunctionCall(
                            name=function.get("name"),
                            args=arguments,
                        )
                    )
                )

            if parts:
                contents.append(protos.Content(role="model", parts=parts))

            continue

        if role == "tool":

            content = message.get("content") or ""

            try:
                payload = json.loads(content)
            except (TypeError, ValueError):
                payload = {"result": content}

            if not isinstance(payload, dict):
                payload = {"result": payload}

            contents.append(
                protos.Content(
                    role="user",
                    parts=[
                        protos.Part(
                            function_response=protos.FunctionResponse(
                                name=(
                                    names.get(message.get("tool_call_id"))
                                    or "tool"
                                ),
                                response=payload,
                            )
                        )
                    ],
                )
            )

    return contents


def parse_response(response):

    """Return (text, tool_calls) from a Gemini response."""

    text_parts = []

    calls = []

    candidates = getattr(response, "candidates", None) or []

    if not candidates:
        return "", calls

    parts = getattr(candidates[0].content, "parts", None) or []

    for index, part in enumerate(parts):

        call = getattr(part, "function_call", None)

        if call and getattr(call, "name", ""):

            arguments = dict(call.args) if call.args else {}

            calls.append({
                "id": f"gemini-{index}",
                "name": call.name,
                "arguments": arguments,
            })

            continue

        if getattr(part, "text", ""):

            text_parts.append(part.text)

    return "\n".join(text_parts).strip(), calls
