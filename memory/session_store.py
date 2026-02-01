"""Session store protocol/interface."""

from typing import Protocol

from schemas.session import SessionState


class SessionSummary:
    """Brief summary of a session for listing."""

    def __init__(
        self,
        session_id: str,
        message_count: int,
        created_at: str,
        updated_at: str,
    ):
        self.session_id = session_id
        self.message_count = message_count
        self.created_at = created_at
        self.updated_at = updated_at


class SessionStore(Protocol):
    """Protocol defining the session store interface."""

    async def get_session(self, session_id: str) -> SessionState | None:
        """Retrieve a session by ID. Returns None if not found."""
        ...

    async def save_session(self, session: SessionState) -> None:
        """Save or update a session."""
        ...

    async def delete_session(self, session_id: str) -> None:
        """Delete a session by ID."""
        ...

    async def list_sessions(self, limit: int = 100) -> list[SessionSummary]:
        """List recent sessions."""
        ...

    async def health_check(self) -> bool:
        """Check if the store is healthy and connected."""
        ...
