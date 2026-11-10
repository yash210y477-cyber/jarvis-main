import concurrent.futures

from providers.manager import AIManager

from brain.intent import IntentEngine
from brain.router import Router
from brain.summary_manager import SummaryManager
from brain import memory_intent, smalltalk

from memory.manager import MemoryManager
from memory.context import ContextBuilder


AI_TIMEOUT_SECONDS = 15

AI_POOL = concurrent.futures.ThreadPoolExecutor(max_workers=2)


FALLBACK_REPLY = (
    "I can't reach an AI provider right now (no API key configured), but I'm "
    "still here for the local stuff: I remember things you tell me, recall "
    "them, open apps and report system stats.\n"
    "Try: \"my favourite colour is black\" then \"what is my favourite colour?\""
)


class Brain:

    SUMMARY_THRESHOLD = 50

    def __init__(self):

        self.ai = AIManager()

        self.intent = IntentEngine()

        self.router = Router()

        self.memory = MemoryManager()

        self.context = ContextBuilder(self.memory)

        self.summary = SummaryManager()

    def _check_summary(self):

        try:

            conversation = self.memory.get_messages()

            if len(conversation) >= self.SUMMARY_THRESHOLD:

                self.summary.generate(conversation)

                self.memory.clear_messages()

        except Exception:

            pass

    # -----------------------------
    # Local (no AI, no API key)
    # -----------------------------

    def _local_reply(self, message: str):
        """Return (provider, action, text) or None when AI is needed."""

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

        # 4. Desktop intents: open app, system status, search
        command = self.intent.detect(message)

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

    def chat(self, message: str):

        message = (message or "").strip()

        if not message:

            return {
                "success": False,
                "provider": "local",
                "action": "empty",
                "response": "Please type something."
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

        prompt = self.context.build(message)

        try:

            ai_response = AI_POOL.submit(
                self.ai.chat,
                prompt
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

    def clear_memory(self):

        self.memory.clear()
