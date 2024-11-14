import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # RabbitMQ Configuration
    RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
    RABBITMQ_PORT = int(os.getenv('RABBITMQ_PORT', 5672))
    RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'guest')
    RABBITMQ_PASS = os.getenv('RABBITMQ_PASS', 'guest')
    
    # Service Configuration
    SERVICE_NAME = os.getenv('SERVICE_NAME', 'unknown')
    
    # Queue Configuration
    QUEUE_SETTINGS = {
        'doener_requests': {'durable': True},
        'order_requests': {'durable': True},
        'invoice_requests': {'durable': True},
        'order_supplied': {'durable': True},
        'doener_supplied': {'durable': True},
        'invoice_supplied': {'durable': True}
    }
    
    # Dead Letter Exchange Configuration
    DLX_EXCHANGE = 'dlx'
    DLX_QUEUE_PREFIX = 'dlq.'
    
    # Retry Configuration
    MAX_RETRIES = 3
    RETRY_DELAY = 5  # seconds
    
    # Monitoring Configuration
    PROMETHEUS_PORT = int(os.getenv('PROMETHEUS_PORT', 8000))