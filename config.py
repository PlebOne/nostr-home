import os
from dotenv import load_dotenv

load_dotenv()

# Your Nostr public key (npub)
NOSTR_NPUB = os.getenv('NOSTR_NPUB', 'npub13hyx3qsqk3r7ctjqrr49uskut4yqjsxt8uvu4rekr55p08wyhf0qq90nt7')

# Nostr relays to connect to - prioritizing Damus as requested
NOSTR_RELAYS = [
    'wss://relay.damus.io',          # Priority 1 - Damus (as requested)
    'wss://relay.primal.net',        # Priority 2 - Primal (we know this works - found 15 events)
    'wss://nos.lol',                 # Priority 3 - Popular and reliable
    'wss://relay.snort.social',      # Priority 4 - Snort relay
    'wss://relay.nostr.band',        # Priority 5 - Nostr.band
    'wss://nostr.wine',              # Additional reliable relay
    'wss://purplepag.es',            # Good for long-form content
    'wss://relay.nostr.wirednet.jp', # International coverage
    'wss://nostr.orangepill.dev'     # Additional coverage
]

# Database settings
DATABASE_PATH = './data/nostr_content.db'

# Cache settings
CACHE_UPDATE_INTERVAL = 6  # hours
CACHE_DIR = './cache'

# Server settings
PORT = int(os.getenv('PORT', 3000))

# Site branding
SITE_NAME = os.getenv('SITE_NAME', 'Nostr Home')  # Customizable site name
SITE_SUBTITLE = os.getenv('SITE_SUBTITLE', 'Your Decentralized Content')  # Customizable subtitle

# Content settings
MAX_POSTS_PER_PAGE = 20
MAX_QUIPS_PER_PAGE = 50
MAX_IMAGES_PER_PAGE = 30

# Relay settings
RELAY_ENABLED = True
RELAY_NAME = "Enhanced Personal Nostr Hub"
RELAY_DESCRIPTION = "Enhanced personal Nostr relay with multi-NIP support and content aggregation"
RELAY_PUBKEY = ""  # Will be generated on first run
RELAY_CONTACT = "admin@localhost"
RELAY_MAX_EVENTS_PER_REQUEST = 500
RELAY_MAX_SUBSCRIPTIONS_PER_CLIENT = 20
RELAY_EVENT_RETENTION_DAYS = 365  # Keep events for 1 year

# Enhanced relay settings
MIN_POW_DIFFICULTY = 0  # Proof of Work difficulty (0 = disabled)
RATE_LIMIT_MESSAGES_PER_MINUTE = 100  # Rate limiting
ENABLE_AUTHENTICATION = False  # NIP-42 authentication
ENABLE_DELETION = True  # NIP-09 event deletion
ENABLE_REPLACEABLE = True  # NIP-16/33 replaceable events
ENABLE_SEARCH = True  # NIP-50 search functionality
RELAY_OWNER_ONLY = True  # Only allow events from the configured NOSTR_NPUB
                         # Set to False to allow events from any user
