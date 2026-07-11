from prompts.base import BASE_PROMPT
from prompts.assistant import ASSISTANT_PROMPT
from prompts.coding import CODING_PROMPT
from prompts.teacher import TEACHER_PROMPT
from prompts.research import RESEARCH_PROMPT


class PromptManager:

    def __init__(self):

        self.mode = "assistant"

    def set_mode(self, mode: str):

        self.mode = mode.lower()

    def get_prompt(self):

        prompts = {

            "assistant": ASSISTANT_PROMPT,

            "coding": CODING_PROMPT,

            "teacher": TEACHER_PROMPT,

            "research": RESEARCH_PROMPT

        }

        selected = prompts.get(
            self.mode,
            ASSISTANT_PROMPT
        )

        return BASE_PROMPT + "\n\n" + selected