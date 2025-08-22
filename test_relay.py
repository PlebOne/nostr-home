#!/usr/bin/env python3

"""
Test script for the integrated Nostr relay
This verifies that all components work together
"""

import sys
import time
import sqlite3
from database import NostrDatabase
import config

def test_database_setup():
    """Test that database tables are created properly"""
    print("🔍 Testing database setup...")
    
    try:
        db = NostrDatabase()
        
        # Test basic functionality
        stats = db.get_relay_stats()
        print(f"✅ Database connected - {stats['total_events']} events in relay")
        
        # Test that relay tables exist
        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            required_tables = ['posts', 'quips', 'images', 'relay_events', 'relay_subscriptions']
            missing_tables = [t for t in required_tables if t not in tables]
            
            if missing_tables:
                print(f"❌ Missing tables: {missing_tables}")
                return False
            else:
                print(f"✅ All required tables present: {', '.join(required_tables)}")
                return True
                
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_config():
    """Test configuration settings"""
    print("🔍 Testing configuration...")
    
    try:
        print(f"✅ Relay enabled: {config.RELAY_ENABLED}")
        print(f"✅ Relay name: {config.RELAY_NAME}")
        print(f"✅ Using npub: {config.NOSTR_NPUB}")
        print(f"✅ Max events per request: {config.RELAY_MAX_EVENTS_PER_REQUEST}")
        print(f"✅ Max subscriptions per client: {config.RELAY_MAX_SUBSCRIPTIONS_PER_CLIENT}")
        return True
        
    except Exception as e:
        print(f"❌ Config test failed: {e}")
        return False

def test_imports():
    """Test that all required modules can be imported"""
    print("🔍 Testing imports...")
    
    required_modules = [
        ('database', 'NostrDatabase'),
        ('nostr_client', 'NostrContentClient'),
        ('config', None),
    ]
    
    try:
        # Test Flask dependencies
        import flask
        import flask_cors
        print("✅ Flask dependencies available")
        
        # Try importing the relay module
        try:
            from nostr_relay import NostrRelay
            print("✅ Nostr relay module available")
        except ImportError as e:
            if 'flask_socketio' in str(e):
                print("⚠️  flask-socketio not installed - installing now...")
                import subprocess
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'flask-socketio', 'eventlet'])
                print("✅ flask-socketio installed")
            else:
                raise
        
        # Test other imports
        for module, class_name in required_modules:
            mod = __import__(module)
            if class_name:
                getattr(mod, class_name)
            print(f"✅ {module} imported successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing Nostr Home Hub Components")
    print("="*50)
    
    tests = [
        ("Imports", test_imports),
        ("Configuration", test_config), 
        ("Database", test_database_setup),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name} Test:")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All tests passed! Your Nostr Hub is ready to start.")
        print("\n🚀 To start your hub:")
        print("   python3 app.py")
        print("\n📱 Your hub will provide:")
        print("   🌐 Web Interface: http://localhost:3000")
        print("   📡 Nostr Relay: ws://localhost:3000/socket.io/")
        print("   📊 Relay Stats: http://localhost:3000/api/relay/stats")
        print("   ℹ️  Relay Info: http://localhost:3000/api/relay/info")
    else:
        print("❌ Some tests failed. Please fix the issues before starting.")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
