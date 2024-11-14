from prometheus_client import Counter, Histogram, make_asgi_app
import structlog
from functools import wraps
import time
from typing import Callable
from fastapi import FastAPI

# Prometheus metrics
message_counter = Counter('processed_messages_total', 'Number of processed messages', ['service', 'message_type', 'status'])
processing_time = Histogram('message_processing_seconds', 'Time spent processing messages', ['service', 'message_type'])
error_counter = Counter('processing_errors_total', 'Number of processing errors', ['service', 'error_type'])



def setup_monitoring(app: FastAPI, service_name: str):
    # Setup structured logging
    logger = structlog.get_logger(service=service_name)
    
    # Add prometheus metrics endpoint to the FastAPI app
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)
    
    return logger

def monitor_message_processing(service_name: str) -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                message_counter.labels(
                    service=service_name,
                    message_type=args[0].get('message_type', 'unknown'),
                    status='success'
                ).inc()
                return result
            except Exception as e:
                error_counter.labels(
                    service=service_name,
                    error_type=type(e).__name__
                ).inc()
                raise
            finally:
                processing_time.labels(
                    service=service_name,
                    message_type=args[0].get('message_type', 'unknown')
                ).observe(time.time() - start_time)
        return wrapper
    return decorator