#!/usr/bin/env python3

import sqlite3
import os
import config

def clear_mock_data():
    """Clear all existing data from the database"""
    print("🧹 Clearing existing mock data...")
    
    # Create data directory if it doesn't exist
    os.makedirs(os.path.dirname(config.DATABASE_PATH), exist_ok=True)
    
    try:
        with sqlite3.connect(config.DATABASE_PATH) as conn:
            cursor = conn.cursor()
            
            # Clear all tables
            cursor.execute('DELETE FROM posts')
            cursor.execute('DELETE FROM quips') 
            cursor.execute('DELETE FROM images')
            
            conn.commit()
            
            # Get counts to confirm
            cursor.execute('SELECT COUNT(*) FROM posts')
            posts_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM quips')
            quips_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM images')
            images_count = cursor.fetchone()[0]
            
            print(f"✅ Mock data cleared successfully!")
            print(f"   Posts: {posts_count}, Quips: {quips_count}, Images: {images_count}")
            
    except Exception as e:
        print(f"❌ Error clearing data: {e}")

if __name__ == "__main__":
    clear_mock_data()
