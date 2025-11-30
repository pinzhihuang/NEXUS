import os

# Use Railway's PORT environment variable or default to 8080
port = int(os.environ.get('PORT', 8080))

bind = f"0.0.0.0:{port}"
workers = 2
worker_class = "sync"
timeout = 600  # 10 minutes for long-running requests
keepalive = 5
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
loglevel = "info"
# preload_app = False - DISABLED for fast startup and health check response
# Railway needs quick binding to port for health checks to pass

