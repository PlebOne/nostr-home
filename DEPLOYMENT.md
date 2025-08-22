# Nostr Home VPS Deployment Guide

## Overview
This guide provides comprehensive instructions for deploying Nostr Home on a VPS with HTTPS/WSS support, including both traditional and Docker deployment options.

## Minimum VPS Specifications

### Basic Requirements (Single User)
- **CPU**: 1 vCPU (2.4+ GHz)
- **RAM**: 1 GB RAM minimum, 2 GB recommended
- **Storage**: 10 GB SSD minimum, 20 GB recommended
- **Bandwidth**: 1 TB/month (typical usage)
- **OS**: Ubuntu 22.04 LTS or newer

### Recommended Specifications (Multiple Users/High Traffic)
- **CPU**: 2 vCPU (2.4+ GHz)
- **RAM**: 4 GB RAM
- **Storage**: 40 GB SSD
- **Bandwidth**: 2+ TB/month
- **OS**: Ubuntu 22.04 LTS or newer

### VPS Provider Recommendations
- **DigitalOcean**: Basic Droplet ($6/month) or Standard ($12/month)
- **Linode**: Nanode 1GB ($5/month) or Shared 2GB ($12/month)
- **Vultr**: Regular Performance ($6/month) or High Performance ($12/month)
- **AWS**: t3.micro ($8.5/month) or t3.small ($16.8/month)
- **Hetzner**: CX11 (€4.15/month) or CX21 (€5.83/month)

## Domain and SSL Requirements

### Domain Setup
1. Purchase a domain from any registrar (Namecheap, Cloudflare, etc.)
2. Point your domain to your VPS IP address:
   ```
   A Record: @ -> YOUR_VPS_IP
   A Record: www -> YOUR_VPS_IP
   ```

### SSL Certificate (Required for HTTPS/WSS)
- We'll use Let's Encrypt (free) with Certbot
- Automatically handles renewals
- Supports wildcard certificates

## Deployment Options

# Option 1: Docker Deployment (Recommended)

Docker provides easier deployment, better security, and simpler updates.

## Prerequisites
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose -y

# Logout and login to apply docker group
exit
```

## Docker Setup Files

Create these files in your project directory:

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p /app/data

# Expose port
EXPOSE 3000

# Run the application
CMD ["python", "app.py"]
```

### docker-compose.yml
```yaml
version: '3.8'

services:
  nostr-home:
    build: .
    ports:
      - "3000:3000"
    volumes:
      - ./data:/app/data
      - ./config:/app/config
    environment:
      - PORT=3000
      - NOSTR_NPUB=${NOSTR_NPUB}
      - SITE_NAME=${SITE_NAME:-Nostr Home}
      - SITE_SUBTITLE=${SITE_SUBTITLE:-Your Decentralized Content}
    restart: unless-stopped
    networks:
      - nostr-network

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
      - /etc/letsencrypt:/etc/letsencrypt
    depends_on:
      - nostr-home
    restart: unless-stopped
    networks:
      - nostr-network

networks:
  nostr-network:
    driver: bridge
```

### nginx.conf
```nginx
events {
    worker_connections 1024;
}

http {
    upstream nostr_backend {
        server nostr-home:3000;
    }

    # Redirect HTTP to HTTPS
    server {
        listen 80;
        server_name yourdomain.com www.yourdomain.com;
        return 301 https://$server_name$request_uri;
    }

    # HTTPS Server
    server {
        listen 443 ssl http2;
        server_name yourdomain.com www.yourdomain.com;

        # SSL Configuration
        ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
        ssl_prefer_server_ciphers off;

        # Security Headers
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        add_header X-Frame-Options DENY always;
        add_header X-Content-Type-Options nosniff always;

        # WebSocket Support for Nostr Relay
        location /socket.io/ {
            proxy_pass http://nostr_backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_cache_bypass $http_upgrade;
            proxy_read_timeout 86400;
        }

        # API and regular HTTP requests
        location / {
            proxy_pass http://nostr_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

### .env file
```bash
# Your Nostr Configuration
NOSTR_NPUB=your_npub_here

