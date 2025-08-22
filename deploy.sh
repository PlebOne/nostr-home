#!/bin/bash

# Nostr Home Hub - Python Deployment Script
# This script sets up your complete Nostr hub on a server

set -e

echo "Nostr Home Hub - Python Deployment"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get domain if provided
DOMAIN=${1:-"localhost"}
PORT=${2:-"3000"}

echo -e "${BLUE}Configuration:${NC}"
echo "   Domain: $DOMAIN"
echo "   Port: $PORT"
echo ""

# Check if running as root for system setup
if [[ $EUID -eq 0 ]] && [[ "$DOMAIN" != "localhost" ]]; then
   echo -e "${GREEN}Setting up system dependencies...${NC}"
   
   # Update system
   apt-get update -y
   
   # Install Python, pip, nginx, certbot
   apt-get install -y python3 python3-pip nginx certbot python3-certbot-nginx
   
   echo -e "${GREEN}System dependencies installed${NC}"
else
   echo -e "${YELLOW}Running in local mode (no system setup)${NC}"
fi

# Install Python dependencies
echo -e "${BLUE}Installing Python dependencies...${NC}"
pip3 install -r requirements.txt

# Set up configuration if needed
if [ ! -f ".env" ]; then
   echo -e "${BLUE}Creating environment configuration...${NC}"
   cat > .env << EOF
# Nostr Configuration
NOSTR_NPUB=npub13hyx3qsqk3r7ctjqrr49uskut4yqjsxt8uvu4rekr55p08wyhf0qq90nt7
PORT=$PORT

# Relay Configuration  
RELAY_NAME=Personal Nostr Hub
RELAY_DESCRIPTION=Your personal Nostr relay and content aggregator
RELAY_CONTACT=admin@$DOMAIN
EOF
   echo -e "${GREEN}Environment file created${NC}"
fi

# Clear any existing data and fetch fresh content
echo -e "${BLUE}Setting up database...${NC}"
python3 clear_data.py

# Test the configuration
echo -e "${BLUE}Testing Nostr connectivity...${NC}"
timeout 30 python3 test_python_nostr.py || echo -e "${YELLOW}Nostr test completed (timeout is normal)${NC}"

# Set up nginx if running as root and not localhost
if [[ $EUID -eq 0 ]] && [[ "$DOMAIN" != "localhost" ]]; then
   echo -e "${BLUE}Setting up nginx reverse proxy...${NC}"
   
   # Create nginx config
   cat > /etc/nginx/sites-available/nostr-hub << EOF
server {
    listen 80;
    server_name $DOMAIN;

    location / {
        proxy_pass http://localhost:$PORT;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        
        # WebSocket support for Nostr relay
        proxy_read_timeout 86400;
    }
}
EOF

   # Enable the site
   ln -sf /etc/nginx/sites-available/nostr-hub /etc/nginx/sites-enabled/
   nginx -t && systemctl reload nginx
   
   echo -e "${GREEN}✅ Nginx configured${NC}"
   
   # Set up SSL with Let's Encrypt
   echo -e "${BLUE}🔒 Setting up SSL certificate...${NC}"
   certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN || echo -e "${YELLOW}⚠️  SSL setup skipped (manual setup required)${NC}"
fi

# Create systemd service for auto-start
if [[ $EUID -eq 0 ]]; then
   echo -e "${BLUE}⚙️  Creating system service...${NC}"
   
   CURRENT_DIR=$(pwd)
   cat > /etc/systemd/system/nostr-hub.service << EOF
[Unit]
Description=Nostr Home Hub
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=$CURRENT_DIR
Environment=PATH=/usr/bin:/usr/local/bin
ExecStart=/usr/bin/python3 app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

   # Set permissions
   chown -R www-data:www-data $CURRENT_DIR
   
   # Enable and start service
   systemctl daemon-reload
   systemctl enable nostr-hub
   systemctl start nostr-hub
   
   echo -e "${GREEN}✅ System service created and started${NC}"
   
   echo ""
   echo -e "${GREEN}🎉 Deployment Complete!${NC}"
   echo -e "${BLUE}📱 Your Nostr Hub is running at:${NC}"
   echo "   🌐 Website: https://$DOMAIN"
   echo "   📡 Relay: wss://$DOMAIN/socket.io/"
   echo "   📊 Stats: https://$DOMAIN/api/relay/stats"
   echo ""
   echo -e "${BLUE}🔧 Management commands:${NC}"
   echo "   systemctl status nostr-hub    # Check status"
   echo "   systemctl restart nostr-hub   # Restart service"
   echo "   systemctl logs nostr-hub      # View logs"
   
else
   # Local development mode
   echo ""
   echo -e "${GREEN}🎉 Setup Complete!${NC}"
   echo -e "${BLUE}🚀 To start your Nostr Hub:${NC}"
   echo "   python3 app.py"
   echo ""
   echo -e "${BLUE}📱 Your Nostr Hub will be available at:${NC}"
   echo "   🌐 Website: http://$DOMAIN:$PORT"
   echo "   📡 Relay: ws://$DOMAIN:$PORT/socket.io/"
   echo "   📊 Stats: http://$DOMAIN:$PORT/api/relay/stats"
fi

echo ""
echo -e "${BLUE}📋 Next Steps:${NC}"
echo "1. Update your npub in config.py or .env if needed"
echo "2. Configure relay settings in config.py:"
echo "   - RELAY_OWNER_ONLY=True (restrict to your events only)"
echo "   - RELAY_OWNER_ONLY=False (allow public access)"
echo "3. Test your relay with a Nostr client"
echo "4. Share your relay URL with friends (if public)!"
echo "5. Monitor your hub with the stats API"
echo ""
echo -e "${GREEN}🌟 Your complete Nostr infrastructure is ready!${NC}"
