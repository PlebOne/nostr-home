#!/usr/bin/env python3

import time
import schedule
import requests
import threading
from datetime import datetime
import config

class BackgroundScheduler:
    def __init__(self):
        self.base_url = "http://localhost:3000"
        self.running = True
    
    def update_cache(self):
        """Trigger cache update via API call"""
        try:
            print(f"[{datetime.now()}] Running scheduled cache update...")
            response = requests.post(f"{self.base_url}/api/update-cache", timeout=60)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    processed = data.get('processed', {})
                    print(f"[{datetime.now()}] ✅ Cache update completed: {processed}")
                else:
                    print(f"[{datetime.now()}] ❌ Cache update failed: {data.get('message')}")
            else:
                print(f"[{datetime.now()}] ❌ Cache update failed with status {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"[{datetime.now()}] ❌ Cache update failed - connection error: {e}")
        except Exception as e:
            print(f"[{datetime.now()}] ❌ Cache update failed - unexpected error: {e}")
    
    def health_check(self):
        """Check if the main app is responsive"""
        try:
            response = requests.get(f"{self.base_url}/api/stats", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def wait_for_app(self):
        """Wait for the main app to be ready"""
        print("Waiting for main application to be ready...")
        while not self.health_check():
            time.sleep(5)
        print("✅ Main application is ready!")
    
    def run(self):
        """Run the scheduler"""
        print("🕒 Background Scheduler starting...")
        print(f"📊 Cache update interval: {config.CACHE_UPDATE_INTERVAL} hours")
        
        # Wait for main app to be ready
        self.wait_for_app()
        
        # Schedule the cache updates
        schedule.every(config.CACHE_UPDATE_INTERVAL).hours.do(self.update_cache)
        
        # Run initial update after a short delay
        threading.Timer(10.0, self.update_cache).start()
        
        print("🔄 Scheduler is running...")
        
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except KeyboardInterrupt:
                print("\n🛑 Scheduler stopping...")
                self.running = False
                break
            except Exception as e:
                print(f"[{datetime.now()}] ❌ Scheduler error: {e}")
                time.sleep(60)

if __name__ == "__main__":
    scheduler = BackgroundScheduler()
    scheduler.run()
