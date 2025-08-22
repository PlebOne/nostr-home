import sqlite3
import json
import os
from typing import List, Dict, Optional, Tuple
import config

class NostrDatabase:
    def __init__(self):
        self.db_path = config.DATABASE_PATH
        self.ensure_data_directory()
        self.init_database()
    
    def ensure_data_directory(self):
        """Ensure the data directory exists"""
        dir_path = os.path.dirname(self.db_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
    
    def init_database(self):
        """Initialize the database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create posts table for long-form content
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS posts (
                    id TEXT PRIMARY KEY,
                    pubkey TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    tags TEXT,
                    kind INTEGER DEFAULT 1,
                    cached_at INTEGER DEFAULT (strftime('%s', 'now'))
                )
            ''')
            
            # Create quips table for short posts
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS quips (
                    id TEXT PRIMARY KEY,
                    pubkey TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    tags TEXT,
                    kind INTEGER DEFAULT 1,
                    cached_at INTEGER DEFAULT (strftime('%s', 'now'))
                )
            ''')
            
            # Create images table for image content
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS images (
                    id TEXT PRIMARY KEY,
                    pubkey TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    image_url TEXT,
                    tags TEXT,
                    kind INTEGER DEFAULT 1,
                    cached_at INTEGER DEFAULT (strftime('%s', 'now'))
                )
            ''')
            
            # Relay events table - stores ALL events received by the relay
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS relay_events (
                    id TEXT PRIMARY KEY,
                    pubkey TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    tags TEXT,
                    kind INTEGER NOT NULL,
                    sig TEXT NOT NULL,
                    received_at INTEGER DEFAULT (strftime('%s', 'now'))
                )
            ''')
            
            # Active subscriptions table - tracks client subscriptions
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS relay_subscriptions (
                    id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    filters TEXT NOT NULL,
                    created_at INTEGER DEFAULT (strftime('%s', 'now'))
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at DESC)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_quips_created_at ON quips(created_at DESC)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_images_created_at ON images(created_at DESC)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_relay_events_pubkey ON relay_events(pubkey)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_relay_events_kind ON relay_events(kind)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_relay_events_created_at ON relay_events(created_at DESC)')
            
            conn.commit()
    
    def save_post(self, event: Dict) -> None:
        """Save a long-form post"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO posts (id, pubkey, content, created_at, tags, kind)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                event['id'],
                event['pubkey'],
                event['content'],
                event['created_at'],
                json.dumps(event.get('tags', [])),
                event.get('kind', 1)
            ))
            conn.commit()
    
    def save_quip(self, event: Dict) -> None:
        """Save a short quip"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO quips (id, pubkey, content, created_at, tags, kind)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                event['id'],
                event['pubkey'],
                event['content'],
                event['created_at'],
                json.dumps(event.get('tags', [])),
                event.get('kind', 1)
            ))
            conn.commit()
    
    def save_image(self, event: Dict, image_url: str) -> None:
        """Save an image post"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO images (id, pubkey, content, created_at, image_url, tags, kind)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                event['id'],
                event['pubkey'],
                event['content'],
                event['created_at'],
                image_url,
                json.dumps(event.get('tags', [])),
                event.get('kind', 1)
            ))
            conn.commit()
    
    def get_posts(self, page: int = 1, limit: int = None) -> List[Dict]:
        """Get posts with pagination"""
        if limit is None:
            limit = config.MAX_POSTS_PER_PAGE
        
        offset = (page - 1) * limit
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, pubkey, content, created_at, tags, kind, cached_at
                FROM posts 
                WHERE length(content) > 200
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            
            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]
    
    def get_post_by_id(self, post_id: str) -> Optional[Dict]:
        """Get a single post by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, pubkey, content, created_at, tags, kind, cached_at
                FROM posts 
                WHERE id = ?
            ''', (post_id,))
            
            row = cursor.fetchone()
            if row:
                return self._row_to_dict(row)
            return None
    
    def get_quips(self, page: int = 1, limit: int = None) -> List[Dict]:
        """Get quips with pagination"""
        if limit is None:
            limit = config.MAX_QUIPS_PER_PAGE
        
        offset = (page - 1) * limit
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, pubkey, content, created_at, tags, kind, cached_at
                FROM quips 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            
            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]
    
    def get_images(self, page: int = 1, limit: int = None) -> List[Dict]:
        """Get images with pagination"""
        if limit is None:
            limit = config.MAX_IMAGES_PER_PAGE
        
        offset = (page - 1) * limit
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, pubkey, content, created_at, image_url, tags, kind, cached_at
                FROM images 
                WHERE image_url IS NOT NULL
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            
            rows = cursor.fetchall()
            return [self._row_to_dict_with_image(row) for row in rows]
    
    def get_counts(self) -> Dict[str, int]:
        """Get content statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM posts WHERE length(content) > 200')
            posts_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM quips WHERE length(content) <= 200')
            quips_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM images WHERE image_url IS NOT NULL')
            images_count = cursor.fetchone()[0]
            
            return {
                'posts': posts_count,
                'quips': quips_count,
                'images': images_count
            }
    
    def get_last_event_timestamp(self) -> Optional[int]:
        """Get the timestamp of the most recent cached event"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT MAX(created_at) as max_timestamp FROM (
                    SELECT created_at FROM posts
                    UNION ALL
                    SELECT created_at FROM quips
                    UNION ALL
                    SELECT created_at FROM images
                )
            ''')
            
            result = cursor.fetchone()
            return result[0] if result and result[0] else None
    
    def _row_to_dict(self, row: Tuple) -> Dict:
        """Convert database row to dictionary"""
        return {
            'id': row[0],
            'pubkey': row[1],
            'content': row[2],
            'created_at': row[3],
            'tags': json.loads(row[4]) if row[4] else [],
            'kind': row[5],
            'cached_at': row[6]
        }
    
    def _row_to_dict_with_image(self, row: Tuple) -> Dict:
        """Convert database row to dictionary including image URL"""
        return {
            'id': row[0],
            'pubkey': row[1],
            'content': row[2],
            'created_at': row[3],
            'image_url': row[4],
            'tags': json.loads(row[5]) if row[5] else [],
            'kind': row[6],
            'cached_at': row[7]
        }
    
    # ===== RELAY METHODS =====
    
    def save_relay_event(self, event: Dict) -> bool:
        """Save an event to the relay"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO relay_events (id, pubkey, content, created_at, tags, kind, sig)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    event['id'],
                    event['pubkey'],
                    event['content'],
                    event['created_at'],
                    json.dumps(event.get('tags', [])),
                    event['kind'],
                    event['sig']
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error saving relay event: {e}")
            return False
    
    def get_relay_events(self, filters: List[Dict], limit: int = 500) -> List[Dict]:
        """Get events from relay based on filters"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            events = []
            for filter_obj in filters:
                # Build dynamic query based on filter
                query_parts = ["SELECT * FROM relay_events WHERE 1=1"]
                params = []
                
                # Filter by authors
                if 'authors' in filter_obj:
                    placeholders = ','.join(['?' for _ in filter_obj['authors']])
                    query_parts.append(f"AND pubkey IN ({placeholders})")
                    params.extend(filter_obj['authors'])
                
                # Filter by kinds
                if 'kinds' in filter_obj:
                    placeholders = ','.join(['?' for _ in filter_obj['kinds']])
                    query_parts.append(f"AND kind IN ({placeholders})")
                    params.extend(filter_obj['kinds'])
                
                # Filter by since
                if 'since' in filter_obj:
                    query_parts.append("AND created_at >= ?")
                    params.append(filter_obj['since'])
                
                # Filter by until
                if 'until' in filter_obj:
                    query_parts.append("AND created_at <= ?")
                    params.append(filter_obj['until'])
                
                # Filter by IDs
                if 'ids' in filter_obj:
                    placeholders = ','.join(['?' for _ in filter_obj['ids']])
                    query_parts.append(f"AND id IN ({placeholders})")
                    params.extend(filter_obj['ids'])
                
                # Order and limit
                query_parts.append("ORDER BY created_at DESC")
                query_parts.append(f"LIMIT {min(limit, config.RELAY_MAX_EVENTS_PER_REQUEST)}")
                
                query = ' '.join(query_parts)
                cursor.execute(query, params)
                
                for row in cursor.fetchall():
                    events.append({
                        'id': row[0],
                        'pubkey': row[1],
                        'content': row[2],
                        'created_at': row[3],
                        'tags': json.loads(row[4]) if row[4] else [],
                        'kind': row[5],
                        'sig': row[6]
                    })
            
            return events
    
    def save_subscription(self, sub_id: str, client_id: str, filters: List[Dict]) -> None:
        """Save a client subscription"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO relay_subscriptions (id, client_id, filters)
                VALUES (?, ?, ?)
            ''', (sub_id, client_id, json.dumps(filters)))
            conn.commit()
    
    def remove_subscription(self, sub_id: str, client_id: str) -> None:
        """Remove a client subscription"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM relay_subscriptions 
                WHERE id = ? AND client_id = ?
            ''', (sub_id, client_id))
            conn.commit()
    
    def get_relay_stats(self) -> Dict:
        """Get relay statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM relay_events')
            total_events = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(DISTINCT pubkey) FROM relay_events')
            unique_authors = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM relay_subscriptions')
            active_subscriptions = cursor.fetchone()[0]
            
            return {
                'total_events': total_events,
                'unique_authors': unique_authors,
                'active_subscriptions': active_subscriptions
            }

    def delete_event_if_owner(self, event_id: str, pubkey: str) -> bool:
        """Delete an event if the pubkey owns it (NIP-09)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check if event exists and is owned by the pubkey
            cursor.execute('SELECT pubkey FROM relay_events WHERE id = ?', (event_id,))
            result = cursor.fetchone()
            
            if result and result[0] == pubkey:
                cursor.execute('DELETE FROM relay_events WHERE id = ?', (event_id,))
                conn.commit()
                return cursor.rowcount > 0
            
            return False
    
    def delete_replaceable_event(self, kind: int, pubkey: str) -> bool:
        """Delete previous replaceable events (NIP-16)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM relay_events 
                WHERE kind = ? AND pubkey = ?
            ''', (kind, pubkey))
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_parameterized_replaceable_event(self, kind: int, pubkey: str, d_tag: str) -> bool:
        """Delete previous parameterized replaceable events (NIP-33)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM relay_events 
                WHERE kind = ? AND pubkey = ? AND tags LIKE ?
            ''', (kind, pubkey, f'%["d","{d_tag}"%'))
            conn.commit()
            return cursor.rowcount > 0
