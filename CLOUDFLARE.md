# Cloudflare & Nginx Deployment Guide

This guide covers deploying RNG-THING behind Cloudflare with optional Nginx reverse proxy.

---

## Option 1: Cloudflare Tunnel (Recommended)

Cloudflare Tunnel (formerly Argo Tunnel) exposes your application without opening firewall ports.

### Setup Steps

1. **Install cloudflared on your server:**
   ```bash
   # Debian/Ubuntu
   curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
   sudo dpkg -i cloudflared.deb
   ```

2. **Authenticate with Cloudflare:**
   ```bash
   cloudflared tunnel login
   ```

3. **Create a tunnel:**
   ```bash
   cloudflared tunnel create rng-thing
   ```

4. **Configure the tunnel** (`~/.cloudflared/config.yml`):
   ```yaml
   tunnel: <YOUR_TUNNEL_ID>
   credentials-file: /home/user/.cloudflared/<TUNNEL_ID>.json
   
   ingress:
     - hostname: yourdomain.com
       service: http://localhost:8000
     - service: http_status:404
   ```

5. **Route DNS:**
   ```bash
   cloudflared tunnel route dns rng-thing yourdomain.com
   ```

6. **Run as service:**
   ```bash
   sudo cloudflared service install
   sudo systemctl start cloudflared
   sudo systemctl enable cloudflared
   ```

### Docker with Cloudflare Tunnel

Add to `docker-compose.yml`:
```yaml
cloudflared:
  image: cloudflare/cloudflared:latest
  container_name: cloudflared
  command: tunnel --no-autoupdate run --token ${CF_TUNNEL_TOKEN}
  environment:
    - CF_TUNNEL_TOKEN=${CF_TUNNEL_TOKEN}
  restart: unless-stopped
  depends_on:
    - web
```

Set `CF_TUNNEL_TOKEN` in your `.env` file.

---

## Option 2: Nginx Reverse Proxy

For direct server deployment with SSL termination.

### Nginx Configuration

Create `/etc/nginx/sites-available/rng-thing`:

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    # SSL Configuration (use Cloudflare Origin CA or Let's Encrypt)
    ssl_certificate /etc/nginx/ssl/origin.pem;
    ssl_certificate_key /etc/nginx/ssl/origin-key.pem;
    
    # SSL Security Settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;
    
    # Proxy to application
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (for future real-time features)
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    # Serve static files directly
    location /static {
        alias /opt/rng-thing/app/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/rng-thing /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## Cloudflare Dashboard Settings

### DNS Settings
- **Type:** A or CNAME
- **Proxy status:** Proxied (orange cloud)

### SSL/TLS Settings
- **Encryption mode:** Full (strict) - if using Origin CA
- **Minimum TLS Version:** 1.2
- **Always Use HTTPS:** On

### Security Settings
- **Security Level:** Medium or High
- **Bot Fight Mode:** On
- **Challenge Passage:** 30 minutes

### Speed Settings
- **Auto Minify:** HTML, CSS, JavaScript
- **Brotli:** On

### Caching
- **Caching Level:** Standard
- **Browser Cache TTL:** 4 hours
- **Always Online:** On

---

## Environment Variables for Production

In your `.env` file:

```env
# Server
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
DEBUG=false

# Security - CHANGE THESE!
SECRET_KEY=your-very-long-random-secret-key-here-min-32-chars

# Database
DB_PATH=/app/data/casino.db

# Logging
LOG_LEVEL=WARNING
LOG_TO_FILE=true

# Rate Limiting
RATE_LIMIT_ENABLED=true

# Cloudflare Tunnel (if using)
# CF_TUNNEL_TOKEN=your-tunnel-token-here
```

---

## Systemd Service (Without Docker)

If running directly on the server:

`/etc/systemd/system/rng-thing.service`:
```ini
[Unit]
Description=RNG-THING Web Application
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/rng-thing
Environment="PATH=/opt/rng-thing/venv/bin"
ExecStart=/opt/rng-thing/venv/bin/gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app --bind 127.0.0.1:8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable rng-thing
sudo systemctl start rng-thing
```

---

## Deployment Checklist

- [ ] Update `SECRET_KEY` in config.json or .env
- [ ] Set `DEBUG=false`
- [ ] Set `admin_password_hash` to a secure password
- [ ] Configure rate limiting appropriately
- [ ] Set up database backups
- [ ] Configure Cloudflare SSL/TLS settings
- [ ] Test all game endpoints
- [ ] Verify admin login works via hidden path
