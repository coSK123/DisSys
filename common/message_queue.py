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
        self._setup_dlx()
        self._ensure_connection()

    def _setup_dlx(self):
        try:
            self._ensure_connection()
            
            # Delete existing queues first
            for queue_name in self.config.QUEUE_SETTINGS:
                try:
                    self._channel.queue_delete(queue=queue_name)
                except Exception:
                    pass
            
            # Declare the dead letter exchange
            self._channel.exchange_declare(
                exchange=self.config.DLX_EXCHANGE,
                exchange_type='direct',
                durable=True
            )
            
            # Create dead letter queues for each main queue
            for queue_name in self.config.QUEUE_SETTINGS:
                dlq_name = f"{self.config.DLX_QUEUE_PREFIX}{queue_name}"
                self._channel.queue_declare(queue=dlq_name, durable=True)
                self._channel.queue_bind(
                    queue=dlq_name,
                    exchange=self.config.DLX_EXCHANGE,
                    routing_key=queue_name
                )
        except Exception as e:
            self.logger.error("dlx_setup_failed", error=str(e))
            raise

    def _create_connection_params(self):
        return pika.ConnectionParameters(
            host=self.config.RABBITMQ_HOST,
            port=self.config.RABBITMQ_PORT,
            credentials=pika.PlainCredentials(
                self.config.RABBITMQ_USER,
                self.config.RABBITMQ_PASS
            ),
            heartbeat=60,
            blocked_connection_timeout=30,
            connection_attempts=3,
            retry_delay=5
        )

    def _declare_queue(self, queue_name: str, **kwargs):
        """Declare queue with dead letter exchange configuration."""
        default_settings = self.config.QUEUE_SETTINGS.get(queue_name, {'durable': True})
        settings = {**default_settings, **kwargs}
        
        try:
            self._channel.queue_declare(
                queue=queue_name,
                durable=settings['durable'],
                arguments={
                    'x-dead-letter-exchange': self.config.DLX_EXCHANGE,
                    'x-dead-letter-routing-key': queue_name
                }
            )
        except Exception as e:
            self.logger.error("queue_declaration_failed", 
                            queue=queue_name, 
                            error=str(e))
            raise

    def _ensure_connection(self):
        with self._lock:
            try:
                if self._connection is None or self._connection.is_closed:
                    self._connection = pika.BlockingConnection(
                        self._create_connection_params()
                    )
                    self._channel = self._connection.channel()
                    self._channel.basic_qos(prefetch_count=1)
                    
                    # Declare default queues
                    for queue_name in self.config.QUEUE_SETTINGS:
                        self._declare_queue(queue_name)
                    
                    self.logger.info("rabbitmq_connected")
            except Exception as e:
                self.logger.error("connection_failed", error=str(e))
                raise

    def publish(self, queue_name: str, message: Any) -> bool:
        """Publish message with retry logic."""
        self.logger.info("publishing_message", 
                        queue=queue_name, 
                        correlation_id=message.get('correlation_id'))

        for attempt in range(self.config.MAX_RETRIES):
            try:
                self._ensure_connection()
                
                # Prepare message
                if isinstance(message, dict):
                    message_body = json.dumps(message)
                elif hasattr(message, 'to_json'):
                    message_body = json.dumps(message.to_json())
                else:
                    message_body = json.dumps(message)

                self._declare_queue(queue_name)
                
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
                self.logger.error("publish_failed", 
                                attempt=attempt + 1,
                                error=str(e))
                if attempt < self.config.MAX_RETRIES - 1:
                    time.sleep(self.config.RETRY_DELAY)
                    self._ensure_connection()
                else:
                    return False

    def consume(self, queue_name: str, callback: Callable) -> None:
        """Set up consumer with automatic reconnection."""
        def wrapped_callback(ch, method, properties, body):
            try:
                if isinstance(body, bytes):
                    message = json.loads(body.decode('utf-8'))
                else:
                    message = body

                self.logger.info("message_received", 
                               queue=queue_name,
                               correlation_id=message.get('correlation_id'))

                callback(ch, method, properties, message)
                
            except json.JSONDecodeError as e:
                self.logger.error("message_decode_failed", 
                                error=str(e))
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            except Exception as e:
                self.logger.error("message_processing_failed", 
                                error=str(e))
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

        while True:
            try:
                self._ensure_connection()
                self._declare_queue(queue_name)
                self._channel.basic_consume(
                    queue=queue_name,
                    on_message_callback=wrapped_callback,
                    auto_ack=False
                )
                self.logger.info("consumer_started", queue=queue_name)
                self._channel.start_consuming()
                
            except Exception as e:
                self.logger.error("consumer_error", 
                                queue=queue_name,
                                error=str(e))
                time.sleep(self.config.RETRY_DELAY)

    def close(self):
        """Safely close connection."""
        with self._lock:
            try:
                if self._channel and self._channel.is_open:
                    self._channel.close()
                if self._connection and not self._connection.is_closed:
                    self._connection.close()
                    self.logger.info("connection_closed")
            except Exception as e:
                self.logger.error("close_connection_failed", 
                                error=str(e))