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
    专门处理 WebSocket 服务器和客户端通信
    """

    def __init__(self, host: str = "python-middleware-api", port: int = 8765):
        self.host = host
        self.port = port
        self.server = None
        self.callback_registry: Dict[str, Callable] = {}
        self.active_connections: Set[ServerConnection] = set()
        self._running = False

    async def start_server(self):
        """启动 WebSocket 服务器"""
        if self.server:
            logger.warning("WebSocket server is already running")
            return self.server

        try:
            self.server = await serve(
                self._handle_client_connection,
                self.host,
                self.port
            )
            self._running = True
            logger.info(f"WebSocket server started on {self.host}:{self.port}")
            return self.server
        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")
            raise

    async def stop_server(self):
        """停止 WebSocket 服务器"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self._running = False
            logger.info("WebSocket server stopped")

        # 关闭所有活跃连接
        if self.active_connections:
            await asyncio.gather(
                *[conn.close() for conn in self.active_connections],
                return_exceptions=True
            )
            self.active_connections.clear()

    async def _handle_client_connection(self, websocket: ServerConnection, path: str):
        """处理客户端连接"""
        self.active_connections.add(websocket)
        client_addr = websocket.remote_address
        logger.info(f"New WebSocket connection from {client_addr}")

        try:
            async for message in websocket:
                await self._handle_client_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"WebSocket connection closed: {client_addr}")
        except Exception as e:
            logger.error(f"WebSocket error for {client_addr}: {e}")
        finally:
            self.active_connections.discard(websocket)
            if not websocket.closed:
                await websocket.close()

    async def _handle_client_message(self, websocket: ServerConnection, message: str):
        """处理客户端消息"""
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
        """处理用户确认"""
        callback_id = data.get("callback_id")
        if callback_id and callback_id in self.callback_registry:
            callback = self.callback_registry[callback_id]
            confirmation = UserConfirmation(
                proceed=data.get("proceed", False),
                feedback=data.get("feedback")
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
        """处理任务取消"""
        user_id = data.get("user_id")
        task_id = data.get("task_id")

        if user_id and task_id:
            # 这里可以添加取消任务的逻辑
            # 由于需要访问数据库管理器，这个功能可能需要通过回调实现
            logger.info(f"Task cancellation requested: user={user_id}, task={task_id}")
            await self.broadcast_message({
                "type": "task_cancelled",
                "user_id": user_id,
                "task_id": task_id,
                "timestamp": asyncio.get_event_loop().time()
            })
        else:
            logger.warning("Invalid cancellation request: missing user_id or task_id")

    async def _handle_ping(self, websocket: ServerConnection, data: Dict[str, Any]):
        """处理心跳检测"""
        pong_data = {
            "type": "pong",
            "timestamp": asyncio.get_event_loop().time(),
            "original_data": data
        }
        await self._send_to_client(websocket, pong_data)

    async def _handle_subscription(self, websocket: ServerConnection, data: Dict[str, Any]):
        """处理订阅请求"""
        user_id = data.get("user_id")
        if user_id:
            # 可以在这里实现用户特定的订阅逻辑
            logger.info(f"User {user_id} subscribed to updates")
            await self._send_to_client(websocket, {
                "type": "subscription_confirmed",
                "user_id": user_id
            })

    async def _send_error(self, websocket: ServerConnection, error_message: str):
        """发送错误消息给客户端"""
        error_data = {
            "type": "error",
            "message": error_message,
            "timestamp": asyncio.get_event_loop().time()
        }
        await self._send_to_client(websocket, error_data)

    async def _send_to_client(self, websocket: ServerConnection, data: Dict[str, Any]):
        """发送数据给特定客户端"""
        try:
            if not websocket.closed:
                await websocket.send(json.dumps(data))
        except Exception as e:
            logger.error(f"Failed to send message to client: {e}")

    async def notify_user(self, step_result: TaskStepResult, user_id: str, task_id: str, step: int) -> UserConfirmation:
        """通知用户任务步骤结果"""
        callback_id = str(uuid.uuid4())
        confirmation_future = asyncio.Future()

        # 注册回调
        self.callback_registry[callback_id] = lambda confirmation: confirmation_future.set_result(confirmation)

        # 准备通知数据
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
            "timestamp": asyncio.get_event_loop().time()
        }

        try:
            # 广播给所有连接的客户端（可以优化为只发送给特定用户）
            await self.broadcast_message(notification_data)

            # 等待用户确认，设置超时
            try:
                return await asyncio.wait_for(confirmation_future, timeout=300)  # 5分钟超时
            except asyncio.TimeoutError:
                logger.warning(f"User confirmation timeout for callback {callback_id}")
                # 清理回调
                self.callback_registry.pop(callback_id, None)
                return UserConfirmation(proceed=True)  # 默认继续

        except Exception as e:
            logger.error(f"WebSocket notification error: {e}")
            # 清理回调
            self.callback_registry.pop(callback_id, None)
            return UserConfirmation(proceed=True)  # 默认继续

    async def send_heartbeat(self, user_id: str, task_id: str, interval: int = 30):
        """发送心跳消息"""
        heartbeat_data = {
            "type": "heartbeat",
            "status": "heartbeat",
            "message": "任务仍在执行中...",
            "user_id": user_id,
            "task_id": task_id,
            "timestamp": asyncio.get_event_loop().time()
        }

        while self._running:
            try:
                await self.broadcast_message(heartbeat_data)
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"WebSocket heartbeat error: {e}")
                break

    async def broadcast_message(self, message: Dict[str, Any]):
        """广播消息给所有连接的客户端"""
        if not self.active_connections:
            logger.debug("No active WebSocket connections for broadcast")
            return

        # 过滤掉已关闭的连接
        active_connections = [conn for conn in self.active_connections if not conn.closed]
        self.active_connections = set(active_connections)

        if active_connections:
            await asyncio.gather(
                *[self._send_to_client(conn, message) for conn in active_connections],
                return_exceptions=True
            )
            logger.debug(f"Broadcasted message to {len(active_connections)} clients")

    async def send_to_user(self, user_id: str, message: Dict[str, Any]):
        """发送消息给特定用户（需要实现用户连接映射）"""
        # 这里可以实现用户ID到WebSocket连接的映射
        # 目前简化为广播
        message["target_user_id"] = user_id
        await self.broadcast_message(message)

    def get_connection_count(self) -> int:
        """获取活跃连接数"""
        return len([conn for conn in self.active_connections if not conn.closed])

    def get_status(self) -> Dict[str, Any]:
        """获取WebSocket管理器状态"""
        return {
            "running": self._running,
            "host": self.host,
            "port": self.port,
            "active_connections": self.get_connection_count(),
            "pending_callbacks": len(self.callback_registry)
        }
