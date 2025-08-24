import eventlet
# Patch everything except thread-related modules to avoid WebSocket issues
eventlet.monkey_patch(socket=True, select=True, thread=False)

# Worker configuration
bind = "0.0.0.0:3000"
workers = 1
worker_class = "eventlet"
worker_connections = 1000
keepalive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

def when_ready(server):
    server.log.info("Server is ready. Spawning workers")

def worker_int(worker):
    worker.log.info("Worker received INT or QUIT signal")

def pre_fork(server, worker):
    server.log.info(f"Worker spawned (pid: {worker.pid})")
