import multiprocessing

# Gunicorn yapılandırması
bind = 'unix:/var/www/rehberpos/restaurant_management.sock'
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'sync'
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 50
worker_connections = 1000

# Loglama ayarları
accesslog = 'logs/gunicorn-access.log'
errorlog = 'logs/gunicorn-error.log'
loglevel = 'info'
access_log_format = '%({x-forwarded-for}i)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# SSL/TLS ayarları (Nginx üzerinden yönetilecek)
ssl_version = 'TLS'
keyfile = None
certfile = None

# Diğer ayarlar
reload = False
spew = False
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None