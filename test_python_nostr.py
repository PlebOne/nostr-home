#!/usr/bin/env python3

from nostr_client import NostrContentClient
import config

def test_nostr_fetch():
    """Test fetching Nostr content with Python client"""
    client = NostrContentClient()
    
    try:
        print("🔍 Testing Python Nostr client...")
        print(f"📊 Using npub: {config.NOSTR_NPUB}")
        print(f"🌐 Testing {len(config.NOSTR_RELAYS)} relays")
        
        pubkey = client.npub_to_hex(config.NOSTR_NPUB)
        print(f"🔑 Converted to pubkey: {pubkey}")
        
        print("\n📡 Fetching ALL events (no time limit)...")
        events = client.fetch_all_events(pubkey)
        
        print(f"✅ Fetched {len(events)} total events")
        
        if events:
            print("\n📝 Sample events:")
            for i, event in enumerate(events[:3]):
                print(f"\nEvent {i+1}:")
                print(f"  ID: {event.get('id', 'N/A')}")
                print(f"  Content: {event.get('content', '')[:100]}...")
                print(f"  Created: {event.get('created_at', 'N/A')}")
                print(f"  Tags: {len(event.get('tags', []))} tags")
            
            print(f"\n🔄 Processing events...")
            processed = client.process_events(events)
            print(f"📊 Processed: {processed['posts']} posts, {processed['quips']} quips, {processed['images']} images")
            
        else:
            print("\n⚠️  No events found. This could mean:")
            print("   1. Your npub has no content on these relays")
            print("   2. The relays are not responding")
            print("   3. Network connectivity issues")
            print("   4. Try different relays")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_nostr_fetch()
