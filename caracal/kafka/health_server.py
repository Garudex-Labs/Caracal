"""
Health check HTTP server for Kafka consumers.

Provides health check endpoints for Kafka consumer services.

Requirements: Deployment
"""

import asyncio
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from typing import Optional, Any

from caracal.monitoring.health import HealthChecker, HealthStatus
from caracal.logging_config import get_logger

logger = get_logger(__name__)


class ConsumerHealthHandler(BaseHTTPRequestHandler):
    """
    HTTP request handler for consumer health checks.
    
    Serves health status at /health endpoint.
    """
    
    def __init__(self, *args, health_checker: Optional[HealthChecker] = None, **kwargs):
        """
        Initialize health handler.
        
        Args:
            health_checker: HealthChecker instance
        """
        self.health_checker = health_checker
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/health':
            self._serve_health()
        else:
            self.send_error(404, "Not Found")
    
    def _serve_health(self):
        """Serve health check endpoint."""
        try:
            if self.health_checker is None:
                # No health checker - return basic healthy response
                health_data = {
                    "status": "healthy",
                    "service": "caracal-consumer",
                    "message": "Health checker not configured"
                }
                status_code = 200
            else:
                # Perform health check (synchronous wrapper for async)
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    health_result = loop.run_until_complete(self.health_checker.check_health())
                    health_data = health_result.to_dict()
                    
                    # Determine status code
                    if health_result.status == HealthStatus.HEALTHY:
                        status_code = 200
                    else:
                        status_code = 503
                finally:
                    loop.close()
            
            # Send response
            response_body = json.dumps(health_data, indent=2).encode('utf-8')
            
            self.send_response(status_code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(response_body)))
            self.end_headers()
            self.wfile.write(response_body)
            
            logger.debug(f"Served health check: status={status_code}")
        
        except Exception as e:
            logger.error(f"Failed to serve health check: {e}", exc_info=True)
            self.send_error(500, f"Internal Server Error: {e}")
    
    def log_message(self, format, *args):
        """Override to use our logger instead of stderr."""
        logger.debug(f"HTTP {format % args}")


class ConsumerHealthServer:
    """
    HTTP server for consumer health checks.
    
    Runs in a separate thread to avoid blocking the consumer.
    Exposes health status at http://host:port/health.
    
    Requirements: Deployment
    """
    
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8080,
        health_checker: Optional[HealthChecker] = None
    ):
        """
        Initialize consumer health server.
        
        Args:
            host: Host to bind to (default: 0.0.0.0)
            port: Port to bind to (default: 8080)
            health_checker: HealthChecker instance
        """
        self.host = host
        self.port = port
        self.health_checker = health_checker
        
        self._server = None
        self._thread = None
        self._running = False
        
        logger.info(f"ConsumerHealthServer initialized: host={host}, port={port}")
    
    def start(self):
        """
        Start HTTP server in background thread.
        
        The server will listen on the configured host and port and serve
        health status at /health endpoint.
        """
        if self._running:
            logger.warning("Health server already running")
            return
        
        # Create handler factory with health checker
        def handler_factory(*args, **kwargs):
            return ConsumerHealthHandler(
                *args,
                health_checker=self.health_checker,
                **kwargs
            )
        
        # Create HTTP server
        self._server = HTTPServer((self.host, self.port), handler_factory)
        
        # Start server in background thread
        self._thread = Thread(target=self._run_server, daemon=True)
        self._thread.start()
        
        self._running = True
        
        logger.info(
            f"Consumer health server started: "
            f"http://{self.host}:{self.port}/health"
        )
    
    def _run_server(self):
        """Run HTTP server (called in background thread)."""
        try:
            logger.info("Health server thread started")
            self._server.serve_forever()
        except Exception as e:
            logger.error(f"Health server error: {e}", exc_info=True)
        finally:
            logger.info("Health server thread stopped")
    
    def stop(self):
        """Stop HTTP server."""
        if not self._running:
            return
        
        logger.info("Stopping consumer health server")
        
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None
        
        self._running = False
        
        logger.info("Consumer health server stopped")
    
    def is_running(self) -> bool:
        """Check if server is running."""
        return self._running
    
    def get_url(self) -> str:
        """Get health endpoint URL."""
        return f"http://{self.host}:{self.port}/health"
