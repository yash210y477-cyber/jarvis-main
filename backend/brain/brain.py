import concurrent.futures

from providers.manager import AIManager

from brain.intent import IntentEngine
from brain.router import Router
from brain.summary_manager import SummaryManager
from brain import tasks, vocabulary
from brain import local_clock, memory_intent, smalltalk
from brain import language
from brain.multi import split_commands

from memory.manager import MemoryManager
from memory.context import ContextBuilder

from tools import builtin, local_intents, nlu
from tools.agent import AgentLoop
from tools.approvals import (
    ApprovalStore,
    describe,
    is_approval,
    is_rejection,
)


# A local Ollama model on CPU needs more than the cloud APIs did.
AI_TIMEOUT_SECONDS = 95

# Writing a whole program (a game, a page) in one tool call took ~50s here,
# so a 60s cap turned a working request into the "no provider" fallback.
AGENT_TIMEOUT_SECONDS = 120

AI_POOL = concurrent.futures.ThreadPoolExecutor(max_workers=2)


def file_markers(steps):
    """One `[file]name` line per file the agent wrote, for the chat card."""

    from urllib.parse import quote

    marks = []

    for step in steps or []:

        if step.get("tool") != "write_file" or not step.get("success"):

            continue

        path = str((step.get("arguments") or {}).get("path") or "").strip()

        if path:

            marks.append(f"[file]{quote(path)}")

    return marks


def shutdown_pool():
    """Drop queued AI work so Ctrl+C does not wait on a stuck request."""

    try:

        AI_POOL.shutdown(wait=False, cancel_futures=True)

    except Exception:

        pass


# Said instead of a stack of failed calls. It keeps the old "no ai provider"
# wording, which the semantic memory already knows not to index, and tells the
# user what to do next instead of shouting a status code at them.
FALLBACK_REPLY = (
    "No AI provider is reachable right now. Add or check a key in Settings, "
    "or ask me something local — like \"what time is it\"."
)


