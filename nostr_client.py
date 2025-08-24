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
from concurrent.futures import ThreadPoolExecutor, as_completed

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
            return None
    
    def bech32_decode(self, bech_str: str) -> str:
        """Decode a bech32 string to hex"""
        charset = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
        
        if not bech_str.startswith('npub'):
            raise ValueError("Invalid npub format")
        
        # Remove the prefix
        data = bech_str[4:]
        
        # Convert from bech32 to 5-bit groups
        values = []
        for char in data:
            if char not in charset:
                continue
            values.append(charset.index(char))
        
        # Convert 5-bit groups to 8-bit bytes
        bits = 0
        value = 0
        bytes_arr = []
        
        for v in values:
            value = (value << 5) | v
            bits += 5
            
            while bits >= 8:
                bits -= 8
                bytes_arr.append((value >> bits) & 0xff)
        
        # Remove checksum (last 6 bytes)
        bytes_arr = bytes_arr[:-6]
        
        # Convert to hex
        return ''.join(format(b, '02x') for b in bytes_arr)
    
    def create_filter(self, pubkey: str, since: Optional[int] = None) -> Dict:
        """Create a filter for querying events"""
        filter_obj = {
            "authors": [pubkey],
            "kinds": [1, 30023, 0, 3]  # Regular notes, long-form, profiles, contacts
        }
        
        if since:
            filter_obj["since"] = since
            
        return filter_obj
    
    def create_subscription(self, filter_obj: Dict) -> tuple:
        """Create a subscription message"""
        sub_id = hashlib.sha256(str(time.time()).encode()).hexdigest()[:16]
        message = json.dumps(["REQ", sub_id, filter_obj])
        return sub_id, message
    
    def extract_image_urls(self, content: str) -> List[str]:
        """Extract image URLs from note content"""
        image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp')
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+\.(?:jpg|jpeg|png|gif|webp|svg|bmp)'
        
        urls = re.findall(url_pattern, content, re.IGNORECASE)
        return list(set(urls))  # Remove duplicates
    
    def is_first_run(self) -> bool:
        """Check if this is the first run (empty database)"""
        try:
            # Check using the existing database method
            last_timestamp = self.db.get_last_event_timestamp()
            
            # If no timestamp found, it's likely first run
            is_first = last_timestamp is None
            
            if is_first:
                print("🆕 First run detected - will perform deep historical fetch")
            else:
                print(f"📊 Found existing events (last: {time.strftime('%Y-%m-%d', time.localtime(last_timestamp))}) - will fetch only recent updates")
                
            return is_first
            
        except Exception as e:
            print(f"Error checking first run status: {e}")
            return True  # Assume first run on error
    
    def is_long_form_post(self, event: Dict) -> bool:
        """Check if event is a long-form post (NIP-23 or has title tag)"""
        # NIP-23 long-form content
        if event.get('kind') == 30023:
            return True
        
        # Check for title tag in regular notes
        tags = event.get('tags', [])
        has_title = any(tag[0] == 'title' for tag in tags if tag)
        
        # Check for markdown-like content or significant length
        content = event.get('content', '')
        has_markdown = bool(re.search(r'^#{1,6}\s+.+|^[-*+]\s+.+|\[.+\]\(.+\)', content, re.MULTILINE))
        is_long = len(content) > 800  # Arbitrary threshold for "long" content
        
        return has_title or (has_markdown and is_long)
    
    def fetch_events_simple(self, pubkey: str, since: Optional[int] = None) -> List[Dict]:
        """Fetch events using concurrent connections with timeouts"""
        all_events = []
        unique_events = {}
        
        # Calculate and display time range for better logging
        if since:
            time_range = int(time.time()) - since
            days = time_range / (24 * 60 * 60)
            
            if days > 7:
                print(f"📚 Deep fetch: Getting {days:.1f} days of history...")
            else:
                print(f"🔄 Incremental fetch: Getting updates from last {days:.1f} days")
        
        print(f"🚀 Fetching from {len(self.relays)} relays concurrently...")
        
        def fetch_with_timeout(relay_url, timeout=15):
            try:
                print(f"🔍 Connecting to: {relay_url}")
                events = self._fetch_from_single_relay_timeout(relay_url, pubkey, since, timeout)
                return relay_url, events
            except Exception as e:
                print(f"❌ Error with {relay_url}: {e}")
                return relay_url, []
        
        # Use ThreadPoolExecutor for concurrent fetching
        with ThreadPoolExecutor(max_workers=len(self.relays)) as executor:
            # Submit all relay fetch tasks
            future_to_relay = {
                executor.submit(fetch_with_timeout, relay_url): relay_url 
                for relay_url in self.relays
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_relay):
                relay_url = future_to_relay[future]
                try:
                    relay_url, events = future.result()
                    if events:
                        print(f"✅ Found {len(events)} events from {relay_url}")
                        for event in events:
                            event_id = event.get('id')
                            if event_id and event_id not in unique_events:
                                unique_events[event_id] = event
                    else:
                        print(f"⚪ No events from {relay_url}")
                except Exception as e:
                    print(f"❌ Failed to fetch from {relay_url}: {e}")
        
        all_events = list(unique_events.values())
        print(f"📊 Total unique events: {len(all_events)}")
        return all_events
    
    def _fetch_from_single_relay_timeout(self, relay_url: str, pubkey: str, since: Optional[int] = None, timeout: int = 10) -> List[Dict]:
        """Fetch from a single relay with timeout"""
        events = []
        ws = None
        event_queue = []
        connection_complete = threading.Event()
        
        def on_message(ws, message):
            try:
                data = json.loads(message)
                if data[0] == "EVENT":
                    event_queue.append(data[2])
                elif data[0] == "EOSE":
                    connection_complete.set()
            except:
                pass
        
        def on_error(ws, error):
            connection_complete.set()
        
        def on_open(ws):
            filter_obj = self.create_filter(pubkey, since)
            sub_id, sub_message = self.create_subscription(filter_obj)
            ws.send(sub_message)
        
        def on_close(ws, close_status_code, close_msg):
            connection_complete.set()
        
        try:
            ws = websocket.WebSocketApp(
                relay_url,
                on_message=on_message,
                on_error=on_error,
                on_open=on_open,
                on_close=on_close
            )
            
            # Run WebSocket in a separate thread
            ws_thread = threading.Thread(target=ws.run_forever, kwargs={'ping_interval': 20, 'ping_timeout': 5})
            ws_thread.daemon = True
            ws_thread.start()
            
            # Wait for completion or timeout (increased from 10 to 15 seconds)
            if connection_complete.wait(timeout):
                # Return all collected events
                events = event_queue
            
            # Close WebSocket
            if ws:
                ws.close()
            
        except Exception as e:
            print(f"WebSocket connection failed for {relay_url}: {e}")
        
        return events
    
    def update_cache(self) -> Dict[str, int]:
        """Update the cache with new events - smart fetching based on first run"""
        try:
            print("Starting Nostr cache update with Python client...")
            
            pubkey = self.npub_to_hex(self.npub)
            if not pubkey:
                raise ValueError("Invalid npub provided")
            
            print(f"Using pubkey: {pubkey}")
            
            # Check if this is the first run
            is_first = self.is_first_run()
            
            if is_first:
                # FIRST RUN: Full historical fetch (no time limit)
                since = None  # Fetch ALL historical events
                print(f"🎉 First run! Fetching ALL historical content (no time limit)...")
                print(f"📅 This may take a while as we're fetching complete history...")
            else:
                # SUBSEQUENT RUNS: Only get recent updates
                last_event = self.db.get_last_event_timestamp()
                if last_event:
                    # Add a larger buffer (2 hours) to avoid missing events due to timing issues
                    # This accounts for relay propagation delays and timezone differences
                    buffer_time = 2 * 60 * 60  # 2 hours
                    since = last_event - buffer_time
                    print(f"🔄 Update run: Fetching new events since last update")
                    print(f"📅 Last event: {time.strftime('%Y-%m-%d %H:%M', time.localtime(last_event))}")
                    print(f"🕐 Using {buffer_time//3600}h buffer - fetching since: {time.strftime('%Y-%m-%d %H:%M', time.localtime(since))}")
                else:
                    # Fallback to 7 days if no timestamp found
                    since = int(time.time()) - (7 * 24 * 60 * 60)
                    print(f"⚠️ No last timestamp found, fetching last 7 days")
            
            print(f"Fetching events since timestamp: {since}")
            
            # Fetch events with appropriate time range
            events = self.fetch_events_simple(pubkey, since)
            print(f"Fetched {len(events)} total events from all relays")
            
            if events:
                # Show sample of what we found
                print("Sample event:", events[0] if events else "None")
                
                # Sort by timestamp to see range
                sorted_events = sorted(events, key=lambda x: x.get('created_at', 0))
                if sorted_events:
                    oldest = sorted_events[0].get('created_at', 0)
                    newest = sorted_events[-1].get('created_at', 0)
                    print(f"📅 Event date range: {time.strftime('%Y-%m-%d', time.localtime(oldest))} to {time.strftime('%Y-%m-%d', time.localtime(newest))}")
            
            processed = self.process_events(events)
            print(f"Processed: {processed['posts']} posts, {processed['quips']} quips, {processed['images']} images")
            
            # If this was a first run with lots of data, note it
            if is_first and sum(processed.values()) > 20:
                print(f"✨ Successfully loaded your historical Nostr content!")
                print(f"   Future updates will only fetch new content")
            
            return processed
            
        except Exception as e:
            print(f"Error updating cache: {e}")
            raise e
    
    def fetch_all_events(self, pubkey: str) -> List[Dict]:
        """Fetch all events (no time limit) for testing"""
        print("Fetching ALL events (no time limit)...")
        return self.fetch_events_simple(pubkey, since=None)
    
    def force_full_historical_fetch(self) -> Dict[str, int]:
        """Force a complete historical fetch of all events (ignoring existing data)"""
        try:
            print("🔄 FORCING FULL HISTORICAL FETCH...")
            print("⚠️  This will fetch ALL historical events regardless of what's already cached")
            
            pubkey = self.npub_to_hex(self.npub)
            if not pubkey:
                raise ValueError("Invalid npub provided")
            
            print(f"Using pubkey: {pubkey}")
            print(f"🚀 Fetching ALL historical events (no time restrictions)...")
            
            # Use reliable relays and fetch sequentially for better reliability
            reliable_relays = ['wss://relay.nostr.band', 'wss://relay.primal.net', 'wss://nos.lol']
            print(f"📡 Using {len(reliable_relays)} reliable relays with sequential fetch for maximum reliability")
            
            all_events = []
            unique_events = {}
            
            for relay in reliable_relays:
                try:
                    print(f"🔍 Fetching from: {relay}")
                    events = self._fetch_from_single_relay_timeout(relay, pubkey, since=None, timeout=25)
                    print(f"✅ Found {len(events)} events from {relay}")
                    
                    # Add unique events
                    for event in events:
                        event_id = event.get('id')
                        if event_id and event_id not in unique_events:
                            unique_events[event_id] = event
                    
                    # Small delay between relays to be respectful
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"❌ Error with {relay}: {e}")
                    continue
            
            all_events = list(unique_events.values())
            print(f"📊 Total unique events collected: {len(all_events)}")
            
            if all_events:
                # Sort by timestamp to see range
                sorted_events = sorted(all_events, key=lambda x: x.get('created_at', 0))
                oldest = sorted_events[0].get('created_at', 0)
                newest = sorted_events[-1].get('created_at', 0)
                print(f"📅 Full date range: {time.strftime('%Y-%m-%d', time.localtime(oldest))} to {time.strftime('%Y-%m-%d', time.localtime(newest))}")
                
                # Show some stats about what we found
                print(f"🗓️  Oldest event: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(oldest))}")
                print(f"🗓️  Newest event: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(newest))}")
                print(f"📈 Events span {(newest - oldest) / (24 * 60 * 60):.1f} days")
            
            # Process all events
            processed = self.process_events(all_events)
            print(f"✅ Processed: {processed['posts']} posts, {processed['quips']} quips, {processed['images']} images")
            print(f"🎉 Full historical fetch completed!")
            
            return processed
            
        except Exception as e:
            print(f"❌ Error during full historical fetch: {e}")
            raise e
    
    def process_events(self, events: List[Dict]) -> Dict[str, int]:
        """Process and store events in the database"""
        processed = {'posts': 0, 'quips': 0, 'images': 0}
        
        for event in events:
            try:
                # Prepare event data with standardized structure
                event_data = {
                    'id': event.get('id'),
                    'content': event.get('content', ''),
                    'created_at': event.get('created_at'),
                    'pubkey': event.get('pubkey'),
                    'kind': event.get('kind', 1),
                    'tags': event.get('tags', [])
                }
                
                content = event_data['content']
                tags = event_data['tags']
                
                # Check for images first
                image_urls = self.extract_image_urls(content)
                if image_urls:
                    # Process each image URL
                    for image_url in image_urls:
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
