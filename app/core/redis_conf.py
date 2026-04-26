import json
import asyncio
from typing import Dict, List
from fastapi import WebSocket
import redis.asyncio as redis
from app.core.config import settings
from app.core.logger import logger

class ConnectionManager:
    def __init__(self):
        # mapping từ user_id -> List[WebSocket]
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.redis_client = None
        self.pubsub = None
        self.listen_task = None

    async def connect_redis(self):
        if not settings.REDIS_URL:
            logger.warning("[Redis] REDIS_URL chưa được cấu hình!")
            return
        try:
            # Kết nối tới Upstash bằng redis.asyncio
            # Với rediss:// (TLS), ssl_cert_reqs="none" giúp tránh lỗi SSL trên local
            self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True, ssl_cert_reqs="none")
            self.pubsub = self.redis_client.pubsub()
            await self.pubsub.subscribe("user_notifications")
            logger.info("📡 [Redis] Đã kết nối Pub/Sub thành công!")
            # Chạy task lắng nghe ngầm
            self.listen_task = asyncio.create_task(self._listen_redis())
        except Exception as e:
            logger.error(f"[Redis] Lỗi kết nối: {e}")

    async def _listen_redis(self):
        try:
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        user_id = data.get("user_id")
                        payload = data.get("payload")
                        
                        if user_id and payload:
                            # Đẩy tin nhắn trực tiếp qua WebSocket tới user_id tương ứng
                            await self.send_personal_message(payload, user_id)
                    except json.JSONDecodeError:
                        logger.error("[Redis] Lỗi parse JSON từ Pub/Sub")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"[Redis] Lỗi vòng lặp Pub/Sub: {e}")

    async def close_redis(self):
        if self.listen_task:
            self.listen_task.cancel()
        if self.pubsub:
            await self.pubsub.close()
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Đã đóng kết nối Redis.")

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info(f"[WebSocket] User {user_id} đã kết nối. Tổng: {len(self.active_connections[user_id])} thiết bị.")

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"[WebSocket] User {user_id} đã ngắt kết nối.")

    async def send_personal_message(self, message: str, user_id: str):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    logger.error(f"[WebSocket] Lỗi gửi tin cho {user_id}: {e}")

    async def publish_user_notification(self, user_id: str, message: str):
        """Gửi thông báo vào kênh Pub/Sub, dùng khi Worker làm xong việc muốn báo về UI"""
        if self.redis_client:
            payload = json.dumps({"user_id": user_id, "payload": message})
            await self.redis_client.publish("user_notifications", payload)

ws_manager = ConnectionManager()