class Brain:

    SUMMARY_THRESHOLD = 50

    CONVERSATION_KEEP = 10

    def __init__(self, summary_threshold=None, conversation_keep=None):

        self.ai = AIManager()

        self.intent = IntentEngine()

        self.router = Router()

        self.memory = MemoryManager()

        self.context = ContextBuilder(self.memory)

        self.summary = SummaryManager()

        self.summary_threshold = (
            summary_threshold
            if summary_threshold is not None
            else self.SUMMARY_THRESHOLD
        )

        self.conversation_keep = (
            conversation_keep
            if conversation_keep is not None
            else self.CONVERSATION_KEEP
        )

        self.registry = builtin.REGISTRY

        self.executor = builtin.EXECUTOR

        self.approvals = ApprovalStore()

        self.agent = AgentLoop(
            self.ai,
            self.registry,
            self.executor,
            self.approvals,
        )

    def _maybe_summarize(self):
        """Summarise in the background once the log gets long; never block."""

        try:

            if self.memory.message_count() < self.summary_threshold:

                return

            # Without providers there is nothing to summarise with.
            if self.ai.providers:

                messages = self.memory.get_messages()

                self.summary.generate(messages)

            self.memory.trim_messages(self.conversation_keep)

        except Exception:

            pass

    def _check_summary(self):

        self._maybe_summarize()

    # -----------------------------
    # Local (no AI, no API key)
    # -----------------------------

    def _local_reply(self, message: str):
        """Return (provider, action, text) or None when AI is needed."""

        hinglish = language.reply_language(message) == "hinglish"

        command = self.intent.detect(message)

        # 0. Multi-fact remember: "my name is Yash and my city is Pune"
        if command.get("intent") == "remember" and command.get("entities"):

            result = self.router.route(command)

            if result.get("success"):

                return ("memory", "remember", result.get("message", "Got it."))

        # 0b. Local clock: date, month, year, weekday, time
        clock = local_clock.reply(message)

        if clock:

            return ("local", "time", clock)

        # 1. Memory recall comes first: "what is my city name"
        key = memory_intent.detect_recall(message)

        if key:

            if key == "__all__":

                return (
                    "memory",
                    "recall_all",
                    memory_intent.describe_all(self.memory)
                )

            return (
                "memory",
                "recall",
                memory_intent.describe(self.memory, key)
            )

        # 2. Memory save: "my favourite colour is black"
        remembered = memory_intent.detect_remember(message)

        if remembered:

            if "note" in remembered:

                result = self.memory.add_note(remembered["note"])

                return (
                    "memory",
                    "remember_note",
                    result.get("message", "Got it.")
                )

            result = self.memory.remember(
                remembered["field"],
                remembered["value"]
            )

            return (
                "memory",
                "remember",
                result.get("message", "Got it.")
            )

        # 3. Everyday small talk: "hey", "thanks", "time"
        reply = smalltalk.local_reply(message, self.memory)

        if reply:

            return ("local", "smalltalk", reply)

        # 3b. Direct tool requests (works without any AI provider)
        intent = local_intents.detect(message)

        if intent:

            tool = self.registry.get(intent["tool"])

            if tool and tool["permission"] == "confirm":

                pending = self.approvals.request(
                    intent["tool"],
                    intent["arguments"],
                    reason="This tool runs on your computer.",
                )

                return ("agent", "confirm", describe(pending, message))

            result = self.executor.execute(
                intent["tool"],
                **intent["arguments"],
            )

            return (
                "local",
                intent["tool"],
                local_intents.render(intent["tool"], result, hinglish),
            )

        # 3c. Loose phrasing: words in any order ("search song on spotify")
        loose = nlu.interpret(message)

        if loose:

            tool = self.registry.get(loose["tool"])

            if tool:

                result = self.executor.execute(
                    loose["tool"], **loose["arguments"]
                )

                return (
                    "local",
                    loose["tool"],
                    local_intents.render(loose["tool"], result, hinglish),
                )

        # 4. Desktop intents: open app, system status, search
        if command.get("intent") not in ("chat", "remember", "recall"):

            result = self.router.route(command)

            if result.get("success"):

                text = (
                    result.get("message")
                    or result.get("response")
                    or str(result)
                )

                return ("router", command.get("intent"), text)

        return None

    # -----------------------------
    # Chat entry point
    # -----------------------------

    def chat(self, message: str, model=None):

        message = (message or "").strip()

        # Remember the user's own words so calls can repair misheard ones.
        vocabulary.learn(message)

        # "close terminal and open calculator" runs both, in order.
        parts = split_commands(message)

        if len(parts) > 1:

            results = [self._chat_single(part, model=model) for part in parts]

            lines = [
                f"- {part}: {(result.get('response') or '').strip()}"
                for part, result in zip(parts, results, strict=False)
            ]

            return {
                "success": all(result.get("success") for result in results),
                "provider": "local",
                "action": "multi",
                "commands": parts,
                "results": results,
                "response": "\n".join(lines),
            }

        return self._chat_single(message, model=model)

    def _chat_single(self, message: str, model=None):

        message = (message or "").strip()

        if not message:

            return {
                "success": False,
                "provider": "local",
                "action": "empty",
                "response": "Please type something."
            }

        # A parked confirm-tool waits for yes/no before anything else.
        pending = self.approvals.peek()

        if pending and is_approval(message):

            return self._run_approved(message)

        if pending and is_rejection(message):

            self.approvals.clear()

            text = "Okay, cancelled."

            self.memory.add_user_message(message)
            self.memory.add_assistant_message(text)

            return {
                "success": True,
                "provider": "local",
                "action": "cancelled",
                "response": text,
            }

        self.memory.add_user_message(message)

        local = self._local_reply(message)

        if local:

            provider, action, text = local

            self.memory.add_assistant_message(text)

            self._check_summary()

            return {
                "success": True,
                "provider": provider,
                "action": action,
                "response": text
            }

        # -----------------------------
        # AI fallback
        # -----------------------------

        # No provider at all: answer immediately instead of waiting on dead
        # endpoints. Free-form chat needs a key; local commands are above.
        if not self.ai.providers:

            self.memory.add_assistant_message(FALLBACK_REPLY)

            self._check_summary()

            return {
                "success": True,
                "provider": "local",
                "action": "fallback",
                "response": FALLBACK_REPLY,
            }

        # Tool-calling loop first: the model may need to act, not just talk.
        agent_result = None

        try:

                        # The agent gets the same context a plain reply would, minus the
            # current message (the agent sends that one itself).
            agent_context = self.context.build(message).split(
                "### Current User Message"
            )[0].strip()

            agent_result = AI_POOL.submit(

                self.agent.run,

                message,

                agent_context,

                "",

            ).result(timeout=AGENT_TIMEOUT_SECONDS)

        except Exception:

            agent_result = None

        if agent_result and agent_result.get("success"):

            text = agent_result.get("response") or ""

            marks = file_markers(agent_result.get("steps"))

            if marks:

                text = "\n".join([text, *marks]).strip()

            self.memory.add_assistant_message(text)

            self._check_summary()

            return {
                "success": True,
                "provider": agent_result.get("provider", "ai"),
                "model": agent_result.get("model", ""),
                "action": (
                    "tool" if agent_result.get("steps") else "chat"
                ),
                "response": text,
                "steps": agent_result.get("steps", []),
                "needs_confirmation": agent_result.get(
                    "needs_confirmation", False
                ),
            }

        prompt = self.context.build(message)

        try:

            ai_response = AI_POOL.submit(
                self.ai.chat,
                prompt,
                model,
                tasks.detect(message),
            ).result(timeout=AI_TIMEOUT_SECONDS)

        except concurrent.futures.TimeoutError:

            ai_response = {
                "success": False,
                "provider": "local",
                "message": "AI provider timed out."
            }

        except Exception:

            ai_response = {
                "success": False,
                "provider": "local",
                "message": "AI provider failed."
            }

        if ai_response.get("success"):

            text = (
                ai_response.get("response")
                or ai_response.get("message")
                or ""
            )

            self.memory.add_assistant_message(text)

            self._check_summary()

            return {
                "success": True,
                "provider": ai_response.get("provider", "ai"),
                "model": ai_response.get("model", ""),
                "action": "chat",
                "response": text
            }

        # No provider / no API key: never fail a normal message
        self.memory.add_assistant_message(FALLBACK_REPLY)

        self._check_summary()

        return {
            "success": True,
            "provider": "local",
            "action": "fallback",
            "response": FALLBACK_REPLY
        }

    def _run_approved(self, message: str):
        """Run the parked tool after the user said yes."""

        pending = self.approvals.take()

        if not pending:

            return {
                "success": False,
                "provider": "local",
                "action": "expired",
                "response": "That confirmation expired. Ask me again.",
            }

        result = self.executor.execute(
            pending["tool"],
            **pending["arguments"],
        )

        text = local_intents.render(
            pending["tool"], result, language.reply_language(message) == "hinglish"
        )

        marks = file_markers([{
            "tool": pending["tool"],
            "arguments": pending["arguments"],
            "success": bool(result.get("success")),
        }])

        if marks:

            text = "\n".join([text, *marks]).strip()

        self.memory.add_user_message(message)
        self.memory.add_assistant_message(text)

        return {
            "success": True,
            "provider": "local",
            "action": pending["tool"],
            "response": text,
            "steps": [{
                "tool": pending["tool"],
                "arguments": pending["arguments"],
                "success": bool(result.get("success")),
            }],
        }

    def clear_memory(self):

        self.memory.clear()
