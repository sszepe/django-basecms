# gunicorn.conf.py — loaded automatically by gunicorn when present in the cwd
bind = "0.0.0.0:8000"
workers = 3
worker_class = "sync"
timeout = 120
keepalive = 5
accesslog = "-"
errorlog = "-"
loglevel = "info"
