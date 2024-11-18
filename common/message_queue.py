import pika
import json
import logging
from typing import Callable, Any
from contextlib import contextmanager
import time
from threading import Lock
from .config import Config
import structlog

class RabbitMQ:
    def __init__(self):
        self.config = Config()
        self._connection = None
        self._channel = None
        self._lock = Lock()
        self.logger = structlog.get_logger()
        
        # Initialize connection with retries
        retry_count = 0
        last_error = None
        while retry_count < 5:
            try:
                self._ensure_connection()
                self._setup_dlx()
                return
            except Exception as e:
                retry_count += 1
                last_error = e
                self.logger.warning(f"Connection attempt {retry_count} failed", error=str(e))
                if retry_count < 5:
                    time.sleep(5)  # Wait before retrying
        
        self.logger.error("Failed to initialize RabbitMQ after 5 attempts")
        raise last_error

    def _setup_dlx(self):
        """Set up Dead Letter Exchange with proper queue cleanup"""
        try:
            self._ensure_connection()
            
            # First declare the exchange (not passive)
            self._channel.exchange_declare(
                exchange=self.config.DLX_EXCHANGE,
                exchange_type='direct',
                durable=True,
                passive=False  # Create if doesn't exist
            )
            self.logger.info(f"Exchange '{self.config.DLX_EXCHANGE}' setup successful")

            # Set up queues
            for queue_name in self.config.QUEUE_SETTINGS:
                # Create DLQ
                dlq_name = f"dlq.{queue_name}"
                self._channel.queue_declare(
                    queue=dlq_name,
                    durable=True,
                    passive=False  # Create if doesn't exist
                )
                
                # Bind DLQ to exchange
                self._channel.queue_bind(
                    queue=dlq_name,
                    exchange=self.config.DLX_EXCHANGE,
                    routing_key=queue_name
                )
                self.logger.info(f"Dead letter queue '{dlq_name}' setup successful")

                # Create main queue
                self._declare_queue(queue_name)
                self.logger.info(f"Main queue '{queue_name}' setup successful")

        except pika.exceptions.ChannelClosedByBroker as e:
            self.logger.error("Channel closed by broker during DLX setup", error=str(e))
            raise
        except Exception as e:
            self.logger.error("Failed to set up DLX", error=str(e))
            raise

    def _declare_queue(self, queue_name: str):
        """Declare a queue with dead letter exchange configuration"""
        try:
            result = self._channel.queue_declare(
                queue=queue_name,
                durable=True,
                arguments={
                    'x-dead-letter-exchange': self.config.DLX_EXCHANGE,
                    'x-dead-letter-routing-key': queue_name
                }
            )
            return result
        except Exception as e:
            self.logger.error(f"Failed to declare queue {queue_name}", error=str(e))
            raise

    def _create_connection_params(self):
        """Create connection parameters with retry settings"""
        return pika.ConnectionParameters(
            host=self.config.RABBITMQ_HOST,
            port=self.config.RABBITMQ_PORT,
            virtual_host='/',
            credentials=pika.PlainCredentials(
                self.config.RABBITMQ_USER,
                self.config.RABBITMQ_PASS
            ),
            heartbeat=60,
            blocked_connection_timeout=30,
            connection_attempts=3,
            retry_delay=5
        )

    def _ensure_connection(self):
        """Ensure connection and channel are available"""
        with self._lock:
            try:
                if self._connection is None or self._connection.is_closed:
                    self._connection = pika.BlockingConnection(
                        self._create_connection_params()
                    )
                    self._channel = self._connection.channel()
                    self._channel.basic_qos(prefetch_count=1)
                    self.logger.info("RabbitMQ connection established")
            except Exception as e:
                self.logger.error("Connection failed", error=str(e))
                raise

    def publish(self, queue_name: str, message: Any) -> bool:
        """Publish message to queue with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self._ensure_connection()
                
                if isinstance(message, dict):
                    message_body = json.dumps(message)
                elif hasattr(message, 'to_json'):
                    message_body = json.dumps(message.to_json())
                else:
                    message_body = json.dumps(message)

                self._channel.basic_publish(
                    exchange='',
                    routing_key=queue_name,
                    body=message_body,
                    properties=pika.BasicProperties(
                        delivery_mode=2,
                        content_type='application/json'
                    )
                )
                return True
            except Exception as e:
                last_error = e
                if attempt == max_retries - 1:
                    self.logger.error(f"Failed to publish to {queue_name} after {max_retries} attempts", error=str(e))
                    return False
                time.sleep(1)
                continue

    def consume(self, queue_name: str, callback: Callable):
        """Set up consumer with automatic reconnection"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self._ensure_connection()
                self._channel.basic_consume(
                    queue=queue_name,
                    on_message_callback=callback,
                    auto_ack=False
                )
                self.logger.info(f"Consumer set up for {queue_name}")
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    self.logger.error(f"Failed to set up consumer for {queue_name} after {max_retries} attempts", error=str(e))
                    raise
                time.sleep(1)
                continue

    def start_consuming(self):
        """Start consuming messages"""
        try:
            self.logger.info("Starting to consume messages")
            self._channel.start_consuming()
        except Exception as e:
            self.logger.error("Error while consuming messages", error=str(e))
            raise

    def close(self):
        """Safely close connection"""
        with self._lock:
            try:
                if self._channel and self._channel.is_open:
                    self._channel.close()
                if self._connection and not self._connection.is_closed:
                    self._connection.close()
                self.logger.info("RabbitMQ connection closed")
            except Exception as e:
                self.logger.error("Failed to close connection", error=str(e))