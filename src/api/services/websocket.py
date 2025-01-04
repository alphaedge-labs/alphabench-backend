from typing import Dict
from fastapi import WebSocket
import logging

logger = logging.getLogger()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        if user_id in self.active_connections:
            logger.warning(f"User {user_id} is already connected. Overwriting the existing connection.")
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"User {user_id} connected.")

    def disconnect(self, user_id):
        if user_id in self.active_connections:
            self.active_connections.pop(user_id)
            logger.info(f"User {user_id} disconnected.")
        else:
            logger.warning(f"User {user_id} was not connected. Cannot disconnect.")

    async def broadcast(self, user_id: str, message: str):
        # Check if the user is connected
        if user_id not in self.active_connections:
            logger.warning(f"User {user_id} is not connected. Cannot broadcast message.")
            return  # Exit the method if the user is not connected

        connection = self.active_connections[user_id]
        if connection:
            await connection.send_text(message)

manager = ConnectionManager()