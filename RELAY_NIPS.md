# Enhanced Nostr Relay - Supported NIPs

This enhanced Nostr relay implementation supports a comprehensive set of Nostr Implementation Possibilities (NIPs) to provide a modern, feature-rich relay experience.

## Supported NIPs

### Core Protocol (NIP-1)
- ✅ **NIP-01**: Basic protocol flow description
  - REQ/EVENT/CLOSE message handling
  - Subscription management
  - Event broadcasting

### Event Types & Tags (NIP-2, NIP-10)
- ✅ **NIP-02**: Contact List and Petnames
  - Support for kind 3 events (contact lists)
- ✅ **NIP-10**: Conventions for clients' use of `e` and `p` tags in text events
  - Proper handling of event and pubkey tags

### Security & Verification (NIP-3, NIP-13, NIP-22)
- ✅ **NIP-03**: OpenTimestamps Attestations for Events
  - Timestamp validation support
- ✅ **NIP-13**: Proof of Work
  - Configurable PoW validation
  - Leading zero counting in event IDs
- ✅ **NIP-22**: Event `created_at` Limits
  - Rejects events too far in future (>10 minutes)
  - Rejects events too old (>1 year)

### Privacy & Encryption (NIP-4)
- ✅ **NIP-04**: Encrypted Direct Messages
  - Support for kind 4 events
  - Encrypted message handling

### Identity & DNS (NIP-5)
- ✅ **NIP-05**: Mapping Nostr keys to DNS-based internet identifiers
  - DNS-based identity verification support

### Event Management (NIP-9, NIP-16, NIP-33)
- ✅ **NIP-09**: Event Deletion
  - Allow users to delete their own events
  - Kind 5 deletion event handling
- ✅ **NIP-16**: Event Treatment (Replaceable Events)
  - Kind 0, 3, and 10000-19999 replaceable events
  - Automatic replacement of older versions
- ✅ **NIP-33**: Parameterized Replaceable Events
  - Kind 30000-39999 parameterized events
  - D-tag based replacement logic

### Relay Information (NIP-11)
- ✅ **NIP-11**: Relay Information Document
  - Comprehensive relay metadata
  - Supported NIPs advertisement
  - Rate limits and capabilities

### Advanced Filtering (NIP-12, NIP-50)
- ✅ **NIP-12**: Generic Tag Queries
  - `#<tag_name>` filter support
  - Multi-value tag filtering
- ✅ **NIP-50**: Keywords filter
  - Content search functionality
  - Case-insensitive search

### Protocol Enhancements (NIP-15, NIP-20)
- ✅ **NIP-15**: End of Stored Events Notice
  - EOSE message after subscription results
- ✅ **NIP-20**: Command Results
  - OK responses for event submissions
  - Error reporting with reasons

### Social Features (NIP-25, NIP-28)
- ✅ **NIP-25**: Reactions
  - Support for kind 7 reaction events
  - Like/dislike functionality
- ✅ **NIP-28**: Public Chat
  - Kind 42 channel message support
  - Public chat room functionality

### Advanced Protocol (NIP-26, NIP-40, NIP-42, NIP-45)
- ✅ **NIP-26**: Delegated Event Signing
  - Delegation tag support
  - Signature verification delegation
- ✅ **NIP-40**: Expiration Timestamp
  - Event expiration handling
  - Automatic cleanup of expired events
- ✅ **NIP-42**: Authentication of clients to relays
  - AUTH message handling
  - Challenge-response authentication
  - Optional client authentication
- ✅ **NIP-45**: Counting results
  - COUNT message support
  - Event count queries

### Metadata (NIP-65)
- ✅ **NIP-65**: Relay List Metadata
  - Kind 10002 relay list support
  - Relay recommendation handling

## Configuration Options

The enhanced relay supports extensive configuration through `config.py`:

### Basic Relay Settings
```python
RELAY_ENABLED = True
RELAY_NAME = "Enhanced Personal Nostr Hub"
RELAY_DESCRIPTION = "Enhanced personal Nostr relay with multi-NIP support"
RELAY_MAX_EVENTS_PER_REQUEST = 500
RELAY_MAX_SUBSCRIPTIONS_PER_CLIENT = 20
```

### Security Settings
```python
MIN_POW_DIFFICULTY = 0  # Proof of Work difficulty (0 = disabled)
RATE_LIMIT_MESSAGES_PER_MINUTE = 100  # Rate limiting
ENABLE_AUTHENTICATION = False  # NIP-42 authentication
```

