#!/usr/bin/env python3

import json
import time
import hashlib
import uuid
from typing import Dict, List, Optional, Set
from flask_socketio import SocketIO, emit, disconnect
from database import NostrDatabase
import config

class NostrRelay:
    """Nostr relay implementation for Flask-SocketIO"""
    
    def __init__(self, socketio: SocketIO):
        self.socketio = socketio
        self.db = NostrDatabase()
        self.clients: Dict[str, Dict] = {}  # client_id -> client_info
        self.subscriptions: Dict[str, Dict] = {}  # sub_id -> subscription_info
        
        # Register SocketIO event handlers
        self.register_handlers()
        
        print(f"🚀 Nostr Relay initialized: {config.RELAY_NAME}")
        print(f"📄 Description: {config.RELAY_DESCRIPTION}")
    
    def register_handlers(self):
        """Register SocketIO event handlers"""
        
        @self.socketio.on('connect')
        def handle_connect():
            client_id = self.generate_client_id()
            self.clients[client_id] = {
                'id': client_id,
                'connected_at': time.time(),
                'subscriptions': set()
            }
            print(f"📡 Client connected: {client_id}")
            return True
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            client_id = self.get_client_id()
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
                
                client_id = self.get_client_id()
                if not client_id:
                    return
                
                self.process_message(client_id, message)
                
            except json.JSONDecodeError:
                self.send_notice("Invalid JSON")
            except Exception as e:
                print(f"Error handling message: {e}")
                self.send_notice("Internal server error")
    
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
        else:
            self.send_notice(f"Unknown message type: {message_type}")
    
    def handle_request(self, client_id: str, message: List):
        """Handle REQ messages (client requesting events)"""
        if len(message) < 3:
            self.send_notice("Invalid REQ format")
            return
        
        subscription_id = message[1]
        filters = message[2:]
        
        # Check subscription limits
        if len(self.clients[client_id]['subscriptions']) >= config.RELAY_MAX_SUBSCRIPTIONS_PER_CLIENT:
            self.send_notice("Too many subscriptions")
            return
        
        # Save subscription
        self.subscriptions[subscription_id] = {
            'client_id': client_id,
            'filters': filters,
            'created_at': time.time()
        }
        self.clients[client_id]['subscriptions'].add(subscription_id)
        self.db.save_subscription(subscription_id, client_id, filters)
        
        # Send matching events
        events = self.db.get_relay_events(filters)
        for event in events:
            self.send_event(subscription_id, event)
        
        # Send EOSE (End of Stored Events)
        self.send_eose(subscription_id)
        
        print(f"📝 Subscription {subscription_id} created for client {client_id} - found {len(events)} events")
    
    def handle_event(self, client_id: str, message: List):
        """Handle EVENT messages (client publishing events)"""
        if len(message) < 2:
            self.send_notice("Invalid EVENT format")
            return
        
        event = message[1]
        
        # Validate event
        if not self.validate_event(event):
            self.send_ok(event.get('id', ''), False, "Invalid event")
            return
        
        # Save event to database
        if self.db.save_relay_event(event):
            self.send_ok(event['id'], True, "Event saved")
            
            # Broadcast to subscribers
            self.broadcast_event(event)
            
            print(f"📨 Event published: {event['id'][:16]}... by {event['pubkey'][:16]}...")
        else:
            self.send_ok(event['id'], False, "Failed to save event")
    
    def handle_close(self, client_id: str, message: List):
        """Handle CLOSE messages (client closing subscription)"""
        if len(message) < 2:
            self.send_notice("Invalid CLOSE format")
            return
        
        subscription_id = message[1]
        self.remove_subscription(subscription_id, client_id)
        print(f"🔒 Subscription {subscription_id} closed by client {client_id}")
    
    def validate_event(self, event: Dict) -> bool:
        """Validate a Nostr event"""
        required_fields = ['id', 'pubkey', 'created_at', 'kind', 'tags', 'content', 'sig']
        
        for field in required_fields:
            if field not in event:
                return False
        
        # Basic type checks
        if not isinstance(event['tags'], list):
            return False
        if not isinstance(event['created_at'], int):
            return False
        if not isinstance(event['kind'], int):
            return False
        
        # TODO: Add cryptographic signature verification
        # For now, we'll accept events without full verification
        
        return True
    
    def broadcast_event(self, event: Dict):
        """Broadcast event to all relevant subscribers"""
        for sub_id, sub_info in self.subscriptions.items():
            if self.event_matches_filters(event, sub_info['filters']):
                self.send_event_to_client(sub_info['client_id'], sub_id, event)
    
    def event_matches_filters(self, event: Dict, filters: List[Dict]) -> bool:
        """Check if event matches any of the subscription filters"""
        for filter_obj in filters:
            if self.event_matches_filter(event, filter_obj):
                return True
        return False
    
    def event_matches_filter(self, event: Dict, filter_obj: Dict) -> bool:
        """Check if event matches a single filter"""
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
            self.db.remove_subscription(sub_id, client_id)
    
    def send_event(self, subscription_id: str, event: Dict):
        """Send event to requesting client"""
        message = ["EVENT", subscription_id, event]
        emit('message', json.dumps(message))
    
    def send_event_to_client(self, client_id: str, subscription_id: str, event: Dict):
        """Send event to specific client"""
        message = ["EVENT", subscription_id, event]
        # Note: In a real implementation, you'd need to track room/session IDs
        # For now, we'll broadcast to all
        self.socketio.emit('message', json.dumps(message))
    
    def send_eose(self, subscription_id: str):
        """Send End of Stored Events"""
        message = ["EOSE", subscription_id]
        emit('message', json.dumps(message))
    
    def send_ok(self, event_id: str, success: bool, message: str = ""):
        """Send OK response for event submission"""
        ok_message = ["OK", event_id, success, message]
        emit('message', json.dumps(ok_message))
    
    def send_notice(self, notice: str):
        """Send notice to client"""
        message = ["NOTICE", notice]
        emit('message', json.dumps(message))
    
    def generate_client_id(self) -> str:
        """Generate unique client ID"""
        return str(uuid.uuid4())
    
    def get_client_id(self) -> Optional[str]:
        """Get client ID for current session"""
        # This would need proper session tracking in a real implementation
        # For now, return a placeholder
        return "temp_client"
    
    def get_relay_info(self) -> Dict:
        """Get relay information document (NIP-11)"""
        return {
            "name": config.RELAY_NAME,
            "description": config.RELAY_DESCRIPTION,
            "pubkey": config.RELAY_PUBKEY,
            "contact": config.RELAY_CONTACT,
            "supported_nips": [1, 11, 15, 20],
            "software": "Nostr Blogster Hub",
            "version": "1.0.0",
            "limitation": {
                "max_message_length": 65536,
                "max_subscriptions": config.RELAY_MAX_SUBSCRIPTIONS_PER_CLIENT,
                "max_filters": 10,
                "max_limit": config.RELAY_MAX_EVENTS_PER_REQUEST,
                "max_subid_length": 100,
                "min_pow_difficulty": 0,
                "auth_required": False,
                "payment_required": False
            },
            "relay_countries": ["US"],
            "language_tags": ["en"],
            "tags": ["personal", "blog", "aggregator"],
            "posting_policy": "Personal relay - accepts events from any user"
        }
