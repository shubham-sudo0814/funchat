# Funchat Production Deployment Guide 🚀

This document details deploying Funchat on a Linux production server (Ubuntu 22.04 / 24.04 LTS) using **PostgreSQL**, **Gunicorn**, and **Nginx**.

---

## 1. System Requirements

* Ubuntu 22.04 LTS or 24.04 LTS
* Python 3.11+
* PostgreSQL 16+ or 17
* Nginx
* Git

---

## 2. PostgreSQL Setup

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib libpq-dev

# Switch to postgres user and create database & user
sudo -u postgres psql

CREATE DATABASE funchat_db;
CREATE USER funchat_user WITH ENCRYPTED PASSWORD 'YOUR_STRONG_DB_PASSWORD';
ALTER ROLE funchat_user SET client_encoding TO 'utf8';
ALTER ROLE funchat_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE funchat_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE funchat_db TO funchat_user;
\q
```

---

## 3. Clone Repository & Setup Virtual Environment

```bash
cd /var/www
sudo git clone <your-repo-url> funchat
cd /var/www/funchat

sudo chown -R www-data:www-data /var/www/funchat
sudo chmod -R 775 /var/www/funchat/media

# Create virtualenv
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn
```

---

## 4. Production Environment (`.env`)

Create `/var/www/funchat/.env`:
```env
DJANGO_SECRET_KEY=GENERATE_SECURE_RANDOM_KEY_AT_LEAST_50_CHARS
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

DB_ENGINE=django.db.backends.postgresql
DB_NAME=funchat_db
DB_USER=funchat_user
DB_PASSWORD=YOUR_STRONG_DB_PASSWORD
DB_HOST=127.0.0.1
DB_PORT=5432
```

Collect static files and run database migrations:
```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

---

## 5. Systemd Service for Gunicorn

Create `/etc/systemd/system/funchat.service`:
```ini
[Unit]
Description=Funchat Gunicorn Daemon
After=network.target postgresql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/funchat
ExecStart=/var/www/funchat/venv/bin/gunicorn --config /var/www/funchat/gunicorn.conf.py config.wsgi:application
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable funchat
sudo systemctl start funchat
sudo systemctl status funchat
```

---

## 6. Nginx Reverse Proxy Configuration

Create `/etc/nginx/sites-available/funchat`:
```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    client_max_body_size 10M;

    location = /favicon.ico { access_log off; log_not_found off; }

    location /static/ {
        alias /var/www/funchat/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    location /media/ {
        alias /var/www/funchat/media/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    location / {
        include proxy_params;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable the site and test configuration:
```bash
sudo ln -s /etc/nginx/sites-available/funchat /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 7. SSL with Let's Encrypt (Certbot)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

---

## 8. Security Checklist

1. `DJANGO_DEBUG=False` in production `.env`.
2. Secure unique random secret key.
3. Bot API keys are hashed with SHA-256 and never logged.
4. HTTPS enforced across all bot API endpoints and webhooks.
5. Daily PostgreSQL backups configured with `pg_dump` cron jobs.
