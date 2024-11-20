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
    QUEUES = [
        'doener_requests',
        'order_requests',
        'invoice_requests',
        'order_supplied',
        'doener_supplied',
        'invoice_supplied',
    ]
    
    # Dead Letter Exchange Configuration
    DLX_EXCHANGE = 'dlx'
    DLX_QUEUE_PREFIX = 'dlq.'
    
    # Retry Configuration
    MAX_RETRIES = 3
    RETRY_DELAY = 5  # seconds
    
    # Monitoring Configuration
    PROMETHEUS_PORT = int(os.getenv('PROMETHEUS_PORT', 8000))

    @staticmethod
    def get_rabbitmq_url():
        return f'amqp://{Config.RABBITMQ_USER}:{Config.RABBITMQ_PASS}@{Config.RABBITMQ_HOST}:{Config.RABBITMQ_PORT}'