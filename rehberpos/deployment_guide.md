# Django Projesini Hostinger VPS'de Yayınlama Rehberi

## 1. Sunucu Hazırlığı

```bash
# Sistem güncellemesi
sudo apt update && sudo apt upgrade -y

# Python ve gerekli paketlerin kurulumu
sudo apt install python3-pip python3-dev libpq-dev postgresql postgresql-contrib nginx curl -y

# Python sanal ortam kurulumu
sudo apt install python3-venv -y
```

## 2. PostgreSQL Veritabanı Kurulumu

```bash
# PostgreSQL kullanıcı ve veritabanı oluşturma
sudo -u postgres psql

# PostgreSQL komutları
CREATE DATABASE rehberpos;
CREATE USER rehberpos_user WITH PASSWORD 'your_secure_password';
ALTER ROLE rehberpos_user SET client_encoding TO 'utf8';
ALTER ROLE rehberpos_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE rehberpos_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE rehberpos TO rehberpos_user;
\q
```

## 3. Proje Dosyalarının Yüklenmesi

```bash
# Proje dizini oluşturma
mkdir /var/www/
cd /var/www/

# Projeyi git ile klonlama veya dosyaları FTP ile yükleme
# Git kullanımı:
git clone your_repository_url rehberpos
cd rehberpos

# Sanal ortam oluşturma ve aktifleştirme
python3 -m venv venv
source venv/bin/activate

# Gerekli paketlerin kurulumu
pip install -r requirements.txt
```

## 4. Django Proje Ayarları

`.env` dosyasını oluşturun ve aşağıdaki ayarları ekleyin:

```env
SECRET_KEY=your_secret_key
DEBUG=False
ALLOWED_HOSTS=your_domain.com,www.your_domain.com

DB_NAME=rehberpos
DB_USER=rehberpos_user
DB_PASSWORD=your_secure_password
DB_HOST=localhost
DB_PORT=5432
```

## 5. Gunicorn Yapılandırması

```bash
# Gunicorn servis dosyası oluşturma
sudo nano /etc/systemd/system/gunicorn.service
```

Aşağıdaki içeriği ekleyin:

```ini
[Unit]
Description=gunicorn daemon
After=network.target

[Service]
User=root
Group=www-data
WorkingDirectory=/var/www/rehberpos
ExecStart=/var/www/rehberpos/venv/bin/gunicorn --workers 3 --bind unix:/var/www/rehberpos/restaurant_management.sock restaurant_management.wsgi:application

[Install]
WantedBy=multi-user.target
```

## 6. Nginx Yapılandırması

```bash
# Nginx site yapılandırması
sudo nano /etc/nginx/sites-available/rehberpos
```

Aşağıdaki içeriği ekleyin:

```nginx
server {
    listen 80;
    server_name your_domain.com www.your_domain.com;

    location = /favicon.ico { access_log off; log_not_found off; }
    
    location /static/ {
        root /var/www/rehberpos;
    }

    location /media/ {
        root /var/www/rehberpos;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/var/www/rehberpos/restaurant_management.sock;
    }
}
```

## 7. Servis Aktivasyonu

```bash
# Statik dosyaları toplama
python manage.py collectstatic

# Veritabanı migrasyonları
python manage.py migrate

# Gunicorn servisini başlatma
sudo systemctl start gunicorn
sudo systemctl enable gunicorn

# Nginx yapılandırmasını aktifleştirme
sudo ln -s /etc/nginx/sites-available/rehberpos /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl restart nginx
```

## 8. SSL Sertifikası (Let's Encrypt)

```bash
# Certbot kurulumu
sudo apt install certbot python3-certbot-nginx -y

# SSL sertifikası alma
sudo certbot --nginx -d your_domain.com -d www.your_domain.com
```

## 9. Güvenlik Önlemleri

1. UFW Firewall yapılandırması:
```bash
sudo ufw allow 'Nginx Full'
sudo ufw allow OpenSSH
sudo ufw enable
```

2. settings.py güvenlik ayarları:
- DEBUG = False
- ALLOWED_HOSTS ayarı
- SECURE_SSL_REDIRECT = True
- SESSION_COOKIE_SECURE = True
- CSRF_COOKIE_SECURE = True

## 10. Bakım ve İzleme

- Log dosyalarını kontrol etme:
```bash
sudo tail -f /var/log/nginx/error.log
sudo journalctl -u gunicorn
```

- Servisleri yeniden başlatma:
```bash
sudo systemctl restart gunicorn
sudo systemctl restart nginx
```