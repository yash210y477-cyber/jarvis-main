from memory.profile import Profile
from memory.conversation import Conversation


class Memory:

    def __init__(self):

        self.profile = Profile()

        self.conversation = Conversation()

    def remember(self, key: str, value: str):

        profile_fields = {

            "name",

            "email",

            "city",

            "occupation"

        }

        if key in profile_fields:

            return self.profile.update(

                key,

                value

            )

        return self.profile.save_fact(

            key,

            value

        )

    def recall(self, key: str):

        profile_value = self.profile.get(key)

        if profile_value:

            return profile_value

        return self.profile.get_fact(key)

    def remember_conversation(

        self,

        role: str,

        message: str

    ):

        self.conversation.add(

            role,

            message

        )

    def recent_conversation(

        self,

        limit: int = 10

    ):

        return self.conversation.last(

            limit

        )

    def reset(self):

        self.profile.clear()

        self.conversation.clear()

    def stats(self):

        return {

            "profile": self.profile.get_profile(),

            "conversation_count": self.conversation.count()

        }