bind = "0.0.0.0:8000"
workers = 2
worker_class = "sync"
timeout = 600  # 10 minutes for long-running requests
keepalive = 5
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
loglevel = "info"
preload_app = True

