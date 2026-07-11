from collections import deque

from memory.models import MemoryItem


class SessionMemory:

    def __init__(self, max_messages: int = 20):

        self.messages = deque(maxlen=max_messages)

    def add(self, item: MemoryItem):

        self.messages.append(item)

    def all(self):

        return list(self.messages)

    def clear(self):

        self.messages.clear()

    def size(self):

        return len(self.messages)