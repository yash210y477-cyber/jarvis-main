"""Which kind of work a message asks for, so the best provider answers it."""

import re

CODE_WORDS = {
    "code", "coding", "python", "py", "javascript", "typescript", "java", "c++",
    "node", "react", "html", "css", "sql", "query", "api", "endpoint", "server",
    "backend", "frontend", "function", "class", "method", "variable", "bug",
    "debug", "error", "exception", "traceback", "stacktrace", "refactor",
    "compile", "compiler", "algorithm", "regex", "script", "bash", "shell",
    "git", "commit", "merge", "docker", "kubernetes", "database", "json", "xml",
    "framework", "library", "import", "syntax", "loop", "array", "object",
    "leetcode", "test", "unit", "deploy", "package", "dependency",
}

CODE_PHRASES = (
    "write code", "fix the bug", "fix this error", "explain this code",
    "code likho", "code likh", "program banao", "error aa raha", "bug hai",
)

RESEARCH_WORDS = {
    "research", "report", "sources", "source", "study", "paper", "papers",
    "latest", "news", "trend", "trends", "compare", "comparison", "versus",
    "vs", "statistics", "data", "review", "survey", "analysis", "analyze",
    "analyse", "documentation", "overview", "history", "khoj", "jaankari",
    "jankari", "detail", "details",
}

RESEARCH_PHRASES = (
    "latest news", "what is happening", "compare ", "difference between",
    "explain in detail", "research on", "tell me about", "ke baare me batao",
    "ke bare me batao", "current status", "price of", "deep dive",
    "find out", "batao detail", "detail me batao", "details batao",
)


def detect(message: str) -> str:
    """Return "coding", "research" or "general" for one user message."""

    text = (message or "").lower().strip()

    if not text:

        return "general"

    if any(phrase in text for phrase in CODE_PHRASES):

        return "coding"

    words = set(re.findall(r"[a-zA-Z+#]+", text))

    if words & CODE_WORDS:

        return "coding"

    if any(phrase in text for phrase in RESEARCH_PHRASES):

        return "research"

    if words & RESEARCH_WORDS:

        return "research"

    return "general"