### Feature Toggles
```python
ENABLE_DELETION = True  # NIP-09 event deletion
ENABLE_REPLACEABLE = True  # NIP-16/33 replaceable events
ENABLE_SEARCH = True  # NIP-50 search functionality
```

## Event Types Supported

| Kind | Description | NIP |
|------|-------------|-----|
| 0 | Metadata (replaceable) | NIP-01, NIP-16 |
| 1 | Text Note | NIP-01 |
| 2 | Recommend Relay | NIP-01 |
| 3 | Contacts (replaceable) | NIP-02, NIP-16 |
| 4 | Encrypted Direct Messages | NIP-04 |
| 5 | Event Deletion | NIP-09 |
| 7 | Reaction | NIP-25 |
| 42 | Channel Message | NIP-28 |
| 10000-19999 | Replaceable Events | NIP-16 |
| 22242 | Client Authentication | NIP-42 |
| 30000-39999 | Parameterized Replaceable Events | NIP-33 |

## Enhanced Features

### Rate Limiting
- Configurable per-client rate limiting
- Default: 100 messages per minute
- Automatic bucket reset

### Event Validation
- Comprehensive event structure validation
- Timestamp limits (NIP-22)
- Content length limits (64KB)
- Event ID verification
- Optional Proof of Work validation

### Advanced Filtering
- Search within event content (NIP-50)
- Generic tag queries (NIP-12)
- Expiration filtering (NIP-40)
- Multi-filter support

### Subscription Management
- Per-client subscription limits
- Subscription ID validation
- Automatic cleanup on disconnect

### Error Handling
- Detailed error messages
- Graceful degradation
- Client notification system

## WebSocket API

The relay uses WebSocket connections and follows the standard Nostr protocol:

### Client -> Relay
```json
["REQ", <subscription_id>, <filters...>]
["EVENT", <event>]
["CLOSE", <subscription_id>]
["AUTH", <event>]
["COUNT", <subscription_id>, <filters...>]
```

### Relay -> Client
```json
["EVENT", <subscription_id>, <event>]
["EOSE", <subscription_id>]
["OK", <event_id>, <true|false>, <message>]
["NOTICE", <message>]
["AUTH", <challenge>]
["COUNT", <subscription_id>, {"count": <number>}]
```

## Database Schema

The enhanced relay uses SQLite with optimized indexes:

```sql
-- Enhanced relay events table
CREATE TABLE relay_events (
    id TEXT PRIMARY KEY,
    pubkey TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    tags TEXT,
    kind INTEGER NOT NULL,
    sig TEXT NOT NULL,
    received_at INTEGER DEFAULT (strftime('%s', 'now'))
);

-- Optimized indexes
CREATE INDEX idx_relay_events_pubkey ON relay_events(pubkey);
CREATE INDEX idx_relay_events_kind ON relay_events(kind);
CREATE INDEX idx_relay_events_created_at ON relay_events(created_at DESC);
```

## Performance Features

- **Efficient Filtering**: Optimized database queries with proper indexing
- **Event Deduplication**: Automatic duplicate event prevention
- **Memory Management**: Efficient subscription and client tracking
- **Rate Limiting**: Prevents abuse and ensures fair usage

## Future NIP Support

The relay architecture is designed to easily support additional NIPs:

- NIP-06: Basic key derivation from mnemonic seed phrase
- NIP-07: Browser extension for signing events
- NIP-08: Handling mentions
- NIP-14: Subject tag in text events
- NIP-18: Reposts
- NIP-19: bech32-encoded entities
- NIP-23: Long-form content
- NIP-30: Custom emoji
- NIP-36: Sensitive content

## Installation & Usage

1. Ensure the enhanced relay is enabled in `config.py`:
```python
RELAY_ENABLED = True
```

2. Start the application:
```bash
python app.py
```

3. The relay will be available on the WebSocket endpoint of your Flask application.

4. Connect clients to: `ws://localhost:3000` (or your configured port)

## Monitoring & Statistics

The relay provides comprehensive statistics through the `/api/relay-info` endpoint:

- Total events stored
- Unique authors
- Active subscriptions
- Supported NIPs list
- Rate limits and capabilities

This enhanced relay provides a robust, feature-complete Nostr relay implementation suitable for personal use or small communities, with extensive NIP support for modern Nostr applications.
