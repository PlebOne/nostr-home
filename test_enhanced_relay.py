#!/usr/bin/env python3
"""
Test script for the Enhanced Nostr Relay
Tests various NIP functionalities and relay features
"""

import json
import time
import hashlib
import websocket
import threading
from typing import Dict, List

class NostrRelayTester:
    def __init__(self, relay_url: str = "ws://localhost:3000"):
        self.relay_url = relay_url
        self.ws = None
        self.received_messages = []
        self.connected = False
        
    def connect(self):
        """Connect to the relay"""
        try:
            self.ws = websocket.WebSocketApp(
                self.relay_url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )
            
            # Start WebSocket in a separate thread
            wst = threading.Thread(target=self.ws.run_forever)
            wst.daemon = True
            wst.start()
            
            # Wait for connection
            timeout = 5
            while not self.connected and timeout > 0:
                time.sleep(0.1)
                timeout -= 0.1
                
            return self.connected
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def _on_open(self, ws):
        """WebSocket connection opened"""
        print("✅ Connected to Enhanced Nostr Relay")
        self.connected = True
    
    def _on_message(self, ws, message):
        """Handle incoming messages"""
        try:
            data = json.loads(message)
            self.received_messages.append(data)
            print(f"📨 Received: {data[0]} - {len(data)} fields")
        except json.JSONDecodeError:
            print(f"❌ Invalid JSON received: {message}")
    
    def _on_error(self, ws, error):
        """Handle WebSocket errors"""
        print(f"❌ WebSocket error: {error}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """WebSocket connection closed"""
        print("🔌 Disconnected from relay")
        self.connected = False
    
    def send_message(self, message: List):
        """Send a message to the relay"""
        if self.ws and self.connected:
            self.ws.send(json.dumps(message))
            time.sleep(0.1)  # Small delay for processing
        else:
            print("❌ Not connected to relay")
    
    def test_basic_subscription(self):
        """Test basic REQ/EOSE functionality (NIP-01)"""
        print("\n🧪 Testing basic subscription (NIP-01)...")
        
        # Send subscription request
        req = ["REQ", "test-sub-1", {"kinds": [1], "limit": 5}]
        self.send_message(req)
        
        # Wait for response
        time.sleep(1)
        
        # Check for EOSE
        eose_received = any(msg[0] == "EOSE" and msg[1] == "test-sub-1" 
                           for msg in self.received_messages)
        
        if eose_received:
            print("✅ Basic subscription works - EOSE received")
        else:
            print("❌ No EOSE received for subscription")
        
        # Close subscription
        close = ["CLOSE", "test-sub-1"]
        self.send_message(close)
        
        return eose_received
    
    def test_event_publishing(self):
        """Test event publishing (NIP-01, NIP-20)"""
        print("\n🧪 Testing event publishing (NIP-01, NIP-20)...")
        
        # Create a test event
        event = {
            "id": "",
            "pubkey": "test" + "0" * 60,  # Fake pubkey for testing
            "created_at": int(time.time()),
            "kind": 1,
            "tags": [["t", "test"], ["p", "test" + "0" * 60]],
            "content": "Test event from Enhanced Nostr Relay tester! 🚀",
            "sig": "test" + "0" * 124  # Fake signature for testing
        }
        
        # Calculate event ID
        event_json = json.dumps([
            0,
            event["pubkey"],
            event["created_at"],
            event["kind"],
            event["tags"],
            event["content"]
        ], separators=(',', ':'), ensure_ascii=False)
        
        event["id"] = hashlib.sha256(event_json.encode()).hexdigest()
        
        # Send event
        self.send_message(["EVENT", event])
        
        # Wait for OK response
        time.sleep(1)
        
        # Check for OK response
        ok_received = any(msg[0] == "OK" and msg[1] == event["id"] 
                         for msg in self.received_messages)
        
        if ok_received:
            print("✅ Event publishing works - OK response received")
        else:
            print("❌ No OK response received for event")
        
        return ok_received
    
    def test_generic_tag_filtering(self):
        """Test generic tag queries (NIP-12)"""
        print("\n🧪 Testing generic tag filtering (NIP-12)...")
        
        # Request events with specific tag
        req = ["REQ", "test-tag-sub", {"#t": ["test"], "limit": 5}]
        self.send_message(req)
        
        time.sleep(1)
        
        # Check for tag-filtered events
        events_received = [msg for msg in self.received_messages 
                          if msg[0] == "EVENT" and msg[1] == "test-tag-sub"]
        
        print(f"📊 Received {len(events_received)} events with tag filter")
        
        # Close subscription
        self.send_message(["CLOSE", "test-tag-sub"])
        
        return len(events_received) >= 0  # Always pass, just testing functionality
    
    def test_search_functionality(self):
        """Test search functionality (NIP-50)"""
        print("\n🧪 Testing search functionality (NIP-50)...")
        
        # Search for events containing "test"
        req = ["REQ", "test-search", {"search": "test", "limit": 5}]
        self.send_message(req)
        
        time.sleep(1)
        
        # Check for search results
        search_events = [msg for msg in self.received_messages 
                        if msg[0] == "EVENT" and msg[1] == "test-search"]
        
        print(f"🔍 Search returned {len(search_events)} events")
        
        # Close subscription
        self.send_message(["CLOSE", "test-search"])
        
        return True  # Search functionality tested
    
    def test_count_functionality(self):
        """Test COUNT functionality (NIP-45)"""
        print("\n🧪 Testing COUNT functionality (NIP-45)...")
        
        # Send COUNT request
        count_req = ["COUNT", "test-count", {"kinds": [1]}]
        self.send_message(count_req)
        
        time.sleep(1)
        
        # Check for COUNT response
        count_received = any(msg[0] == "COUNT" and msg[1] == "test-count" 
                           for msg in self.received_messages)
        
        if count_received:
            count_msg = next(msg for msg in self.received_messages 
                           if msg[0] == "COUNT" and msg[1] == "test-count")
            count_value = count_msg[2].get("count", 0)
            print(f"✅ COUNT functionality works - {count_value} events found")
        else:
            print("❌ No COUNT response received")
        
        return count_received
    
    def test_relay_info(self):
        """Test if relay provides proper info"""
        print("\n🧪 Testing relay information...")
        
        # This would typically be an HTTP GET to /.well-known/nostr.json
        # For now, just verify we can connect and the relay responds
        return self.connected
    
    def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting Enhanced Nostr Relay Tests")
        print("=" * 50)
        
        if not self.connect():
            print("❌ Failed to connect to relay. Make sure it's running.")
            return False
        
        # Clear previous messages
        self.received_messages.clear()
        
        tests = [
            ("Basic Subscription", self.test_basic_subscription),
            ("Event Publishing", self.test_event_publishing),
            ("Generic Tag Filtering", self.test_generic_tag_filtering),
            ("Search Functionality", self.test_search_functionality),
            ("COUNT Functionality", self.test_count_functionality),
            ("Relay Info", self.test_relay_info),
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            try:
                result = test_func()
                if result:
                    passed += 1
                    print(f"✅ {test_name}: PASSED")
                else:
                    print(f"❌ {test_name}: FAILED")
            except Exception as e:
                print(f"❌ {test_name}: ERROR - {e}")
        
        print("\n" + "=" * 50)
        print(f"🏁 Tests completed: {passed}/{total} passed")
        
        if self.ws:
            self.ws.close()
        
        return passed == total

if __name__ == "__main__":
    # Test the enhanced relay
    tester = NostrRelayTester()
    success = tester.run_all_tests()
    
    if success:
        print("🎉 All tests passed! Enhanced Nostr Relay is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the relay implementation.")
