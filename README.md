# Nostr Home

A comprehensive decentralized content platform and Nostr relay implementation that aggregates and displays your Nostr content with automatic caching and a modern web interface.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Quick Start](#quick-start)
- [Documentation](#documentation)
- [Installation](#installation)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [API Reference](#api-reference)
- [Development](#development)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)

## Overview

Nostr Home is a Flask-based web application that serves as both a content aggregation platform and a fully-featured Nostr relay. It connects to multiple Nostr relays, caches content locally, and presents it through a beautiful, responsive web interface while simultaneously operating as an enhanced Nostr relay with support for 23 NIPs (Nostr Implementation Possibilities).

### Key Components

- **Web Interface**: Modern, responsive frontend for browsing Nostr content
- **Enhanced Relay**: Full Nostr relay implementation with 23 NIP support
- **Content Aggregation**: Automatic fetching and caching from multiple relays
- **Database Layer**: SQLite-based storage with optimized queries
- **Docker Support**: Complete containerization for easy deployment

## Features

### Content Display
- **Long-form Posts**: Display detailed articles and long-form content
- **Quips**: Show short thoughts and quick updates
- **Image Gallery**: Visual content with automatic image detection and optimization
- **Real-time Updates**: Live content updates from connected relays

### Relay Features
- **Complete NIP Implementation**: 23 NIPs fully implemented and tested
  - **Core Protocol**: NIP-01, 11, 15, 20 (WebSocket, Info, EOSE, Commands)
  - **Advanced Queries**: NIP-12, 45, 50 (Tag Filtering, COUNT, Search)
  - **Event Management**: NIP-09, 16, 33 (Deletion, Replaceable, Parameterized)
  - **Security**: NIP-22, 42, 13 (Time Limits, Auth, Proof of Work)
  - **Content Types**: NIP-02, 04, 25, 28 (Contacts, DMs, Reactions, Chat)
  - **Advanced**: NIP-26, 40, 65, 05 (Delegation, Expiration, Relay Lists, DNS)
- **High Performance**: Go-based implementation with optimized database queries
- **Owner-only Mode**: Configurable restriction to specific pubkey
- **Real-time Broadcasting**: Efficient event distribution to all subscribers
- **Comprehensive Validation**: Event verification, signature checking, and filtering
- **Statistics Dashboard**: Real-time relay metrics and monitoring

### Technical Features
- **Automatic Caching**: Intelligent content caching with configurable intervals
- **Multi-relay Support**: Connect to multiple Nostr relays simultaneously
- **Dark/Light Theme**: User-configurable interface themes
- **Responsive Design**: Mobile-first, responsive web interface
- **API Endpoints**: RESTful API for programmatic access

## Quick Start

### Using Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/nostr-home.git
cd nostr-home

# Run the deployment script
./docker-deploy.sh yourdomain.com
```

### Manual Installation

```bash
# Clone and setup
git clone https://github.com/yourusername/nostr-home.git
cd nostr-home

# Install dependencies
pip install -r requirements.txt

# Configure your settings
cp .env.example .env
# Edit .env with your configuration

# Run the application
python app.py
```

## Documentation

This project includes comprehensive documentation:

### Deployment Guides
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Complete VPS deployment guide with both Docker and traditional approaches
- **[PRODUCTION.md](PRODUCTION.md)** - Production deployment guide with cost estimates and provider recommendations

### Setup and Configuration
- **[SETUP.md](SETUP.md)** - Initial setup and configuration instructions
- **[README_RELAY.md](README_RELAY.md)** - Detailed relay functionality and NIP implementation documentation

### Technical Documentation
- **[RELAY_NIPS.md](RELAY_NIPS.md)** - Complete list of supported NIPs with implementation details

### Quick Reference
- **[.env.example](.env.example)** - Environment configuration template
- **[requirements.txt](requirements.txt)** - Python dependencies

## Installation

### Prerequisites

- Python 3.11 or higher
- SQLite 3
- Git

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/nostr-home.git
   cd nostr-home
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env file with your settings
   ```

5. **Initialize database**
   ```bash
   python app.py
   # Database will be created automatically on first run
   ```

### Production Deployment

For production deployment, see our comprehensive guides:
- [Docker Deployment](DEPLOYMENT.md#docker-deployment-recommended) - One-command deployment with SSL
- [Traditional VPS](DEPLOYMENT.md#traditional-vps-deployment) - Manual server setup
- [Production Guide](PRODUCTION.md) - Complete production deployment walkthrough

## Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```bash
# Required: Your Nostr public key
NOSTR_NPUB=npub1your_public_key_here

# Site Branding
SITE_NAME=Your Site Name
SITE_SUBTITLE=Your Custom Subtitle

# Server Configuration
PORT=3000

# Relay Settings (Optional)
RELAY_NAME=Your Personal Relay
RELAY_DESCRIPTION=Personal Nostr relay and content hub
```

### Core Configuration

Edit `config.py` for advanced configuration:

- **Relay List**: Configure which Nostr relays to connect to
- **Cache Settings**: Adjust update intervals and storage options
- **Database Settings**: Customize database location and settings
- **Relay Features**: Enable/disable specific relay functionality

### Site Customization

The application supports complete site customization:
- **Dynamic Branding**: Site name and subtitle update across all pages
- **Theme Support**: Built-in dark/light theme switching
- **Custom Styling**: Modify `public/styles.css` for visual customization

## Deployment

### Minimum VPS Requirements

- **CPU**: 1 vCPU
- **RAM**: 1 GB (2 GB recommended)
- **Storage**: 10 GB SSD
- **Bandwidth**: 1 TB/month
- **Cost**: Starting at $5/month

### Supported Providers

- DigitalOcean, Linode, Vultr, Hetzner, AWS
- Complete setup guides available in [DEPLOYMENT.md](DEPLOYMENT.md)

### SSL and Security

- Automatic SSL certificate provisioning with Let's Encrypt
- WebSocket Secure (WSS) support for Nostr relay
- Security headers and HTTPS redirection
- Firewall configuration guidelines

## API Reference

### Content Endpoints

- `GET /api/posts` - Retrieve paginated posts
- `GET /api/quips` - Retrieve paginated short posts
- `GET /api/images` - Retrieve image gallery content
- `GET /api/stats` - Get content statistics

### Relay Endpoints

- `GET /api/relay/info` - Relay information (NIP-11)
- `GET /api/relay/stats` - Relay statistics and metrics
- `WebSocket /socket.io/` - Nostr relay protocol endpoint

### Configuration Endpoints

- `GET /api/config` - Site configuration and branding
- `POST /api/update-cache` - Trigger content cache update

### Example API Usage

```bash
# Get posts
curl https://yourdomain.com/api/posts?page=1

# Get relay info
curl https://yourdomain.com/api/relay/info

# Get site configuration
curl https://yourdomain.com/api/config
```

## Development

### Project Structure

```
nostr-home/
├── app.py                      # Main Flask application
├── config.py                   # Configuration settings
├── database.py                 # Database models and operations
├── nostr_client.py            # Nostr client implementation
├── nostr_relay_enhanced.py    # Enhanced relay with 23 NIP support
├── public/                    # Frontend assets
│   ├── index.html             # Main page
│   ├── posts.html             # Posts page
│   ├── quips.html             # Quips page
│   ├── gallery.html           # Gallery page
│   ├── relay.html             # Relay dashboard
│   ├── app.js                 # Main JavaScript
│   ├── site-config.js         # Dynamic site configuration
│   └── styles.css             # CSS styles
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Docker container definition
├── docker-compose.yml         # Multi-service orchestration
├── nginx.conf                 # Reverse proxy configuration
└── deploy scripts/            # Deployment automation
```

### Running Tests

```bash
# Test relay functionality
python test_relay.py

# Test enhanced relay features
python test_enhanced_relay.py

# Test owner-only mode
python test_owner_only.py

# Test HTTP endpoints
python test_relay_http.py
```

### Development Workflow

1. **Make changes** to source code
2. **Test locally** using `python app.py`
3. **Run tests** to ensure functionality
4. **Update documentation** if needed
5. **Commit changes** with descriptive messages

## Testing

### Automated Tests

The project includes comprehensive test suites:

- **Relay Tests**: Verify Nostr protocol compliance
- **HTTP Tests**: Validate API endpoints
- **Integration Tests**: End-to-end functionality testing
- **Owner Mode Tests**: Security and access control validation

### Manual Testing

1. **Start the application**: `python app.py`
2. **Visit web interface**: `http://localhost:3000`
3. **Test relay connection**: Use a Nostr client to connect to `ws://localhost:3000/socket.io/`
4. **Verify API endpoints**: Test using curl or Postman

## Contributing

### Getting Started

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and add tests
4. Ensure all tests pass: `python -m pytest`
5. Commit your changes: `git commit -am 'Add feature'`
6. Push to the branch: `git push origin feature-name`
7. Submit a pull request

### Development Guidelines

- Follow PEP 8 Python style guidelines
- Add tests for new functionality
- Update documentation for new features
- Use descriptive commit messages
- Ensure backward compatibility when possible

### Areas for Contribution

- Additional NIP implementations
- Frontend improvements and themes
- Performance optimizations
- Additional relay features
- Documentation improvements
- Testing and bug fixes

## Supported NIPs

The relay implementation supports 23 Nostr Implementation Possibilities:

**Core Protocol**: NIP-01 (Basic protocol), NIP-02 (Contact lists), NIP-03 (OpenTimestamps)
**Enhanced Features**: NIP-04 (Encrypted DMs), NIP-05 (DNS-based verification), NIP-09 (Event deletion)
**Advanced Features**: NIP-11 (Relay info), NIP-12 (Generic tags), NIP-15 (End of stored events)

For complete NIP documentation, see [RELAY_NIPS.md](RELAY_NIPS.md).

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Support

- **Documentation**: Comprehensive guides in the `/docs` directory
- **Issues**: Report bugs and request features via GitHub Issues
- **Community**: Join the Nostr community for discussions and support

## Acknowledgments

- Built on the Nostr protocol specification
- Inspired by the decentralized web movement
- Thanks to the Nostr development community

---

**Nostr Home** - Your gateway to the decentralized web.
