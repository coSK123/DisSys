import structlog
from aio_pika import connect_robust, Message as AioPikaMessage, IncomingMessage, ExchangeType
import json

logger = structlog.get_logger()


# RabbitMQ Service
class RabbitMQService:
    def __init__(self, service_name: str, connection_url: str):
        self.service_name = service_name
        self.connection_url = connection_url
        self.connection = None
        self.channel = None
        self.direct_exchange = None
        self.fanout_exchange = None

        self.request_queues = [
            "doener_requests",
            "order_requests",
            "invoice_requests"
        ]  # queues that only exist once because only one service consumes and to be able to scale the services

        self.fanout_queues = [
            "order_supplied",
            "doener_supplied",
            "invoice_supplied"
        ]  # queues that exist for each service that consumes them so that ALL consumers get ALL messages

    async def initialize(self):
        self.connection = await connect_robust(self.connection_url)
        self.channel = await self.connection.channel()
        await self.channel.set_qos(prefetch_count=10)

        # Direct exchange for request queues
        self.direct_exchange = await self.channel.declare_exchange(
            "order_requests",
            ExchangeType.DIRECT,
            durable=True
        )

        # Topic exchange for fanout queues
        self.fanout_exchange = await self.channel.declare_exchange(
            "order_events",
            ExchangeType.TOPIC,
            durable=True
        )

        # Set up request queues
        for queue_name in self.request_queues:
            queue = await self.channel.declare_queue(queue_name, durable=True)
            await queue.bind(self.direct_exchange, routing_key=queue_name)

        # Set up fanout queues
        for event_type in self.fanout_queues:
            queue_name = f"{event_type}.{self.service_name}"
            queue = await self.channel.declare_queue(
                queue_name,
                durable=True,
                auto_delete=True
            )
            await queue.bind(self.fanout_exchange, routing_key=event_type)

    async def ensure_connection(self):
        try:
            if not self.connection or self.connection.is_closed:
                await self.initialize()
        except Exception as e:
            logger.error("connection_recovery_failed", error=str(e))
            raise

    async def publish(self, queue_name: str, message: dict):
        await self.ensure_connection()
        message_body = json.dumps(message).encode()
        logger.info("publishing_message", queue=queue_name)
        if queue_name in self.request_queues:
            await self.direct_exchange.publish(
                AioPikaMessage(body=message_body, delivery_mode=2),
                routing_key=queue_name
            )
        else:
            await self.fanout_exchange.publish(
                AioPikaMessage(body=message_body, delivery_mode=2),
                routing_key=queue_name
            )

        logger.info("message_published", queue=queue_name)

    async def consume(self, queue_name: str, handler):
        try:
            await self.ensure_connection()
            if queue_name in self.request_queues:
                queue = await self.channel.declare_queue(queue_name, passive=True)
            else:
                queue = await self.channel.declare_queue(
                    f"{queue_name}.{self.service_name}",
                    passive=True
                )
            await queue.consume(handler)
        except Exception as e:
            logger.error("error consuming queue", queue=queue_name)

    async def close(self):
        if self.connection:
            await self.connection.close()
