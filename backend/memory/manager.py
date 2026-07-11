import uuid

from datetime import datetime

from memory.models import MemoryItem
from memory.session import SessionMemory


class MemoryManager:

    def __init__(self):

        self.session = SessionMemory()

    def add_user_message(self, message: str):

        memory = MemoryItem(

            id=str(uuid.uuid4()),

            role="user",

            content=message,

            timestamp=datetime.now()

        )

        self.session.add(memory)

    def add_assistant_message(self, message: str):

        memory = MemoryItem(

            id=str(uuid.uuid4()),

            role="assistant",

            content=message,

            timestamp=datetime.now()

        )

        self.session.add(memory)

    def get_messages(self):

        return self.session.all()

    def clear(self):

        self.session.clear()