# Site Branding
SITE_NAME=Your Site Name
SITE_SUBTITLE=Your Custom Subtitle

# Server Configuration
PORT=3000

# Domain (replace with your domain)
DOMAIN=yourdomain.com
```

## Docker Deployment Steps

1. **Prepare your VPS:**
```bash
# Connect to your VPS
ssh root@YOUR_VPS_IP

# Create project directory
mkdir -p /opt/nostr-home
cd /opt/nostr-home

# Clone or upload your project files
# (Upload all the files we created above)
```

2. **Install SSL Certificate:**
```bash
# Install Certbot
sudo apt install certbot -y

# Get SSL certificate (replace yourdomain.com)
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Verify certificate location
sudo ls -la /etc/letsencrypt/live/yourdomain.com/
```

3. **Configure and Deploy:**
```bash
# Edit your .env file with your actual values
nano .env

# Update nginx.conf with your domain
sed -i 's/yourdomain.com/YOUR_ACTUAL_DOMAIN/g' nginx.conf

# Build and start the application
docker-compose up -d

# Check status
docker-compose ps
docker-compose logs -f nostr-home
```

4. **Setup SSL Auto-Renewal:**
```bash
# Add cron job for certificate renewal
echo "0 3 * * * certbot renew --quiet && docker-compose restart nginx" | sudo crontab -
```

# Option 2: Traditional VPS Deployment

For users preferring traditional deployment without Docker.

## System Setup

1. **Initial Server Setup:**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3 python3-pip python3-venv git nginx certbot python3-certbot-nginx sqlite3 supervisor

# Create application user
sudo useradd -m -s /bin/bash nostr
sudo usermod -aG sudo nostr

# Switch to application user
sudo su - nostr
```

2. **Application Setup:**
```bash
# Create project directory
mkdir -p /home/nostr/nostr-home
cd /home/nostr/nostr-home

# Upload your project files or clone from repository

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create data directory
mkdir -p data

# Test the application
python app.py
# (Should see the server start successfully)
```

3. **SSL Certificate:**
```bash
# Install SSL certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

4. **Nginx Configuration:**
```bash
sudo nano /etc/nginx/sites-available/nostr-home
```

```nginx
# /etc/nginx/sites-available/nostr-home
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # WebSocket support for Nostr relay
    location /socket.io/ {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 86400;
    }

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

5. **Enable Nginx Site:**
```bash
sudo ln -s /etc/nginx/sites-available/nostr-home /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

6. **Process Management with Supervisor:**
```bash
sudo nano /etc/supervisor/conf.d/nostr-home.conf
```

```ini
[program:nostr-home]
command=/home/nostr/nostr-home/venv/bin/python app.py
directory=/home/nostr/nostr-home
user=nostr
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/supervisor/nostr-home.log
environment=PATH="/home/nostr/nostr-home/venv/bin"
```

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start nostr-home
sudo supervisorctl status
```

## Configuration

### Environment Variables (.env file)
```bash
# Create .env file in your project directory
nano .env
```

```bash
# Your Nostr public key (required)
NOSTR_NPUB=npub1your_actual_npub_here

# Site customization
SITE_NAME=Your Personal Site
SITE_SUBTITLE=Powered by Nostr

# Server settings
PORT=3000

# Database (optional, defaults to ./data/nostr_content.db)
DATABASE_PATH=./data/nostr_content.db

# Relay settings (optional)
RELAY_NAME=Your Personal Relay
RELAY_DESCRIPTION=Personal Nostr relay and content hub
RELAY_CONTACT=admin@yourdomain.com
```

### Security Configuration

1. **Firewall Setup:**
```bash
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

2. **Fail2Ban (Optional but recommended):**
```bash
sudo apt install fail2ban -y
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

## Monitoring and Maintenance

### Log Monitoring
```bash
# Application logs (Docker)
docker-compose logs -f nostr-home

# Application logs (Traditional)
sudo tail -f /var/log/supervisor/nostr-home.log

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Database Backup
```bash
# Create backup script
nano backup.sh
```

```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/home/nostr/backups"
mkdir -p $BACKUP_DIR

