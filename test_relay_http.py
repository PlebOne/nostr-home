#!/usr/bin/env python3
"""Simple test of the Enhanced Nostr Relay functionality"""

import requests
import json
import time

def test_relay_endpoints():
    """Test the relay HTTP endpoints"""
    base_url = "http://localhost:3000"
    
    print("🧪 Testing Enhanced Nostr Relay HTTP Endpoints")
    print("=" * 50)
    
    # Test relay info endpoint
    try:
        response = requests.get(f"{base_url}/api/relay/info", timeout=5)
        if response.status_code == 200:
            info = response.json()
            print("✅ Relay Info Endpoint Working!")
            print(f"   Name: {info.get('name', 'Unknown')}")
            print(f"   Version: {info.get('version', 'Unknown')}")
            print(f"   Supported NIPs: {len(info.get('supported_nips', []))}")
            print(f"   NIPs: {', '.join(map(str, info.get('supported_nips', [])))}")
            
            # Show limitations
            limitations = info.get('limitation', {})
            print(f"   Max Subscriptions: {limitations.get('max_subscriptions', 'Unknown')}")
            print(f"   Max Message Length: {limitations.get('max_message_length', 'Unknown')}")
            print(f"   Auth Required: {limitations.get('auth_required', 'Unknown')}")
            
        else:
            print(f"❌ Relay Info Endpoint Failed: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to relay: {e}")
        return False
    
    # Test relay stats endpoint  
    try:
        response = requests.get(f"{base_url}/api/relay/stats", timeout=5)
        if response.status_code == 200:
            stats = response.json()
            print("✅ Relay Stats Endpoint Working!")
            print(f"   Total Events: {stats.get('total_events', 0)}")
            print(f"   Unique Authors: {stats.get('unique_authors', 0)}")
            print(f"   Active Subscriptions: {stats.get('active_subscriptions', 0)}")
        else:
            print(f"❌ Relay Stats Endpoint Failed: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to relay stats: {e}")
    
    # Test basic posts endpoint to verify server is working
    try:
        response = requests.get(f"{base_url}/api/posts?page=1", timeout=5)
        if response.status_code == 200:
            posts = response.json()
            print("✅ Main API Working!")
            print(f"   Posts returned: {len(posts.get('posts', []))}")
        else:
            print(f"❌ Posts API Failed: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to posts API: {e}")
    
    print("\n🏁 Test completed!")
    return True

if __name__ == "__main__":
    test_relay_endpoints()
