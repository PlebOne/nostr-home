#!/usr/bin/env python3

"""
Test script to verify owner-only relay restriction
"""

import json
import time
import websocket
import config
from nostr_client import NostrContentClient

def test_owner_only_relay():
    """Test that relay only accepts events from the configured owner"""
    
    print("🧪 Testing Owner-Only Relay Restriction")
    print("=" * 50)
    
    # Get owner pubkey
    client = NostrContentClient()
    owner_pubkey = client.npub_to_hex(config.NOSTR_NPUB)
    print(f"👤 Owner npub: {config.NOSTR_NPUB}")
    print(f"🔑 Owner pubkey: {owner_pubkey}")
    print()
    
    # Connect to relay
    ws_url = "ws://localhost:3000/ws"
    print(f"🔗 Connecting to relay: {ws_url}")
    
    try:
        ws = websocket.create_connection(ws_url)
        print("✅ Connected to relay")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return
    
    # Test 1: Try to send event from owner pubkey (should succeed)
    print("\n🧪 Test 1: Event from owner pubkey")
    owner_event = {
        "id": "test_owner_event_123",
        "pubkey": owner_pubkey,
        "created_at": int(time.time()),
        "kind": 1,
        "tags": [],
        "content": "Test event from owner - should be accepted",
        "sig": "fake_signature_for_testing"
    }
    
    event_message = ["EVENT", owner_event]
    ws.send(json.dumps(event_message))
    
    try:
        response = ws.recv()
        response_data = json.loads(response)
        print(f"📨 Response: {response_data}")
        if response_data[0] == "OK" and response_data[2] == True:
            print("✅ Owner event accepted (expected)")
        else:
            print(f"⚠️ Owner event rejected: {response_data[3] if len(response_data) > 3 else 'Unknown reason'}")
    except Exception as e:
        print(f"❌ Error receiving response: {e}")
    
    # Test 2: Try to send event from different pubkey (should fail)
    print("\n🧪 Test 2: Event from non-owner pubkey")
    fake_pubkey = "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
    non_owner_event = {
        "id": "test_nonowner_event_456",
        "pubkey": fake_pubkey,
        "created_at": int(time.time()),
        "kind": 1,
        "tags": [],
        "content": "Test event from non-owner - should be rejected",
        "sig": "fake_signature_for_testing"
    }
    
    event_message = ["EVENT", non_owner_event]
    ws.send(json.dumps(event_message))
    
    try:
        response = ws.recv()
        response_data = json.loads(response)
        print(f"📨 Response: {response_data}")
        if response_data[0] == "OK" and response_data[2] == False:
            print("✅ Non-owner event rejected (expected)")
            if len(response_data) > 3:
                print(f"🔒 Rejection reason: {response_data[3]}")
        else:
            print(f"⚠️ Non-owner event unexpectedly accepted!")
    except Exception as e:
        print(f"❌ Error receiving response: {e}")
    
    # Close connection
    ws.close()
    print("\n🔌 Connection closed")
    print("\n✅ Owner-only relay test completed!")

if __name__ == "__main__":
    test_owner_only_relay()
