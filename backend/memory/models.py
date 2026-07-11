from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class MemoryItem:

    id: str

    role: str

    content: str

    timestamp: datetime

    importance: int = 1

    category: str = "conversation"

    user_id: Optional[str] = None


@dataclass
class UserPreference:

    key: str

    value: str

    updated_at: datetime


@dataclass
class ConversationSummary:

    summary: str

    created_at: datetime

    message_count: int