# Backup database
sqlite3 /home/nostr/nostr-home/data/nostr_content.db ".backup $BACKUP_DIR/nostr_content_$DATE.db"

# Keep only last 30 days of backups
find $BACKUP_DIR -name "*.db" -mtime +30 -delete

echo "Backup completed: nostr_content_$DATE.db"
```

```bash
chmod +x backup.sh

# Add to crontab (daily backup at 2 AM)
crontab -e
# Add line: 0 2 * * * /home/nostr/backup.sh
```

### Updates and Maintenance

#### Docker Deployment Updates
```bash
cd /opt/nostr-home

# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

#### Traditional Deployment Updates
```bash
cd /home/nostr/nostr-home

# Activate virtual environment
source venv/bin/activate

# Pull latest code
git pull origin main

# Update dependencies
pip install -r requirements.txt

# Restart application
sudo supervisorctl restart nostr-home
```

## Testing Your Deployment

1. **Basic Functionality Test:**
   - Visit `https://yourdomain.com` (should load your site)
   - Check `https://yourdomain.com/posts` (should show posts)
   - Verify `https://yourdomain.com/api/relay/info` (relay information)

2. **WebSocket Test:**
   - Open browser developer tools
   - Check WebSocket connection in Network tab
   - Should see successful WSS connection to your relay

3. **SSL Test:**
   - Use [SSL Labs Test](https://www.ssllabs.com/ssltest/)
   - Should get A+ rating with proper configuration

## Troubleshooting

### Common Issues

1. **Port 3000 already in use:**
   ```bash
   sudo lsof -i :3000
   sudo kill -9 PID_NUMBER
   ```

2. **SSL certificate issues:**
   ```bash
   sudo certbot renew --dry-run
   sudo nginx -t
   ```

3. **Database permissions:**
   ```bash
   sudo chown -R nostr:nostr /home/nostr/nostr-home/data/
   chmod 644 /home/nostr/nostr-home/data/nostr_content.db
   ```

4. **WebSocket connection failed:**
   - Check nginx configuration for upgrade headers
   - Verify firewall allows HTTPS traffic
   - Test with `wscat -c wss://yourdomain.com/socket.io/`

### Performance Optimization

1. **Nginx Caching:**
   ```nginx
   # Add to server block
   location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
       expires 1y;
       add_header Cache-Control "public, immutable";
   }
   ```

2. **Database Optimization:**
   ```bash
   # Regular database maintenance
   sqlite3 data/nostr_content.db "VACUUM;"
   sqlite3 data/nostr_content.db "ANALYZE;"
   ```

## Security Best Practices

1. **Regular Updates:**
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

2. **SSH Key Authentication:**
   - Disable password authentication
   - Use SSH keys only
   - Change default SSH port

3. **Database Security:**
   - Regular backups
   - Proper file permissions
   - Monitor for unusual activity

4. **Application Security:**
   - Keep dependencies updated
   - Monitor logs for errors
   - Use environment variables for sensitive data

## Cost Estimation

### Monthly Costs
- **VPS**: $5-15/month (depending on specs)
- **Domain**: $1-2/month (annual payment)
- **SSL**: $0 (Let's Encrypt is free)
- **Total**: $6-17/month

### Additional Costs (Optional)
- **Backup Storage**: $1-5/month
- **CDN**: $0-10/month (Cloudflare free tier available)
- **Monitoring**: $0-20/month (many free options)

## Conclusion

This deployment guide provides two robust options for hosting your Nostr Home:

- **Docker** (recommended): Easier deployment, better isolation, simpler updates
- **Traditional**: More control, direct system access, familiar environment

Both approaches provide:
- ✅ HTTPS/WSS encryption
- ✅ Professional deployment
- ✅ Automatic SSL renewal
- ✅ Process monitoring
- ✅ Easy maintenance
- ✅ Scalable architecture

Choose the approach that best fits your technical comfort level and operational preferences.
