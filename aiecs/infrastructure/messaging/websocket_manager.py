import asyncio
import json
import logging
import uuid
import websockets
from typing import Dict, Any, Set, Optional, Callable
from websockets import serve, ServerConnection
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class UserConfirmation(BaseModel):
    proceed: bool
    feedback: Optional[str] = None


class TaskStepResult(BaseModel):
    step: str
    result: Any = None
    completed: bool = False
    message: str
    status: str
    error_code: Optional[str] = None
    error_message: Optional[str] = None


class WebSocketManager:
    """
    Specialized handler for WebSocket server and client communication
    """

    def __init__(self, host: str = "python-middleware-api", port: int = 8765):
        self.host = host
        self.port = port
        self.server = None
        self.callback_registry: Dict[str, Callable] = {}
        self.active_connections: Set[ServerConnection] = set()
        self._running = False

    async def start_server(self):
        """Start WebSocket server"""
        if self.server:
            logger.warning("WebSocket server is already running")
            return self.server

        try:
            self.server = await serve(self._handle_client_connection, self.host, self.port)
            self._running = True
            logger.info(f"WebSocket server started on {self.host}:{self.port}")
            return self.server
        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")
            raise

    async def stop_server(self):
        """Stop WebSocket server"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self._running = False
            logger.info("WebSocket server stopped")

        # Close all active connections
        if self.active_connections:
            await asyncio.gather(
                *[conn.close() for conn in self.active_connections],
                return_exceptions=True,
            )
            self.active_connections.clear()

    async def _handle_client_connection(self, websocket: ServerConnection, path: str):
        """Handle client connection"""
        self.active_connections.add(websocket)
        client_addr = websocket.remote_address
        logger.info(f"New WebSocket connection from {client_addr}")

        try:
            async for message in websocket:
                # Decode bytes to str if needed
                message_str = message if isinstance(message, str) else message.decode('utf-8')
                await self._handle_client_message(websocket, message_str)
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"WebSocket connection closed: {client_addr}")
        except Exception as e:
            logger.error(f"WebSocket error for {client_addr}: {e}")
        finally:
            self.active_connections.discard(websocket)
            try:
                await websocket.close()
            except Exception:
                pass  # Connection already closed

    async def _handle_client_message(self, websocket: ServerConnection, message: str):
        """Handle client message"""
        try:
            data = json.loads(message)
            action = data.get("action")

            if action == "confirm":
                await self._handle_confirmation(data)
            elif action == "cancel":
                await self._handle_cancellation(data)
            elif action == "ping":
                await self._handle_ping(websocket, data)
            elif action == "subscribe":
                await self._handle_subscription(websocket, data)
            else:
                logger.warning(f"Unknown action received: {action}")
                await self._send_error(websocket, f"Unknown action: {action}")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON received: {e}")
            await self._send_error(websocket, "Invalid JSON format")
        except Exception as e:
            logger.error(f"Error handling client message: {e}")
            await self._send_error(websocket, f"Internal error: {str(e)}")

    async def _handle_confirmation(self, data: Dict[str, Any]):
        """Handle user confirmation"""
        callback_id = data.get("callback_id")
        if callback_id and callback_id in self.callback_registry:
            callback = self.callback_registry[callback_id]
            confirmation = UserConfirmation(
                proceed=data.get("proceed", False),
                feedback=data.get("feedback"),
            )
            try:
                callback(confirmation)
                del self.callback_registry[callback_id]
                logger.debug(f"Processed confirmation for callback {callback_id}")
            except Exception as e:
                logger.error(f"Error processing confirmation callback: {e}")
        else:
            logger.warning(f"No callback found for confirmation ID: {callback_id}")

    async def _handle_cancellation(self, data: Dict[str, Any]):
        """Handle task cancellation"""
        user_id = data.get("user_id")
        task_id = data.get("task_id")

        if user_id and task_id:
            # Task cancellation logic can be added here
            # Since database manager access is needed, this functionality may
            # need to be implemented through callbacks
            logger.info(f"Task cancellation requested: user={user_id}, task={task_id}")
            await self.broadcast_message(
                {
                    "type": "task_cancelled",
                    "user_id": user_id,
                    "task_id": task_id,
                    "timestamp": asyncio.get_event_loop().time(),
                }
            )
        else:
            logger.warning("Invalid cancellation request: missing user_id or task_id")

    async def _handle_ping(self, websocket: ServerConnection, data: Dict[str, Any]):
        """Handle heartbeat detection"""
        pong_data = {
            "type": "pong",
            "timestamp": asyncio.get_event_loop().time(),
            "original_data": data,
        }
        await self._send_to_client(websocket, pong_data)

    async def _handle_subscription(self, websocket: ServerConnection, data: Dict[str, Any]):
        """Handle subscription request"""
        user_id = data.get("user_id")
        if user_id:
            # User-specific subscription logic can be implemented here
            logger.info(f"User {user_id} subscribed to updates")
            await self._send_to_client(
                websocket,
                {"type": "subscription_confirmed", "user_id": user_id},
            )

    async def _send_error(self, websocket: ServerConnection, error_message: str):
        """Send error message to client"""
        error_data = {
            "type": "error",
            "message": error_message,
            "timestamp": asyncio.get_event_loop().time(),
        }
        await self._send_to_client(websocket, error_data)

    async def _send_to_client(self, websocket: ServerConnection, data: Dict[str, Any]):
        """Send data to specific client"""
        try:
            await websocket.send(json.dumps(data))
        except Exception as e:
            logger.error(f"Failed to send message to client: {e}")

    async def notify_user(
        self,
        step_result: TaskStepResult,
        user_id: str,
        task_id: str,
        step: int,
    ) -> UserConfirmation:
        """Notify user of task step result"""
        callback_id = str(uuid.uuid4())
        confirmation_future: asyncio.Future[UserConfirmation] = asyncio.Future()

        # Register callback
        self.callback_registry[callback_id] = lambda confirmation: confirmation_future.set_result(confirmation)

        # Prepare notification data
        notification_data = {
            "type": "task_step_result",
            "callback_id": callback_id,
            "step": step,
            "message": step_result.message,
            "result": step_result.result,
            "status": step_result.status,
            "error_code": step_result.error_code,
            "error_message": step_result.error_message,
            "user_id": user_id,
            "task_id": task_id,
            "timestamp": asyncio.get_event_loop().time(),
        }

        try:
            # Broadcast to all connected clients (can be optimized to send only
            # to specific users)
            await self.broadcast_message(notification_data)

            # Wait for user confirmation with timeout
            try:
                # 5 minute timeout
                return await asyncio.wait_for(confirmation_future, timeout=300)
            except asyncio.TimeoutError:
                logger.warning(f"User confirmation timeout for callback {callback_id}")
                # Clean up callback
                self.callback_registry.pop(callback_id, None)
                return UserConfirmation(proceed=True)  # Default to proceed

        except Exception as e:
            logger.error(f"WebSocket notification error: {e}")
            # Clean up callback
            self.callback_registry.pop(callback_id, None)
            return UserConfirmation(proceed=True)  # Default to proceed

    async def send_heartbeat(self, user_id: str, task_id: str, interval: int = 30):
        """Send heartbeat message"""
        heartbeat_data = {
            "type": "heartbeat",
            "status": "heartbeat",
            "message": "Task is still executing...",
            "user_id": user_id,
            "task_id": task_id,
            "timestamp": asyncio.get_event_loop().time(),
        }

        while self._running:
            try:
                await self.broadcast_message(heartbeat_data)
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"WebSocket heartbeat error: {e}")
                break

    async def broadcast_message(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            logger.debug("No active WebSocket connections for broadcast")
            return

        # Filter out closed connections (use try-except to handle closed connections)
        active_connections = []
        for conn in list(self.active_connections):
            try:
                # Try to check if connection is still valid
                active_connections.append(conn)
            except Exception:
                pass  # Connection is closed, skip it
        self.active_connections = set(active_connections)

        if active_connections:
            await asyncio.gather(
                *[self._send_to_client(conn, message) for conn in active_connections],
                return_exceptions=True,
            )
            logger.debug(f"Broadcasted message to {len(active_connections)} clients")

    async def send_to_user(self, user_id: str, message: Dict[str, Any]):
        """Send message to specific user (requires user connection mapping implementation)"""
        # User ID to WebSocket connection mapping can be implemented here
        # Currently simplified to broadcast
        message["target_user_id"] = user_id
        await self.broadcast_message(message)

    def get_connection_count(self) -> int:
        """Get active connection count"""
        return len(self.active_connections)

    def get_status(self) -> Dict[str, Any]:
        """Get WebSocket manager status"""
        return {
            "running": self._running,
            "host": self.host,
            "port": self.port,
            "active_connections": self.get_connection_count(),
            "pending_callbacks": len(self.callback_registry),
        }
