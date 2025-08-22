# Nostr Home Hub - Complete Setup

## What You Now Have

Your Nostr Home has been **completely transformed** into a full Nostr Hub with these capabilities:

### Web Interface (Existing)
- **Posts Page**: Long-form content with titles (500+ chars)
- **Quips Page**: Short thoughts and replies
- **Gallery Page**: Image content
- **Homepage**: Stats and content previews

### Built-in Nostr Relay (NEW!)
- **Full Nostr Relay**: Accepts and stores events from any client
- **WebSocket Endpoint**: `ws://localhost:3000/socket.io/`
- **NIP-01 Compatible**: Standard Nostr protocol support
- **Event Storage**: All events stored in SQLite database
- **Subscription Management**: Handles multiple client subscriptions

### Content Aggregator (Improved)
- **Concurrent Fetching**: Connects to all relays simultaneously
- **10-second Timeouts**: No more hanging on slow relays
- **Priority Relays**: Damus first, then Primal, then others
- **Smart Classification**: Better detection of long-form posts

### Monitoring & Stats
- **Relay Stats**: `http://localhost:3000/api/relay/stats`
- **Relay Info**: `http://localhost:3000/api/relay/info` (NIP-11)
- **Web Stats**: Content counts and activity

## Quick Start

### 1. Install Dependencies
```bash
pip3 install flask flask-cors flask-socketio websocket-client requests python-dotenv schedule
```

### 2. Start Your Hub
```bash
python3 app.py
```

### 3. Access Your Hub
- **Website**: http://localhost:3000
- **Relay**: ws://localhost:3000/socket.io/
- **Stats**: http://localhost:3000/api/relay/stats
- **Info**: http://localhost:3000/api/relay/info

## Using Your Relay

### Connect Nostr Clients
Add your relay to any Nostr client:
```
ws://localhost:3000/socket.io/
```

### Publish Events
Your relay accepts events from any Nostr client and stores them permanently.

### Subscribe to Events
Clients can subscribe to get real-time events based on filters.

## Easy Server Deployment

### Local Testing
```bash
python3 app.py
```

### Server Deployment
```bash
./deploy.sh your-domain.com
```

This script automatically:
- Installs system dependencies
- Sets up nginx reverse proxy
- Configures SSL with Let's Encrypt
- Creates systemd service for auto-start
- Sets up proper permissions

## Configuration

### Edit `config.py`:
```python
# Your Nostr identity
NOSTR_NPUB = "your_npub_here"

# Relay settings
RELAY_ENABLED = True
RELAY_NAME = "Your Personal Hub"
RELAY_DESCRIPTION = "Your personal Nostr relay and blog"

# Content settings  
MAX_POSTS_PER_PAGE = 20
RELAY_MAX_EVENTS_PER_REQUEST = 500
```

## API Endpoints

### Web Interface
- `GET /` - Homepage
- `GET /posts` - Long-form posts
- `GET /quips` - Short content
- `GET /gallery` - Images

### Content API
- `GET /api/posts` - Posts data
- `GET /api/quips` - Quips data  
- `GET /api/images` - Images data
- `GET /api/stats` - Content statistics
- `POST /api/update-cache` - Manual content refresh

### Relay API
- `GET /api/relay/info` - Relay information (NIP-11)
- `GET /api/relay/stats` - Relay statistics
- `WebSocket /socket.io/` - Nostr protocol endpoint

## 🗄️ Database Schema

### Content Tables (Existing)
- `posts` - Long-form content with titles
- `quips` - Short thoughts and replies
- `images` - Image content

### Relay Tables (NEW!)
- `relay_events` - All events received by relay
- `relay_subscriptions` - Active client subscriptions

## 🎯 What Makes This Special

1. **🔄 Unified System**: One app does everything
2. **📡 Private Relay**: Your own piece of Nostr infrastructure  
3. **🌐 Public Interface**: Beautiful web presentation
4. **⚡ Fast Fetching**: Concurrent connections, no timeouts
5. **📦 Easy Deploy**: Single script server setup
6. **💾 Persistent Storage**: SQLite database for reliability
7. **🔧 Configurable**: Customize everything via config.py

## 🌟 Use Cases

### Personal
- **Blog & Relay**: Your content + your infrastructure
- **Family Hub**: Private relay for family/friends
- **Backup**: Store your Nostr content permanently

### Community  
- **Topic Relay**: Relay for specific communities
- **Local Groups**: Regional Nostr infrastructure
- **Backup Hub**: Community content preservation

### Development
- **Testing**: Local relay for Nostr app development
- **Analytics**: Study Nostr usage patterns
- **Integration**: Custom Nostr-powered applications

## 🎉 You're Ready!

Your **Nostr Home Hub** is now a complete Nostr infrastructure that:

✅ **Fetches** your content from other relays  
✅ **Displays** it beautifully on the web  
✅ **Stores** events in your private relay  
✅ **Serves** as a Nostr relay for others  
✅ **Deploys** easily to any server  

Start it up and you'll have your own piece of the Nostr ecosystem! 🚀
