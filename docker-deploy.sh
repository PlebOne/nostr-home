#!/bin/bash

# Nostr Home Docker Quick Deploy Script
# This script automates the Docker deployment process

set -e

echo "🚀 Nostr Home Docker Quick Deploy Script"
echo "========================================"

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "❌ Please don't run this script as root"
    echo "   Run as regular user with sudo privileges"
    exit 1
fi

# Check if domain is provided
if [ -z "$1" ]; then
    echo "❌ Usage: ./docker-deploy.sh yourdomain.com"
    echo "   Example: ./docker-deploy.sh myblog.example.com"
    exit 1
fi

DOMAIN=$1
PROJECT_DIR="/opt/nostr-home"

echo "📋 Configuration:"
echo "   Domain: $DOMAIN"
echo "   Project Directory: $PROJECT_DIR"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "📦 Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    echo "✅ Docker installed successfully"
else
    echo "✅ Docker already installed"
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "📦 Installing Docker Compose..."
    sudo apt update
    sudo apt install -y docker-compose
    echo "✅ Docker Compose installed successfully"
else
    echo "✅ Docker Compose already installed"
fi

# Create project directory
echo "📁 Creating project directory..."
sudo mkdir -p $PROJECT_DIR
sudo chown $USER:$USER $PROJECT_DIR

# Copy files to project directory
echo "📂 Copying project files..."
cp -r . $PROJECT_DIR/
cd $PROJECT_DIR

# Update domain in nginx configuration
echo "🔧 Configuring nginx for domain: $DOMAIN"
sed -i "s/yourdomain.com/$DOMAIN/g" nginx.conf

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating environment configuration..."
    cp .env.example .env
    echo ""
    echo "⚙️  Please configure your .env file:"
    echo "   - Set your NOSTR_NPUB"
    echo "   - Customize SITE_NAME and SITE_SUBTITLE"
    echo "   - Update DOMAIN to $DOMAIN"
    echo ""
    read -p "Press Enter to edit .env file..." -r
    nano .env
fi

# Install Certbot for SSL
echo "🔒 Installing Certbot for SSL certificates..."
sudo apt update
sudo apt install -y certbot

# Get SSL certificate
echo "🔐 Getting SSL certificate for $DOMAIN..."
echo "   Make sure your domain points to this server's IP address!"
read -p "Press Enter when ready to get SSL certificate..." -r

# Stop any existing nginx containers
docker-compose down nginx 2>/dev/null || true

# Get the certificate
sudo certbot certonly --standalone -d $DOMAIN -d www.$DOMAIN

# Verify certificate
if [ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
    echo "✅ SSL certificate obtained successfully"
else
    echo "❌ SSL certificate not found. Please check your domain configuration."
    exit 1
fi

# Build and start the application
echo "🏗️  Building and starting Nostr Home..."
docker-compose build
docker-compose up -d

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 10

# Check if services are running
if docker-compose ps | grep -q "Up"; then
    echo "✅ Services are running successfully!"
else
    echo "❌ Some services failed to start. Checking logs..."
    docker-compose logs
    exit 1
fi

# Setup SSL renewal cron job
echo "🔄 Setting up SSL certificate auto-renewal..."
(crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet && cd $PROJECT_DIR && docker-compose restart nginx") | crontab -

echo ""
echo "🎉 Deployment completed successfully!"
echo ""
echo "🌐 Your Nostr Home is now available at:"
echo "   https://$DOMAIN"
echo "   https://www.$DOMAIN"
echo ""
echo "📡 Your Nostr relay endpoint:"
echo "   wss://$DOMAIN/socket.io/"
echo ""
echo "📊 Useful commands:"
echo "   Check status: cd $PROJECT_DIR && docker-compose ps"
echo "   View logs: cd $PROJECT_DIR && docker-compose logs -f"
echo "   Restart: cd $PROJECT_DIR && docker-compose restart"
echo "   Update: cd $PROJECT_DIR && git pull && docker-compose build && docker-compose up -d"
echo ""
echo "💡 Don't forget to:"
echo "   1. Configure your Nostr client to use your relay"
echo "   2. Update your site configuration in the .env file"
echo "   3. Set up regular backups of your data directory"
echo ""
