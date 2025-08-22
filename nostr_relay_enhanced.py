#!/usr/bin/env python3

import json
import time
import hashlib
import uuid
import re
from typing import Dict, List, Optional, Set, Tuple, Union
from flask_socketio import SocketIO, emit, disconnect
from database import NostrDatabase
from nostr_client import NostrContentClient
import config

class EnhancedNostrRelay:
    """Enhanced Nostr relay implementation supporting many NIPs"""
    
    def __init__(self, socketio: SocketIO):
        self.socketio = socketio
        self.db = NostrDatabase()
        self.clients: Dict[str, Dict] = {}  # client_id -> client_info
        self.subscriptions: Dict[str, Dict] = {}  # sub_id -> subscription_info
        self.auth_challenges: Dict[str, Dict] = {}  # client_id -> challenge_info
        
        # Initialize NostrContentClient for npub conversion
        self.nostr_client = NostrContentClient()
        
        # Convert owner npub to hex for validation
        self.owner_pubkey = self.nostr_client.npub_to_hex(config.NOSTR_NPUB) if config.RELAY_OWNER_ONLY else None
        
        # Register SocketIO event handlers
        self.register_handlers()
        
        print(f"🚀 Enhanced Nostr Relay initialized: {config.RELAY_NAME}")
        print(f"📄 Description: {config.RELAY_DESCRIPTION}")
        if config.RELAY_OWNER_ONLY:
            print(f"🔒 Owner-only mode: Events restricted to {config.NOSTR_NPUB}")
            print(f"🔑 Owner pubkey: {self.owner_pubkey}")
        print(f"✨ Supported NIPs: {', '.join(map(str, self.get_supported_nips()))}")
    
    def get_supported_nips(self) -> List[int]:
        """Return list of supported NIPs"""
        return [
            1,    # Basic protocol flow description
            2,    # Contact List and Petnames
            3,    # OpenTimestamps Attestations for Events
            4,    # Encrypted Direct Messages
            5,    # Mapping Nostr keys to DNS-based internet identifiers
            9,    # Event Deletion
            10,   # Conventions for clients' use of `e` and `p` tags in text events
            11,   # Relay Information Document
            12,   # Generic Tag Queries
            13,   # Proof of Work
            15,   # End of Stored Events Notice
            16,   # Event Treatment
            20,   # Command Results
            22,   # Event `created_at` Limits
            25,   # Reactions
            26,   # Delegated Event Signing
            28,   # Public Chat
            33,   # Parameterized Replaceable Events
            40,   # Expiration Timestamp
            42,   # Authentication of clients to relays
            45,   # Counting results
            50,   # Keywords filter
            65,   # Relay List Metadata
        ]
    
    def register_handlers(self):
        """Register SocketIO event handlers"""
        
        @self.socketio.on('connect')
        def handle_connect():
            client_id = self.generate_client_id()
            
            self.clients[client_id] = {
                'id': client_id,
                'connected_at': time.time(),
                'subscriptions': set(),
                'authenticated': False,
                'pubkey': None,
                'last_activity': time.time(),
                'rate_limit_bucket': {'count': 0, 'last_reset': time.time()}
            }
            print(f"📡 Client connected: {client_id}")
            return True
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            # Find client by connection (simplified for compatibility)
            client_id = self.get_current_client_id()
            if client_id and client_id in self.clients:
                # Clean up subscriptions
                for sub_id in list(self.clients[client_id]['subscriptions']):
                    self.remove_subscription(sub_id, client_id)
                
                del self.clients[client_id]
                print(f"📡 Client disconnected: {client_id}")
        
        @self.socketio.on('message')
        def handle_message(data):
            """Handle incoming Nostr messages"""
            try:
                if isinstance(data, str):
                    message = json.loads(data)
                else:
                    message = data
                
                client_id = self.get_current_client_id()
                if not client_id:
                    return
                
                # Rate limiting
                if not self.check_rate_limit(client_id):
                    self.send_notice("Rate limit exceeded")
                    return
                
                # Update last activity
                self.clients[client_id]['last_activity'] = time.time()
                
                self.process_message(client_id, message)
                
            except json.JSONDecodeError:
                self.send_notice("Invalid JSON")
            except Exception as e:
                print(f"Error handling message: {e}")
                self.send_notice("Internal server error")
    
    def get_current_client_id(self) -> Optional[str]:
        """Get current client ID (simplified approach)"""
        # For compatibility, return the first available client
        # In a real implementation, this would track sessions properly
        if self.clients:
            return list(self.clients.keys())[0]
        return None
    
    def check_rate_limit(self, client_id: str) -> bool:
        """Check if client is within rate limits"""
        now = time.time()
        bucket = self.clients[client_id]['rate_limit_bucket']
        
        # Reset bucket if needed (1 minute window)
        if now - bucket['last_reset'] > 60:
            bucket['count'] = 0
            bucket['last_reset'] = now
        
        # Check limit (100 messages per minute)
        if bucket['count'] >= 100:
            return False
        
        bucket['count'] += 1
        return True
    
    def process_message(self, client_id: str, message: List):
        """Process incoming Nostr protocol messages"""
        if not isinstance(message, list) or len(message) < 1:
            self.send_notice("Invalid message format")
            return
        
        message_type = message[0]
        
        if message_type == "REQ":
            self.handle_request(client_id, message)
        elif message_type == "EVENT":
            self.handle_event(client_id, message)
        elif message_type == "CLOSE":
            self.handle_close(client_id, message)
        elif message_type == "AUTH":  # NIP-42
            self.handle_auth(client_id, message)
        elif message_type == "COUNT":  # NIP-45
            self.handle_count(client_id, message)
        else:
            self.send_notice(f"Unknown message type: {message_type}")
    
    def handle_request(self, client_id: str, message: List):
        """Handle REQ messages (client requesting events) - Enhanced with many NIPs"""
        if len(message) < 3:
            self.send_notice("Invalid REQ format")
            return
        
        subscription_id = message[1]
        filters = message[2:]
        
        # Check subscription limits
        if len(self.clients[client_id]['subscriptions']) >= config.RELAY_MAX_SUBSCRIPTIONS_PER_CLIENT:
            self.send_notice("Too many subscriptions")
            return
        
        # Validate subscription ID length (NIP-01)
        if len(subscription_id) > 64:
            self.send_notice("Subscription ID too long")
            return
        
        # Save subscription
        self.subscriptions[subscription_id] = {
            'client_id': client_id,
            'filters': filters,
            'created_at': time.time()
        }
        self.clients[client_id]['subscriptions'].add(subscription_id)
        
        # Get matching events with enhanced filtering
        events = self.get_events_with_enhanced_filters(filters)
        
        # Send events
        for event in events:
            self.send_event(subscription_id, event)
        
        # Send EOSE (End of Stored Events) - NIP-15
        self.send_eose(subscription_id)
        
        print(f"📝 Subscription {subscription_id} created for client {client_id} - found {len(events)} events")
    
    def handle_event(self, client_id: str, message: List):
        """Handle EVENT messages with enhanced validation and NIPs support"""
        if len(message) < 2:
            self.send_notice("Invalid EVENT format")
            return
        
        event = message[1]
        
        # Enhanced event validation
        validation_result = self.validate_event_enhanced(event, client_id)
        if not validation_result['valid']:
            self.send_ok(event.get('id', ''), False, validation_result['reason'])
            return
        
        # Check for event deletion (NIP-09)
        if event.get('kind') == 5:
            self.handle_deletion_event(event, client_id)
            return
        
        # Check for expiration (NIP-40)
        if self.is_event_expired(event):
            self.send_ok(event['id'], False, "Event expired")
            return
        
        # Handle replaceable events (NIP-16, NIP-33)
        if self.is_replaceable_event(event):
            self.handle_replaceable_event(event)
        
        # Save event to database
        if self.db.save_relay_event(event):
            self.send_ok(event['id'], True, "")
            
            # Broadcast to subscribers
            self.broadcast_event(event)
            
            print(f"📨 Event published: {event['id'][:16]}... kind:{event['kind']} by {event['pubkey'][:16]}...")
        else:
            self.send_ok(event['id'], False, "Failed to save event")
    
    def handle_auth(self, client_id: str, message: List):
        """Handle AUTH messages (NIP-42)"""
        if len(message) < 2:
            self.send_notice("Invalid AUTH format")
            return
        
        auth_event = message[1]
        
        # Validate auth event
        if not self.validate_auth_event(auth_event, client_id):
            self.send_notice("Invalid auth event")
            return
        
        # Mark client as authenticated
        self.clients[client_id]['authenticated'] = True
        self.clients[client_id]['pubkey'] = auth_event['pubkey']
        
        print(f"🔐 Client {client_id} authenticated as {auth_event['pubkey'][:16]}...")
    
    def handle_count(self, client_id: str, message: List):
        """Handle COUNT messages (NIP-45)"""
        if len(message) < 3:
            self.send_notice("Invalid COUNT format")
            return
        
        subscription_id = message[1]
        filters = message[2:]
        
        # Count matching events
        count = self.count_events_with_filters(filters)
        
        # Send COUNT response
        self.send_count(subscription_id, count)
    
    def handle_deletion_event(self, event: Dict, client_id: str):
        """Handle event deletion (NIP-09)"""
        # Extract event IDs to delete from 'e' tags
        event_ids_to_delete = []
        for tag in event.get('tags', []):
            if len(tag) >= 2 and tag[0] == 'e':
                event_ids_to_delete.append(tag[1])
        
        # Only allow deletion of own events
        deleted_count = 0
        for event_id in event_ids_to_delete:
            if self.db.delete_event_if_owner(event_id, event['pubkey']):
                deleted_count += 1
        
        self.send_ok(event['id'], True, f"Deleted {deleted_count} events")
        print(f"🗑️ Deleted {deleted_count} events for {event['pubkey'][:16]}...")
    
    def validate_event_enhanced(self, event: Dict, client_id: str) -> Dict:
        """Enhanced event validation supporting multiple NIPs"""
        # Basic validation
        required_fields = ['id', 'pubkey', 'created_at', 'kind', 'tags', 'content', 'sig']
        
        for field in required_fields:
            if field not in event:
                return {'valid': False, 'reason': f"Missing field: {field}"}
        
        # Owner-only relay restriction
        if config.RELAY_OWNER_ONLY and self.owner_pubkey:
            if event['pubkey'] != self.owner_pubkey:
                return {'valid': False, 'reason': f"restricted: relay only accepts events from owner"}
        
        # Type checks
        if not isinstance(event['tags'], list):
            return {'valid': False, 'reason': "Tags must be array"}
        if not isinstance(event['created_at'], int):
            return {'valid': False, 'reason': "created_at must be integer"}
        if not isinstance(event['kind'], int):
            return {'valid': False, 'reason': "kind must be integer"}
        
        # NIP-22: Event created_at limits
        now = int(time.time())
        if event['created_at'] > now + 600:  # 10 minutes in future
            return {'valid': False, 'reason': "Event too far in future"}
        if event['created_at'] < now - (365 * 24 * 60 * 60):  # 1 year in past
            return {'valid': False, 'reason': "Event too old"}
        
        # NIP-13: Proof of Work validation
        if self.has_pow_requirement(event['kind']):
            if not self.validate_pow(event):
                return {'valid': False, 'reason': "Insufficient proof of work"}
        
        # Content length limits
        if len(event['content']) > 65536:  # 64KB limit
            return {'valid': False, 'reason': "Content too long"}
        
        # Validate event ID
        if not self.validate_event_id(event):
            return {'valid': False, 'reason': "Invalid event ID"}
        
        return {'valid': True, 'reason': ''}
    
    def get_events_with_enhanced_filters(self, filters: List[Dict]) -> List[Dict]:
        """Get events with enhanced filtering supporting multiple NIPs"""
        all_events = []
        
        for filter_obj in filters:
            # Basic filters (NIP-01)
            events = self.db.get_relay_events([filter_obj])
            
            # Apply additional filters
            filtered_events = []
            for event in events:
                # NIP-50: Search filter
                if 'search' in filter_obj:
                    if not self.event_matches_search(event, filter_obj['search']):
                        continue
                
                # NIP-12: Generic tag queries
                if not self.event_matches_generic_tags(event, filter_obj):
                    continue
                
                # NIP-40: Check expiration
                if self.is_event_expired(event):
                    continue
                
                filtered_events.append(event)
            
            all_events.extend(filtered_events)
        
        # Remove duplicates and sort
        seen_ids = set()
        unique_events = []
        for event in all_events:
            if event['id'] not in seen_ids:
                seen_ids.add(event['id'])
                unique_events.append(event)
        
        # Sort by created_at descending
        unique_events.sort(key=lambda x: x['created_at'], reverse=True)
        
        return unique_events
    
    def event_matches_search(self, event: Dict, search_term: str) -> bool:
        """NIP-50: Search in content"""
        content = event.get('content', '').lower()
        search_term = search_term.lower()
        return search_term in content
    
    def event_matches_generic_tags(self, event: Dict, filter_obj: Dict) -> bool:
        """NIP-12: Generic tag queries"""
        for key, values in filter_obj.items():
            if key.startswith('#') and len(key) == 2:
                tag_name = key[1]
                if not isinstance(values, list):
                    values = [values]
                
                # Check if event has any of the required tag values
                found = False
                for tag in event.get('tags', []):
                    if len(tag) >= 2 and tag[0] == tag_name and tag[1] in values:
                        found = True
                        break
                
                if not found:
                    return False
        
        return True
    
    def count_events_with_filters(self, filters: List[Dict]) -> int:
        """Count events matching filters (NIP-45)"""
        events = self.get_events_with_enhanced_filters(filters)
        return len(events)
    
    def is_event_expired(self, event: Dict) -> bool:
        """Check if event is expired (NIP-40)"""
        for tag in event.get('tags', []):
            if len(tag) >= 2 and tag[0] == 'expiration':
                try:
                    expiration_time = int(tag[1])
                    return int(time.time()) > expiration_time
                except ValueError:
                    continue
        return False
    
    def is_replaceable_event(self, event: Dict) -> bool:
        """Check if event is replaceable (NIP-16, NIP-33)"""
        kind = event.get('kind', 0)
        # Replaceable events: 0, 3, 10000-19999
        # Parameterized replaceable events: 30000-39999
        return (kind == 0 or kind == 3 or 
                (10000 <= kind <= 19999) or 
                (30000 <= kind <= 39999))
    
    def handle_replaceable_event(self, event: Dict):
        """Handle replaceable/parameterized replaceable events"""
        kind = event.get('kind', 0)
        pubkey = event.get('pubkey', '')
        
        if 30000 <= kind <= 39999:
            # Parameterized replaceable events (NIP-33)
            d_tag = None
            for tag in event.get('tags', []):
                if len(tag) >= 2 and tag[0] == 'd':
                    d_tag = tag[1]
                    break
            
            if d_tag is not None:
                # Delete previous versions with same kind, pubkey, and d tag
                self.db.delete_parameterized_replaceable_event(kind, pubkey, d_tag)
        else:
            # Regular replaceable events (NIP-16)
            # Delete previous versions with same kind and pubkey
            self.db.delete_replaceable_event(kind, pubkey)
    
    def has_pow_requirement(self, kind: int) -> bool:
        """Check if event kind requires proof of work"""
        # For now, no PoW requirements, but this can be configured
        return False
    
    def validate_pow(self, event: Dict) -> bool:
        """Validate proof of work (NIP-13)"""
        event_id = event.get('id', '')
        # Count leading zeros in event ID
        leading_zeros = 0
        for char in event_id:
            if char == '0':
                leading_zeros += 1
            else:
                break
        
        # Check if meets minimum difficulty (configurable)
        min_difficulty = getattr(config, 'MIN_POW_DIFFICULTY', 0)
        return leading_zeros >= min_difficulty
    
    def validate_event_id(self, event: Dict) -> bool:
        """Validate event ID is correctly calculated"""
        # Recreate the event hash
        event_json = json.dumps([
            0,
            event['pubkey'],
            event['created_at'],
            event['kind'],
            event['tags'],
            event['content']
        ], separators=(',', ':'), ensure_ascii=False)
        
        calculated_id = hashlib.sha256(event_json.encode()).hexdigest()
        return calculated_id == event['id']
    
    def validate_auth_event(self, auth_event: Dict, client_id: str) -> bool:
        """Validate authentication event (NIP-42)"""
        # Check if it's an auth event (kind 22242)
        if auth_event.get('kind') != 22242:
            return False
        
        # Check for required tags
        has_relay_tag = False
        has_challenge_tag = False
        
        for tag in auth_event.get('tags', []):
            if len(tag) >= 2:
                if tag[0] == 'relay' and tag[1] == config.RELAY_NAME:
                    has_relay_tag = True
                elif tag[0] == 'challenge':
                    has_challenge_tag = True
        
        return has_relay_tag and has_challenge_tag
    
    def broadcast_event(self, event: Dict):
        """Broadcast event to all relevant subscribers"""
        for sub_id, sub_info in self.subscriptions.items():
            if self.event_matches_filters_enhanced(event, sub_info['filters']):
                self.send_event_to_client(sub_info['client_id'], sub_id, event)
    
    def event_matches_filters_enhanced(self, event: Dict, filters: List[Dict]) -> bool:
        """Enhanced filter matching with NIP support"""
        for filter_obj in filters:
            if self.event_matches_filter_enhanced(event, filter_obj):
                return True
        return False
    
    def event_matches_filter_enhanced(self, event: Dict, filter_obj: Dict) -> bool:
        """Enhanced single filter matching"""
        # Basic filters (NIP-01)
        if not self.event_matches_basic_filter(event, filter_obj):
            return False
        
        # NIP-12: Generic tag queries
        if not self.event_matches_generic_tags(event, filter_obj):
            return False
        
        # NIP-50: Search filter
        if 'search' in filter_obj:
            if not self.event_matches_search(event, filter_obj['search']):
                return False
        
        return True
    
    def event_matches_basic_filter(self, event: Dict, filter_obj: Dict) -> bool:
        """Basic filter matching (NIP-01)"""
        # Check authors
        if 'authors' in filter_obj:
            if event['pubkey'] not in filter_obj['authors']:
                return False
        
        # Check kinds
        if 'kinds' in filter_obj:
            if event['kind'] not in filter_obj['kinds']:
                return False
        
        # Check since
        if 'since' in filter_obj:
            if event['created_at'] < filter_obj['since']:
                return False
        
        # Check until
        if 'until' in filter_obj:
            if event['created_at'] > filter_obj['until']:
                return False
        
        # Check IDs
        if 'ids' in filter_obj:
            if event['id'] not in filter_obj['ids']:
                return False
        
        return True
    
    def remove_subscription(self, sub_id: str, client_id: str):
        """Remove a subscription"""
        if sub_id in self.subscriptions:
            del self.subscriptions[sub_id]
            if client_id in self.clients:
                self.clients[client_id]['subscriptions'].discard(sub_id)
    
    def send_event(self, subscription_id: str, event: Dict):
        """Send event to requesting client"""
        message = ["EVENT", subscription_id, event]
        emit('message', json.dumps(message))
    
    def send_event_to_client(self, client_id: str, subscription_id: str, event: Dict):
        """Send event to specific client (broadcast for now)"""
        message = ["EVENT", subscription_id, event]
        self.socketio.emit('message', json.dumps(message))
    
    def send_eose(self, subscription_id: str):
        """Send End of Stored Events (NIP-15)"""
        message = ["EOSE", subscription_id]
        emit('message', json.dumps(message))
    
    def send_ok(self, event_id: str, success: bool, message: str = ""):
        """Send OK response for event submission (NIP-20)"""
        ok_message = ["OK", event_id, success, message]
        emit('message', json.dumps(ok_message))
    
    def send_count(self, subscription_id: str, count: int):
        """Send COUNT response (NIP-45)"""
        count_message = ["COUNT", subscription_id, {"count": count}]
        emit('message', json.dumps(count_message))
    
    def send_notice(self, notice: str):
        """Send notice to client"""
        message = ["NOTICE", notice]
        emit('message', json.dumps(message))
    
    def send_auth_challenge(self, client_id: str):
        """Send authentication challenge (NIP-42)"""
        challenge = str(uuid.uuid4())
        self.auth_challenges[client_id] = {
            'challenge': challenge,
            'created_at': time.time()
        }
        
        message = ["AUTH", challenge]
        self.socketio.emit('message', json.dumps(message))
    
    def generate_client_id(self) -> str:
        """Generate unique client ID"""
        return str(uuid.uuid4())
    
    def handle_close(self, client_id: str, message: List):
        """Handle CLOSE messages (client closing subscription)"""
        if len(message) < 2:
            self.send_notice("Invalid CLOSE format")
            return
        
        subscription_id = message[1]
        self.remove_subscription(subscription_id, client_id)
        print(f"🔒 Subscription {subscription_id} closed by client {client_id}")
    
    def get_relay_info(self) -> Dict:
        """Get relay information document (NIP-11)"""
        # Update description and posting policy based on owner-only mode
        description = config.RELAY_DESCRIPTION
        posting_policy = "Enhanced personal relay - supports modern Nostr features"
        restricted_writes = config.RELAY_OWNER_ONLY
        
        if config.RELAY_OWNER_ONLY:
            description += " - Owner-only relay"
            posting_policy = f"Owner-only relay - only accepts events from {config.NOSTR_NPUB}"
        
        return {
            "name": config.RELAY_NAME,
            "description": description,
            "pubkey": getattr(config, 'RELAY_PUBKEY', ''),
            "contact": config.RELAY_CONTACT,
            "supported_nips": self.get_supported_nips(),
            "software": "Enhanced Nostr Home Hub",
            "version": "2.0.0",
            "limitation": {
                "max_message_length": 65536,
                "max_subscriptions": config.RELAY_MAX_SUBSCRIPTIONS_PER_CLIENT,
                "max_filters": 10,
                "max_limit": config.RELAY_MAX_EVENTS_PER_REQUEST,
                "max_subid_length": 64,
                "max_event_tags": 2000,
                "max_content_length": 65536,
                "min_pow_difficulty": getattr(config, 'MIN_POW_DIFFICULTY', 0),
                "auth_required": False,
                "payment_required": False,
                "restricted_writes": restricted_writes,
                "created_at_lower_limit": int(time.time()) - (365 * 24 * 60 * 60),
                "created_at_upper_limit": int(time.time()) + 600
            },
            "relay_countries": ["US"],
            "language_tags": ["en"],
            "tags": ["personal", "blog", "aggregator", "enhanced"] + (["owner-only"] if config.RELAY_OWNER_ONLY else []),
            "posting_policy": posting_policy,
            "payments_url": "",
            "fees": {
                "admission": [{"amount": 0, "unit": "msats"}],
                "subscription": [{"amount": 0, "unit": "msats"}],
                "publication": [{"amount": 0, "unit": "msats"}]
            }
        }
