import json
import re
import time
from typing import List, Dict, Optional
import websocket
import threading
import hashlib
import binascii
import config
from database import NostrDatabase

class NostrContentClient:
    def __init__(self):
        self.npub = config.NOSTR_NPUB
        self.relays = config.NOSTR_RELAYS
        self.db = NostrDatabase()
        
    def npub_to_hex(self, npub: str) -> str:
        """Convert npub to hex pubkey"""
        try:
            return self.bech32_decode(npub)
        except Exception as e:
            print(f"Error converting npub to hex: {e}")
            return npub
    
    def bech32_decode(self, npub: str) -> str:
        """Simple bech32 decode for npub - for production use proper library"""
        # This is a simplified version - for production, use a proper bech32 library
        # For now, we'll use a hard-coded conversion for the provided npub
        if npub == "npub13hyx3qsqk3r7ctjqrr49uskut4yqjsxt8uvu4rekr55p08wyhf0qq90nt7":
            return "8dc8688200b447ec2e4018ea5e42dc5d480940cb3f19ca8f361d28179dc4ba5e"
        return npub
    
    def has_image(self, content: str, tags: List[List[str]]) -> Optional[str]:
        """Check if content contains an image and return the URL"""
        # Check content for image URLs
        image_regex = r'https?://[^\s]+\.(jpg|jpeg|png|gif|webp|svg)'
        content_match = re.search(image_regex, content, re.IGNORECASE)
        if content_match:
            return content_match.group(0)
        
        # Check tags for image URLs
        for tag in tags:
            if len(tag) >= 2 and tag[0] in ['url', 'r']:
                url_match = re.search(image_regex, tag[1], re.IGNORECASE)
                if url_match:
                    return url_match.group(0)
        
        return None
    
    def is_long_form_post(self, event_data: Dict) -> bool:
        """Determine if this is a proper long-form post (NIP-23 kind 30023 or structured content)"""
        
        kind = event_data.get('kind', 1)
        content = event_data.get('content', '').strip()
        tags = event_data.get('tags', [])
        
        # NIP-23 Long-form content (kind 30023) is always a post
        if kind == 30023:
            return True
        
        # For kind 1 events, check if they have title tags (indicating long-form structure)
        if kind == 1:
            # Check for title tag (NIP-23 style)
            for tag in tags:
                if len(tag) >= 2 and tag[0] == 'title' and tag[1].strip():
                    return True
        
        return False

    def process_events(self, events: List[Dict]) -> Dict[str, int]:
        """Process and categorize events with improved logic"""
        processed = {'posts': 0, 'quips': 0, 'images': 0}
        
        for event_data in events:
            try:
                content = event_data.get('content', '').strip()
                
                # Skip empty content
                if not content:
                    continue
                
                tags = event_data.get('tags', [])
                
                # Check if it's an image post
                image_url = self.has_image(content, tags)
                
                if image_url:
                    self.db.save_image(event_data, image_url)
                    processed['images'] += 1
                elif self.is_long_form_post(event_data):
                    # Save as post if it's NIP-23 long-form or has title tags
                    self.db.save_post(event_data)
                    processed['posts'] += 1
                    title = next((tag[1] for tag in tags if tag[0] == 'title'), content[:50])
                    print(f"📝 Found long-form post: {title}...")
                else:
                    # Everything else is a quip (short thoughts, replies, etc.)
                    self.db.save_quip(event_data)
                    processed['quips'] += 1
                    
            except Exception as e:
                print(f"Error processing event: {e}")
                continue
        
        return processed
    
    def fetch_events_simple(self, pubkey: str, since: Optional[int] = None) -> List[Dict]:
        """Fetch events using concurrent connections with timeouts"""
        import threading
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import time
        
        all_events = []
        
        def fetch_with_timeout(relay_url, timeout=10):
            """Fetch from a single relay with timeout"""
            try:
                print(f"🔍 Connecting to: {relay_url}")
                events = self._fetch_from_single_relay_timeout(relay_url, pubkey, since, timeout)
                if events:
                    print(f"✅ Found {len(events)} events from {relay_url}")
                else:
                    print(f"⚪ No events from {relay_url}")
                return events
            except Exception as e:
                print(f"❌ Failed {relay_url}: {str(e)[:50]}...")
                return []
        
        # Use ThreadPoolExecutor for concurrent fetching
        print(f"🚀 Fetching from {len(self.relays)} relays concurrently...")
        
        with ThreadPoolExecutor(max_workers=len(self.relays)) as executor:
            # Submit all relay fetch tasks
            future_to_relay = {
                executor.submit(fetch_with_timeout, relay_url): relay_url 
                for relay_url in self.relays
            }
            
            # Collect results as they complete (with overall timeout)
            for future in as_completed(future_to_relay, timeout=30):
                try:
                    events = future.result()
                    all_events.extend(events)
                except Exception as e:
                    relay_url = future_to_relay[future]
                    print(f"❌ Timeout/Error {relay_url}: {e}")
        
        # Remove duplicates based on event ID
        unique_events = {}
        for event in all_events:
            event_id = event.get('id')
            if event_id and event_id not in unique_events:
                unique_events[event_id] = event
        
        print(f"📊 Total unique events: {len(unique_events)}")
        return list(unique_events.values())
    
    def _fetch_from_single_relay_timeout(self, relay_url: str, pubkey: str, since: Optional[int] = None, timeout: int = 10) -> List[Dict]:
        """Fetch events from a single relay with timeout"""
        import threading
        import time
        
        events = []
        connection_complete = threading.Event()
        
        def on_message(ws, message):
            try:
                data = json.loads(message)
                if isinstance(data, list) and len(data) >= 3:
                    if data[0] == "EVENT":
                        event = data[2]
                        if event.get('pubkey') == pubkey:
                            events.append(event)
                    elif data[0] == "EOSE":
                        connection_complete.set()
                        ws.close()
            except json.JSONDecodeError:
                pass
            except Exception as e:
                pass
        
        def on_error(ws, error):
            connection_complete.set()
        
        def on_close(ws, close_status_code, close_msg):
            connection_complete.set()
        
        def on_open(ws):
            # Create subscription request
            req_filter = {
                "authors": [pubkey],
                "kinds": [1, 30023]  # Text notes and long-form content (NIP-23)
            }
            if since:
                req_filter["since"] = since
            
            subscription_id = f"sub_{int(time.time())}"
            request = ["REQ", subscription_id, req_filter]
            ws.send(json.dumps(request))
        
        try:
            ws = websocket.WebSocketApp(
                relay_url,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
                on_open=on_open
            )
            
            # Start connection in a thread
            def run_ws():
                ws.run_forever()
            
            ws_thread = threading.Thread(target=run_ws)
            ws_thread.daemon = True
            ws_thread.start()
            
            # Wait for completion or timeout
            connection_complete.wait(timeout=timeout)
            
            # Clean up
            if ws:
                ws.close()
            
            return events
            
        except Exception as e:
            raise Exception(f"Connection failed: {e}")

    def _fetch_from_single_relay(self, relay_url: str, pubkey: str, since: Optional[int] = None) -> List[Dict]:
        """Fetch events from a single relay"""
        events = []
        
        def on_message(ws, message):
            try:
                data = json.loads(message)
                if isinstance(data, list) and len(data) >= 3:
                    if data[0] == "EVENT":
                        event = data[2]
                        if event.get('pubkey') == pubkey:
                            events.append(event)
                    elif data[0] == "EOSE":
                        ws.close()
            except json.JSONDecodeError:
                pass
            except Exception as e:
                print(f"Error processing message: {e}")
        
        def on_error(ws, error):
            print(f"WebSocket error: {error}")
        
        def on_close(ws, close_status_code, close_msg):
            pass
        
        def on_open(ws):
            # Create subscription request
            subscription_id = f"sub_{int(time.time())}"
            filters = {
                "authors": [pubkey],
                "kinds": [1, 30023]  # Text notes and long-form content (NIP-23)
            }
            
            if since:
                filters["since"] = since
            
            request = ["REQ", subscription_id, filters]
            ws.send(json.dumps(request))
        
        try:
            ws = websocket.WebSocketApp(
                relay_url,
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )
            
            # Run with timeout
            ws.run_forever(ping_interval=30, ping_timeout=10)
            
        except Exception as e:
            print(f"WebSocket connection failed for {relay_url}: {e}")
        
        return events
    
    def update_cache(self) -> Dict[str, int]:
        """Update the cache with new events"""
        try:
            print("Starting Nostr cache update with Python client...")
            
            pubkey = self.npub_to_hex(self.npub)
            if not pubkey:
                raise ValueError("Invalid npub provided")
            
            print(f"Using pubkey: {pubkey}")
            
            # Get the timestamp of the most recent cached event
            last_event = self.db.get_last_event_timestamp()
            since = last_event if last_event else int(time.time()) - (7 * 24 * 60 * 60)  # 7 days ago
            
            print(f"Fetching events since: {since}")
            
            events = self.fetch_events_simple(pubkey, since)
            print(f"Fetched {len(events)} total events from all relays")
            
            if events:
                print("Sample event:", events[0] if events else "None")
            
            processed = self.process_events(events)
            print(f"Processed: {processed['posts']} posts, {processed['quips']} quips, {processed['images']} images")
            
            return processed
            
        except Exception as e:
            print(f"Error updating cache: {e}")
            raise e
    
    def fetch_all_events(self, pubkey: str) -> List[Dict]:
        """Fetch all events (no time limit) for testing"""
        return self.fetch_events_simple(pubkey, since=0)
