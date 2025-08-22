#!/usr/bin/env python3

"""
Reclassify existing content based on improved post detection
This moves qualifying content from quips to posts
"""

import sqlite3
import json
import config
from nostr_client import NostrContentClient

def reclassify_content():
    """Reclassify existing quips that should be posts"""
    print("🔄 Reclassifying content with improved logic...")
    
    client = NostrContentClient()
    
    with sqlite3.connect(config.DATABASE_PATH) as conn:
        cursor = conn.cursor()
        
        # Get all quips
        cursor.execute('SELECT * FROM quips')
        quips = cursor.fetchall()
        
        posts_moved = 0
        
        for quip in quips:
            # Reconstruct event data
            event_data = {
                'id': quip[0],
                'pubkey': quip[1], 
                'content': quip[2],
                'created_at': quip[3],
                'tags': json.loads(quip[4]) if quip[4] else [],
                'kind': quip[5]
            }
            
            # Check if this should be a post
            if client.is_long_form_post(event_data['content'], event_data['tags']):
                print(f"📝 Moving to posts: {event_data['content'][:60]}...")
                
                # Add to posts table
                cursor.execute('''
                    INSERT OR REPLACE INTO posts (id, pubkey, content, created_at, tags, kind)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    event_data['id'],
                    event_data['pubkey'],
                    event_data['content'],
                    event_data['created_at'],
                    json.dumps(event_data['tags']),
                    event_data['kind']
                ))
                
                # Remove from quips
                cursor.execute('DELETE FROM quips WHERE id = ?', (event_data['id'],))
                
                posts_moved += 1
        
        conn.commit()
        
        # Get updated counts
        cursor.execute('SELECT COUNT(*) FROM posts')
        posts_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM quips')
        quips_count = cursor.fetchone()[0]
        
        print(f"✅ Reclassification complete!")
        print(f"   📝 Posts: {posts_count} (moved {posts_moved})")
        print(f"   💬 Quips: {quips_count}")

if __name__ == "__main__":
    reclassify_content()
