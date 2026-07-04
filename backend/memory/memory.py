from memory.profile import Profile
from memory.conversation import Conversation


class Memory:
    """
    Central Memory Manager

    Provides access to:

    - Profile Memory
    - Conversation Memory
    """

    def __init__(self):

        self.profile = Profile()

        self.conversation = Conversation()

    def reset(self):

        self.profile.clear()

        self.conversation.clear()

        return {
            "success": True,
            "message": "Memory reset successfully."
        }

    def stats(self):

        return {

            "profile": self.profile.get_profile(),

            "conversation_count":
                self.conversation.count()

        }