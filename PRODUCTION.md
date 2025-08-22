# Nostr Home - Production Deployment Guide

## Quick Start (Recommended)

For the fastest deployment, use our Docker setup:

```bash
# 1. Get the code
git clone <your-repo> nostr-home
cd nostr-home

# 2. Run the deployment script
./docker-deploy.sh yourdomain.com

# 3. Follow the prompts to configure your .env file
# 4. Wait for SSL certificate setup
# 5. Your site will be live at https://yourdomain.com
```

## Detailed Deployment Options

### Option 1: Docker Deployment (Recommended) 🐳

**Advantages:**
- ✅ One-command deployment
- ✅ Isolated environment
- ✅ Easy updates and rollbacks
- ✅ Automatic SSL setup
- ✅ Production-ready configuration

**Requirements:**
- Ubuntu 22.04+ VPS with 1GB+ RAM
- Domain pointing to your server
- Sudo access

### Option 2: Traditional VPS Deployment 🖥️

**Advantages:**
- ✅ Direct system control
- ✅ Familiar environment
- ✅ Easy debugging
- ✅ Lower resource usage

**Requirements:**
- Ubuntu 22.04+ VPS with 1GB+ RAM
- Python 3.11+
- Manual configuration required

## VPS Specifications

### Minimum Requirements (Personal Use)
- **CPU**: 1 vCPU
- **RAM**: 1 GB
- **Storage**: 10 GB SSD
- **Bandwidth**: 1 TB/month
- **Cost**: $5-6/month

### Recommended (Small Community)
- **CPU**: 2 vCPU
- **RAM**: 2-4 GB
- **Storage**: 20-40 GB SSD
- **Bandwidth**: 2 TB/month
- **Cost**: $12-15/month

### High Performance (Large Community)
- **CPU**: 4 vCPU
- **RAM**: 8 GB
- **Storage**: 80 GB SSD
- **Bandwidth**: 4+ TB/month
- **Cost**: $40-60/month

## Provider Recommendations

| Provider | Plan | Monthly Cost | Specs |
|----------|------|--------------|-------|
| **DigitalOcean** | Basic Droplet | $6 | 1GB RAM, 1 vCPU, 25GB SSD |
| **Linode** | Nanode 1GB | $5 | 1GB RAM, 1 vCPU, 25GB SSD |
| **Vultr** | Regular Performance | $6 | 1GB RAM, 1 vCPU, 25GB SSD |
| **Hetzner** | CX11 | €4.15 | 1GB RAM, 1 vCPU, 20GB SSD |
| **AWS** | t3.micro | ~$9 | 1GB RAM, 2 vCPU, EBS storage |

## HTTPS and WSS Setup

Your deployment automatically includes:

- ✅ **HTTPS**: Let's Encrypt SSL certificates (free)
- ✅ **WSS**: WebSocket Secure for Nostr relay
- ✅ **Auto-renewal**: Certificates renew automatically
- ✅ **Security headers**: HSTS, X-Frame-Options, etc.
- ✅ **HTTP redirect**: All traffic redirected to HTTPS

## Files Overview

Your deployment includes these key files:

```
nostr-home/
├── Dockerfile              # Container definition
├── docker-compose.yml      # Multi-service orchestration
├── nginx.conf              # Reverse proxy configuration
├── docker-deploy.sh        # One-command deployment
├── .env.example            # Environment configuration template
├── DEPLOYMENT.md           # This comprehensive guide
└── app.py                  # Main application
```

## Security Features

✅ **SSL/TLS Encryption**: All traffic encrypted  
✅ **HSTS**: HTTP Strict Transport Security enabled  
✅ **Owner-only relay**: Restricted to your Nostr pubkey  
✅ **Security headers**: Protection against common attacks  
✅ **Firewall ready**: UFW configuration included  
✅ **Auto-updates**: SSL certificates renew automatically  

## Monitoring and Logs

### View Application Status
```bash
cd /opt/nostr-home
docker-compose ps
```

### View Live Logs
```bash
cd /opt/nostr-home
docker-compose logs -f nostr-home
```

### Check Nginx Logs
```bash
cd /opt/nostr-home
docker-compose logs -f nginx
```

### Monitor System Resources
```bash
htop
df -h
```

## Backup Strategy

### Automated Database Backup
```bash
# Add to crontab for daily backups
0 2 * * * cd /opt/nostr-home && docker-compose exec -T nostr-home sqlite3 /app/data/nostr_content.db ".backup /app/data/backup_$(date +\%Y\%m\%d).db"
```

### Manual Backup
```bash
cd /opt/nostr-home
docker-compose exec nostr-home sqlite3 /app/data/nostr_content.db ".backup /app/data/manual_backup.db"
docker cp $(docker-compose ps -q nostr-home):/app/data/manual_backup.db ./backup.db
```

## Updates and Maintenance

