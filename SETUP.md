# Quick Setup Guide

## Get Started in 3 Steps

### 1. Update Your Nostr npub
Edit `config.py` and replace the placeholder with your actual npub:
```python
NOSTR_NPUB = 'npub1your_actual_npub_here'
```

### 2. Install Dependencies and Start Server
```bash
# Install Python dependencies
pip3 install -r requirements.txt

# Start the server
python3 app.py
```
Or use the convenience script:
```bash
./start.sh
```

### 3. Visit Your Site
- Web Interface: http://localhost:3000
- Nostr Relay: ws://localhost:3000/socket.io/

## What You Get

- **Homepage**: Overview with stats and preview content
- **Posts**: Long-form content (>200 characters)
- **Quips**: Short thoughts (≤200 characters)  
- **Gallery**: Image content with automatic detection
- **Nostr Relay**: Full relay server accepting events from any client
- **Automatic Caching**: Updates every 6 hours
- **Manual Updates**: API endpoint for immediate cache refresh
- **WebSocket Support**: Real-time relay functionality

## 🔧 Quick Commands

## Commands

```bash
# Start server
python3 app.py

# Run tests
python3 test_python_nostr.py
python3 test_relay.py

# Manual cache update
curl -X POST http://localhost:3000/api/update-cache

# Check stats
curl http://localhost:3000/api/stats

# Clear database
python3 clear_data.py
```

## API Endpoints

- `GET /api/posts` - Long-form posts
- `GET /api/quips` - Short quips
- `GET /api/images` - Image gallery
- `GET /api/stats` - Content statistics
- `POST /api/update-cache` - Force cache update
- `GET /api/relay/info` - Relay information (NIP-11)
- `GET /api/relay/stats` - Relay statistics

## Project Structure

```
nostr-blogster/
├── config.py              # Your npub and settings
├── app.py                 # Main Flask application
├── database.py            # SQLite operations
├── nostr_client.py        # Nostr content aggregation
├── nostr_relay.py         # Nostr relay server
├── requirements.txt       # Python dependencies
├── public/                # Frontend files
│   ├── index.html         # Homepage
│   ├── posts.html         # Posts page
│   ├── quips.html         # Quips page
│   ├── gallery.html       # Gallery page
│   └── styles.css         # Styling
└── data/                  # SQLite database (auto-created)
```

## Next Steps

1. **Customize**: Edit `config.py` for relays, intervals, etc.
2. **Deploy**: Use the deploy.sh script for production
3. **Monitor**: Check relay stats and content updates
3. **Extend**: Add features like search, tags, or themes
4. **Share**: Your content is now beautifully displayed!

---

**Need help?** Check the full README.md for detailed documentation.
