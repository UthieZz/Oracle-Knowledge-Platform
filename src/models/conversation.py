from typing import Any, Dict, List, Optional


class Conversation:
    """A sequence of messages belonging to a single conversation session.

    Attributes:
        id: Stable conversation identifier.
        title: Human-readable title (often the first user prompt).
        source: Absolute path of the source file this was imported from.
        created: ISO-8601 creation timestamp (or ``None``).
        updated: ISO-8601 last-updated timestamp (or ``None``).
        messages: Ordered list of :class:`~src.models.message.Message` objects.
        provenance: Import-level metadata dict (source platform, schema version,
            imported_at, etc.).  Kept at the conversation level to avoid
            bloating individual message objects.
    """

    def __init__(
        self,
        id: str,
        title: str,
        source: str,
        created: Optional[str],
        updated: Optional[str],
        messages: Optional[List[Any]] = None,
        provenance: Optional[Dict[str, Any]] = None,
    ):
        self.id = id
        self.title = title
        self.source = source
        self.created = created
        self.updated = updated
        self.messages: List[Any] = messages if messages is not None else []
        self.provenance: Dict[str, Any] = provenance if provenance is not None else {}

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<Conversation id={self.id!r} title={self.title[:40]!r} "
            f"messages={len(self.messages)}>"
        )
