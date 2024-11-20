
from aio_pika import connect_robust, Message as AioPikaMessage, IncomingMessage, ExchangeType
import json


# RabbitMQ Service
class RabbitMQService:
    def __init__(self, connection_url: str):
        self.connection_url = connection_url
        self.connection = None
        self.channel = None
    
    async def initialize(self):
        self.connection = await connect_robust(self.connection_url)
        self.channel = await self.connection.channel()
        await self.channel.set_qos(prefetch_count=10)

    async def declare_queue_if_not_exists(self, queue_name: str):
        try:
            await self.channel.declare_queue(queue_name, durable=True)
        except Exception as e:
            print(f"Error declaring queue {queue_name}: {e}")
            raise

    async def verify_queues(self, queues: list[str]):
        for queue in queues:
            await self.declare_queue_if_not_exists(queue)
    
    async def publish(self, queue_name: str, message: dict):
        if not self.channel:
            raise RuntimeError("RabbitMQ channel not initialized")
        message_body = json.dumps(message).encode("utf-8")
        await self.channel.default_exchange.publish(
            AioPikaMessage(body=message_body),
            routing_key=queue_name
        )
    
    async def consume(self, queue_name: str, handler):
        try:
            queue = await self.channel.declare_queue(queue_name, passive=True, durable=True)
            await queue.consume(handler)
        except Exception as e:
            print(e)
        
    
    async def close(self):
        if self.connection:
            await self.connection.close()
