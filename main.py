import uvicorn
from multiprocessing import Process
from VT.services.frontend_service import app as frontend_app
from VT.services.order_service import app as order_app
from VT.services.invoice_service import app as invoice_app
from VT.services.doener_service import app as doener_app

import uvicorn
import subprocess
import sys

def start_service(service_name, port):
    subprocess.Popen([
        sys.executable,
        "-m", "uvicorn",
        f"services.{service_name}:app",
        "--host", "0.0.0.0",
        "--port", str(port),
        "--reload"
    ])

if __name__ == "__main__":
    # Start all services
    services = {
        "frontend_service": 8000,
        "order_service": 8001,
        "doener_service": 8002,
        "invoice_service": 8003
    }
    
    for service, port in services.items():
        start_service(service, port)