### Update Application
```bash
cd /opt/nostr-home
git pull origin main
docker-compose build --no-cache
docker-compose up -d
```

### Restart Services
```bash
cd /opt/nostr-home
docker-compose restart
```

### View Resource Usage
```bash
docker stats
```

## Troubleshooting

### Common Issues

**1. Port 80/443 already in use:**
```bash
sudo lsof -i :80
sudo lsof -i :443
# Kill any conflicting processes
```

**2. SSL certificate failed:**
```bash
# Check domain DNS
nslookup yourdomain.com
# Ensure port 80 is open
sudo ufw status
```

**3. Database permission errors:**
```bash
cd /opt/nostr-home
sudo chown -R 1000:1000 data/
```

**4. Container won't start:**
```bash
cd /opt/nostr-home
docker-compose logs nostr-home
```

### Performance Issues

**High CPU usage:**
- Check relay connection count
- Monitor database queries
- Consider upgrading VPS

**High memory usage:**
- Check for memory leaks in logs
- Restart containers periodically
- Upgrade RAM if needed

**Slow database:**
```bash
# Optimize database
docker-compose exec nostr-home sqlite3 /app/data/nostr_content.db "VACUUM; ANALYZE;"
```

## Configuration

### Environment Variables (.env)
```bash
# Required
NOSTR_NPUB=npub1your_public_key_here
DOMAIN=yourdomain.com

# Optional customization
SITE_NAME=Your Site Name
SITE_SUBTITLE=Your Custom Subtitle
PORT=3000

# Relay settings
RELAY_NAME=Your Personal Relay
RELAY_DESCRIPTION=Personal Nostr relay and content hub
```

### Nginx Customization

Edit `nginx.conf` for:
- Custom headers
- Rate limiting
- Cache configuration
- Additional security

### Application Customization

Edit these files:
- `config.py`: Application settings
- `styles.css`: Visual customization
- HTML templates: Layout changes

## Integration with Nostr Clients

Your deployed relay URL will be:
```
wss://yourdomain.com/socket.io/
```

### Popular Nostr Clients
- **Damus** (iOS): Add relay in settings
- **Amethyst** (Android): Add relay in relay list
- **Iris** (Web): Connect to your relay
- **Nostros** (Mobile): Add relay URL

### API Endpoints
- `https://yourdomain.com/api/relay/info` - Relay information
- `https://yourdomain.com/api/relay/stats` - Usage statistics
- `https://yourdomain.com/api/posts` - Your posts
- `https://yourdomain.com/api/config` - Site configuration

## Cost Optimization

### Reduce Costs
1. **Use Hetzner**: Cheapest reliable option (€4.15/month)
2. **Annual billing**: Often 10-20% discount
3. **Cloudflare**: Free CDN and DDoS protection
4. **Monitoring**: Use free tier services

### Scale Up When Needed
- Start with 1GB RAM
- Monitor usage with `htop`
- Upgrade when consistently using >80% resources

## Going Live Checklist

### Before Deployment
- [ ] Purchase domain name
- [ ] Point domain to VPS IP
- [ ] Have your Nostr npub ready
- [ ] VPS meets minimum requirements

### During Deployment
- [ ] Run `./docker-deploy.sh yourdomain.com`
- [ ] Configure .env file with your details
- [ ] Wait for SSL certificate setup
- [ ] Verify services are running

### After Deployment
- [ ] Test website at https://yourdomain.com
- [ ] Test relay connection
- [ ] Add relay to your Nostr client
- [ ] Set up monitoring/backups
- [ ] Configure firewall if needed

### Post-Launch
- [ ] Monitor logs for errors
- [ ] Set up automated backups
- [ ] Join Nostr relay communities
- [ ] Share your relay with friends

## Advanced Features

### Load Balancing (High Traffic)
```yaml
# Add to docker-compose.yml
services:
  nostr-home-2:
    build: .
    # ... duplicate configuration
```

### Database Replication
```bash
# Set up SQLite backup replication
# Consider PostgreSQL for high-scale deployments
```

### CDN Integration
```bash
# Cloudflare setup for static assets
# Improves global performance
```

## Support and Community

### Getting Help
- Check logs first: `docker-compose logs -f`
- Review this guide thoroughly
- Test on local machine first

### Contributing
- Report issues with detailed logs
- Submit feature requests
- Share deployment experiences

## Summary

This deployment guide provides everything needed to run your Nostr Home professionally:

- **Quick deployment**: One command setup with Docker
- **Professional grade**: SSL, security headers, monitoring
- **Cost effective**: Starting at $5/month
- **Scalable**: Easy to upgrade as you grow
- **Secure**: Owner-only relay with modern security
- **Maintainable**: Automated updates and backups

Choose Docker deployment for the easiest experience, or traditional deployment for maximum control. Both approaches will give you a production-ready Nostr hub that you can be proud to share with the world.

**Ready to deploy? Run: `./docker-deploy.sh yourdomain.com`** 🚀
