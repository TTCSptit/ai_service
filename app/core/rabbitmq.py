import os
import json
import logging
import aio_pika
from dotenv import load_dotenv

load_dotenv()

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "")
QUEUE_NAME = "background_tasks_queue"

logger = logging.getLogger(__name__)

class RabbitMQConnection:
    def __init__(self):
        self.connection = None
        self.channel = None

    async def connect(self):
        if not RABBITMQ_URL:
            logger.warning("RABBITMQ_URL is not set. RabbitMQ connection will be skipped.")
            return

        try:
            self.connection = await aio_pika.connect_robust(RABBITMQ_URL)
            self.channel = await self.connection.channel()
            await self.channel.declare_queue(QUEUE_NAME, durable=True)
            logger.info("KẾT NỐI RABBITMQ CLOUDAMQP THÀNH CÔNG!")
        except Exception as e:
            logger.error(f"Lỗi kết nối RabbitMQ: {e}")

    async def close(self):
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            logger.info("Đã đóng kết nối RabbitMQ.")

    async def publish_message(self, task_type: str, payload: dict):
        if not self.channel:
            logger.warning("Không có kết nối RabbitMQ. Bỏ qua publish.")
            return

        message_body = json.dumps({
            "task_type": task_type,
            "payload": payload
        }).encode("utf-8")

        try:
            await self.channel.default_exchange.publish(
                aio_pika.Message(
                    body=message_body,
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key=QUEUE_NAME
            )
            logger.info(f"[RabbitMQ] Đã xuất bản tin nhắn loại '{task_type}' vào Message Broker.")
        except Exception as e:
            logger.error(f"Lỗi khi publish message {task_type}: {e}")

rabbitmq = RabbitMQConnection()
