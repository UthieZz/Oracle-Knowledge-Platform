from typing import Any, Dict, Optional


class Message:
    """A single turn in a conversation.

    Attributes:
        id: Optional stable identifier for the message (e.g. a SHA-256 hex digest).
        role: Speaker role – typically ``"user"``, ``"assistant"``, or ``"system"``.
        content: Plain-text or Markdown body of the message.
        timestamp: ISO-8601 string or Unix epoch float, or ``None``.
        metadata: Arbitrary key-value provenance/extension data.  Callers
            should treat this as a shallow dict; nested dicts are allowed but
            not required.
    """

    def __init__(
        self,
        role: str,
        content: str,
        timestamp: Optional[Any] = None,
        id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.id = id
        self.role = role
        self.content = content
        self.timestamp = timestamp
        self.metadata: Dict[str, Any] = metadata if metadata is not None else {}

    def __repr__(self) -> str:  # pragma: no cover
        preview = self.content[:60].replace("\n", " ")
        return f"<Message role={self.role!r} ts={self.timestamp!r} content={preview!r}>"
