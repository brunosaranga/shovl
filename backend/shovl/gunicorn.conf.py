"""
Gunicorn settings for production. Start command:  gunicorn core.wsgi:application
Gunicorn reads this file by itself when started from this folder.
"""
import os

# The host says which port to listen on.
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"

# Threads, not one-request-at-a-time workers: a scan streams for up to 90 seconds and holds
# its thread the whole time. 2 processes x 8 threads = 16 requests at once, scans included.
workers = int(os.getenv("WEB_CONCURRENCY", "2"))
worker_class = "gthread"
threads = int(os.getenv("GUNICORN_THREADS", "8"))

# A process that stops reporting to gunicorn for this long is restarted. With threads this
# is not a limit on one request, but keep it above the 90-second scan budget anyway.
timeout = 120
# On a redeploy or restart, running scans get this long to finish.
graceful_timeout = 100

# Each process is replaced after about this many requests, so slow memory growth never adds up.
max_requests = 1000
max_requests_jitter = 100

# Requests and errors go to the host's log stream.
accesslog = "-"
errorlog = "-"

# Gunicorn's remote-control socket (a file in the home folder) is not used by shovl.
control_socket_disable = True
