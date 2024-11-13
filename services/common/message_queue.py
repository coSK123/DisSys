import pika
import json
import logging
from typing import Callable, Any
from contextlib import contextmanager
import time
from threading import Lock

class RabbitMQ:
    def __init__(self, host: str = 'localhost', port: int = 5672, 
                 username: str = 'guest', password: str = 'guest',
                 max_retries: int = 3, retry_delay: int = 5):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._connection = None
        self._channel = None
        self._lock = Lock()
        self._default_queues = {
            'doener_requests': {'durable': True},
            'order_requests': {'durable': True},
            'invoice_requests': {'durable': True},
            'order_supplied': {'durable': True},
            'doener_supplied': {'durable': True},
            'invoice_supplied': {'durable': True}
        }
        self._setup_logging()
        self._ensure_connection()

    def _setup_logging(self):
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def _create_connection_params(self):
        return pika.ConnectionParameters(
            host=self.host,
            port=self.port,
            credentials=pika.PlainCredentials(self.username, self.password),
            heartbeat=60,
            blocked_connection_timeout=30,
            connection_attempts=3,
            retry_delay=5
        )

    def _declare_queue(self, queue_name: str, **kwargs):
        """Declare queue with consistent settings."""
        default_settings = self._default_queues.get(queue_name, {'durable': True})
        settings = {**default_settings, **kwargs}
        
        try:
            self._channel.queue_declare(
                queue=queue_name,
                durable=settings['durable'],
                passive=False  # Don't just check if exists
            )
        except pika.exceptions.ChannelClosedByBroker as e:
            # If queue exists with different settings, log warning and continue
            self.logger.warning(f"Queue {queue_name} already exists with different settings: {e}")
            # Reconnect since channel is closed
            self._ensure_connection()
            
        except Exception as e:
            self.logger.error(f"Failed to declare queue {queue_name}: {str(e)}")

    def _ensure_connection(self):
        with self._lock:
            try:
                if self._connection is None or self._connection.is_closed:
                    self._connection = pika.BlockingConnection(self._create_connection_params())
                    self._channel = self._connection.channel()
                    self._channel.basic_qos(prefetch_count=1)
                    
                    # Declare default queues
                    for queue_name in self._default_queues:
                        self._declare_queue(queue_name)
                    
                    self.logger.info("Successfully connected to RabbitMQ")
            except Exception as e:
                self.logger.error(f"Failed to ensure connection: {str(e)}")
                raise

    @property
    def channel(self):
        self._ensure_connection()
        return self._channel
    
    def setup_consumers(self, queues: list, callback: Callable) -> None:
        """Set up multiple consumers with the same callback."""
        for queue in queues:
            self._declare_queue(queue)
            self._channel.basic_consume(
                queue=queue,
                on_message_callback=callback,
                auto_ack=False
            )
        
        try:
            self._channel.start_consuming()
        except Exception as e:
            self.logger.error(f"Consumer error: {str(e)}")
            self._ensure_connection()

    def publish(self, queue_name: str, message: Any) -> bool:
        """Publish message to queue with retry logic and error handling."""
        for attempt in range(self.max_retries):
            try:
                self._ensure_connection()
                
                # Prepare message
                if isinstance(message, dict):
                    message_body = json.dumps(message)
                elif hasattr(message, 'to_json'):
                    message_body = json.dumps(message.to_json())
                else:
                    message_body = json.dumps(message)

                # Use consistent queue declaration
                self._declare_queue(queue_name)
                
                self._channel.basic_publish(
                    exchange='',
                    routing_key=queue_name,
                    body=message_body,
                    properties=pika.BasicProperties(
                        delivery_mode=2,  # Make message persistent
                        content_type='application/json'
                    )
                )
                return True
                
            except Exception as e:
                self.logger.error(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    self._ensure_connection()
                else:
                    return False

    def consume(self, queue_name: str, callback: Callable) -> None:
        """Set up a consumer with automatic reconnection and error handling."""
        def wrapped_callback(ch, method, properties, body):
            try:
                # Decode message
                if isinstance(body, bytes):
                    message = json.loads(body.decode('utf-8'))
                else:
                    message = body

                # Call the actual callback
                callback(ch, method, properties, message)
                ch.basic_ack(delivery_tag=method.delivery_tag)
                
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to decode message: {str(e)}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            except Exception as e:
                self.logger.error(f"Error processing message: {str(e)}")
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
                self.logger.info(f"Started consuming from {queue_name}")
                self._channel.start_consuming()
                
            except Exception as e:
                self.logger.error(f"Consumer error: {str(e)}")
                time.sleep(self.retry_delay)

    def close(self):
        """Safely close the connection."""
        with self._lock:
            try:
                if self._channel and self._channel.is_open:
                    self._channel.close()
                if self._connection and not self._connection.is_closed:
                    self._connection.close()
                    self.logger.info("RabbitMQ connection closed")
            except Exception as e:
                self.logger.error(f"Error closing connection: {str(e)}")