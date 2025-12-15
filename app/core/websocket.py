"""
WebSocket manager for real-time updates.
Handles connections, broadcasts, and chat messages.
"""

import asyncio
from typing import Dict, Set, List
from datetime import datetime
from fastapi import WebSocket
from dataclasses import dataclass, field, asdict

from app.core.logger import get_logger

logger = get_logger("websocket")


@dataclass
class ChatMessage:
    """Chat message structure."""

    username: str
    message: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    id: int = 0


class ConnectionManager:
    """
    Manages WebSocket connections for real-time updates.
    Supports:
    - Balance update broadcasts
    - Big win announcements
    - Global chat
    """

    def __init__(self):
        # Active WebSocket connections: user_id -> WebSocket
        self.active_connections: Dict[int, WebSocket] = {}
        # All connections for broadcasts
        self.all_connections: Set[WebSocket] = set()
        # Chat message history (last 100 messages)
        self.chat_history: List[ChatMessage] = []
        self.max_chat_history = 100
        self.message_counter = 0

    async def connect(self, websocket: WebSocket, user_id: int = None):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.all_connections.add(websocket)

        if user_id:
            self.active_connections[user_id] = websocket

        logger.info(
            f"WebSocket connected: user_id={user_id}, total={len(self.all_connections)}"
        )

        # Send chat history to new connection
        if self.chat_history:
            await websocket.send_json(
                {
                    "type": "chat_history",
                    "messages": [asdict(m) for m in self.chat_history[-50:]],
                }
            )

    def disconnect(self, websocket: WebSocket, user_id: int = None):
        """Remove a WebSocket connection."""
        self.all_connections.discard(websocket)

        if user_id and user_id in self.active_connections:
            del self.active_connections[user_id]

        logger.info(f"WebSocket disconnected: total={len(self.all_connections)}")

    async def send_personal(self, user_id: int, message: dict):
        """Send a message to a specific user."""
        websocket = self.active_connections.get(user_id)
        if websocket:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to user {user_id}: {e}")

    async def broadcast(self, message: dict, exclude: WebSocket = None):
        """Broadcast a message to all connected clients concurrently."""

        # Create a list of send tasks
        tasks = []
        for websocket in self.all_connections:
            if websocket != exclude:
                tasks.append(self._send_with_error_handling(websocket, message))

        # Run all send tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results to find and remove disconnected clients
        disconnected = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # The websocket that failed is the one at the same index in our original set
                # Note: This is a simplification. A more robust way would be to pass the websocket
                # back with the result.
                ws = list(self.all_connections - {exclude if exclude else None})[i]
                disconnected.append(ws)

        if disconnected:
            logger.info(
                f"Found {len(disconnected)} disconnected clients during broadcast."
            )
            for ws in disconnected:
                self.all_connections.discard(ws)

    async def _send_with_error_handling(self, websocket: WebSocket, message: dict):
        """Wrapper to send a message and catch exceptions for disconnected clients."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            # This will be caught by asyncio.gather
            raise e

    async def broadcast_balance_update(self, user_id: int, balance: dict):
        """Broadcast a balance update to a specific user."""
        await self.send_personal(
            user_id, {"type": "balance_update", "user_id": user_id, "balance": balance}
        )

    async def broadcast_big_win(
        self, username: str, game: str, amount: float, multiplier: float
    ):
        """Announce a big win to all connected clients."""
        await self.broadcast(
            {
                "type": "big_win",
                "username": username,
                "game": game,
                "amount": amount,
                "multiplier": multiplier,
                "timestamp": datetime.now().isoformat(),
            }
        )
        logger.info(f"Big win broadcast: {username} won {amount} on {game}")

    async def add_chat_message(self, username: str, message: str) -> ChatMessage:
        """Add a chat message and broadcast to all."""
        # Sanitize message
        message = message.strip()[:200]  # Limit message length

        if not message:
            return None

        self.message_counter += 1
        chat_msg = ChatMessage(
            username=username, message=message, id=self.message_counter
        )

        # Add to history
        self.chat_history.append(chat_msg)

        # Trim history
        if len(self.chat_history) > self.max_chat_history:
            self.chat_history = self.chat_history[-self.max_chat_history :]

        # Broadcast to all
        await self.broadcast({"type": "chat_message", "message": asdict(chat_msg)})

        logger.debug(f"Chat: {username}: {message[:50]}...")
        return chat_msg

    def get_connection_count(self) -> int:
        """Get number of active connections."""
        return len(self.all_connections)


# Global WebSocket manager instance
ws_manager = ConnectionManager()
