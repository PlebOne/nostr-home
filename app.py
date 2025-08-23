from flask import Flask, jsonify, request, send_from_directory
import time
import subprocess
import re
from datetime import datetime
from flask_cors import CORS
from flask_socketio import SocketIO
import os
import config
from database import NostrDatabase
from nostr_client import NostrContentClient
from nostr_relay_enhanced import EnhancedNostrRelay
import requests

# Global start time for uptime calculation
APP_START_TIME = time.time()

app = Flask(__name__, static_folder='public')
CORS(app)

# Initialize SocketIO for relay functionality
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize database and Nostr client
db = NostrDatabase()
nostr_client = NostrContentClient()

# Initialize Enhanced Nostr relay if enabled
# Initialize Enhanced Nostr relay if enabled
relay = None
if config.RELAY_ENABLED:
    relay = EnhancedNostrRelay(socketio)
    print(f"🚀 Enhanced Nostr Relay enabled on WebSocket endpoint")
    print(f"✨ Supporting {len(relay.get_supported_nips())} NIPs")

def format_timestamp(timestamp):
    """Format timestamp for API response"""
    return datetime.fromtimestamp(timestamp).isoformat()

def parse_tags(tags_list):
    """Parse tags for API response"""
    return tags_list if isinstance(tags_list, list) else []

# API Routes
@app.route('/api/posts')
def get_posts():
    try:
        page = int(request.args.get('page', 1))
        posts = db.get_posts(page, config.MAX_POSTS_PER_PAGE)
        
        # Get total count for pagination
        counts = db.get_counts()
        total_posts = counts['posts']
        total_pages = (total_posts + config.MAX_POSTS_PER_PAGE - 1) // config.MAX_POSTS_PER_PAGE
        
        formatted_posts = []
        for post in posts:
            formatted_posts.append({
                'id': post['id'],
                'content': post['content'],
                'created_at': format_timestamp(post['created_at']),
                'tags': parse_tags(post['tags'])
            })
        
        return jsonify({
            'posts': formatted_posts,
            'page': page,
            'totalPages': total_pages,
            'totalPosts': total_posts,
            'hasMore': len(posts) == config.MAX_POSTS_PER_PAGE
        })
    except Exception as e:
        print(f"Error fetching posts: {e}")
        return jsonify({'error': 'Failed to fetch posts'}), 500

@app.route('/api/quips')
def get_quips():
    try:
        page = int(request.args.get('page', 1))
        quips = db.get_quips(page, config.MAX_QUIPS_PER_PAGE)
        
        # Get total count for pagination
        counts = db.get_counts()
        total_quips = counts['quips']
        total_pages = (total_quips + config.MAX_QUIPS_PER_PAGE - 1) // config.MAX_QUIPS_PER_PAGE
        
        formatted_quips = []
        for quip in quips:
            formatted_quips.append({
                'id': quip['id'],
                'content': quip['content'],
                'created_at': format_timestamp(quip['created_at']),
                'tags': parse_tags(quip['tags'])
            })
        
        return jsonify({
            'quips': formatted_quips,
            'page': page,
            'totalPages': total_pages,
            'totalQuips': total_quips,
            'hasMore': len(quips) == config.MAX_QUIPS_PER_PAGE
        })
    except Exception as e:
        print(f"Error fetching quips: {e}")
        return jsonify({'error': 'Failed to fetch quips'}), 500

@app.route('/api/images')
def get_images():
    try:
        page = int(request.args.get('page', 1))
        images = db.get_images(page, config.MAX_IMAGES_PER_PAGE)
        
        formatted_images = []
        for image in images:
            formatted_images.append({
                'id': image['id'],
                'content': image['content'],
                'image_url': image['image_url'],
                'created_at': format_timestamp(image['created_at']),
                'tags': parse_tags(image['tags'])
            })
        
        return jsonify({
            'images': formatted_images,
            'page': page,
            'hasMore': len(images) == config.MAX_IMAGES_PER_PAGE
        })
    except Exception as e:
        print(f"Error fetching images: {e}")
        return jsonify({'error': 'Failed to fetch images'}), 500

@app.route('/api/stats')
def get_stats():
    try:
        counts = db.get_counts()
        return jsonify(counts)
    except Exception as e:
        print(f"Error fetching stats: {e}")
        return jsonify({'error': 'Failed to fetch statistics'}), 500

@app.route('/api/config')
def get_site_config():
    """Get site configuration for frontend"""
    return jsonify({
        'site_name': config.SITE_NAME,
        'site_subtitle': config.SITE_SUBTITLE,
        'npub': config.NOSTR_NPUB
    })

@app.route('/api/update-cache', methods=['POST'])
def update_cache():
    try:
        print('Manual cache update requested')
        result = nostr_client.update_cache()
        return jsonify({
            'success': True,
            'message': 'Cache updated successfully',
            'processed': result
        })
    except Exception as e:
        print(f"Error updating cache: {e}")
        return jsonify({
            'error': 'Failed to update cache',
            'message': str(e)
        }), 500

# Relay API routes - Proxy to Go relay
@app.route('/api/relay/info')
def relay_info():
    """Get relay information (NIP-11) - proxied from Go relay"""
    try:
        # Get NIP-11 relay info from rnostr
        response = requests.get("http://172.18.0.2:8080/", timeout=5, headers={"Accept": "application/nostr+json"})
        if response.status_code == 200:
            relay_info = response.json()
            # rnostr provides NIP-11 compliant info directly
            return jsonify(relay_info)
        else:
            return jsonify({"error": "Go relay not responding"}), 502
    except Exception as e:
        print(f"Error connecting to Go relay: {e}")
        return jsonify({"error": "Go relay not available"}), 502

@app.route("/api/relay/stats")
def relay_stats():
    """Get relay statistics from rnostr Prometheus metrics"""
    try:
        import re
        
        # Get Prometheus metrics from rnostr
        response = requests.get("http://172.18.0.2:8080/metrics?auth=auth_key", timeout=5)
        if response.status_code == 200:
            metrics_text = response.text
            
            # Parse Prometheus metrics
            stats = {
                "relay_events": 0,
                "new_events": 0,
                "total_sessions": 0,
                "active_sessions": 0,
                "total_requests": 0,
                "event_commands": 0,
                "close_commands": 0,
                "database_writes": 0,
                "database_reads": 0,
                "uptime_seconds": round(time.time() - APP_START_TIME),
                "uptime_hours": round((time.time() - APP_START_TIME) / 3600, 1),
                "relay_software": "rnostr v0.4.8",
                "supported_nips": [1, 2, 4, 9, 11, 12, 15, 16, 20, 22, 25, 26, 28, 33, 40, 70],
                "status": "online"
            }
            
            # Parse metrics with regex
            patterns = {
                "new_events": r"nostr_relay_new_event (\d+)",
                "total_sessions": r"nostr_relay_session_total (\d+)",
                "active_sessions": r"nostr_relay_session (\d+)",
                "event_commands": r"nostr_relay_message_total\{command=\"EVENT\"\} (\d+)",
                "close_commands": r"nostr_relay_message_total\{command=\"CLOSE\"\} (\d+)",
                "database_writes": r"nostr_relay_db_write_count (\d+)",
                "database_reads": r"nostr_relay_db_get_count (\d+)"
            }
            
            for key, pattern in patterns.items():
                match = re.search(pattern, metrics_text)
                if match:
                    stats[key] = int(match.group(1))
            
            # Calculate total requests from REQ commands
            req_match = re.search(r"nostr_relay_message_total\{command=\"REQ\"\} (\d+)", metrics_text)
            if req_match:
                stats["total_requests"] = int(req_match.group(1))
            
            # Set relay_events to new_events for now (could be expanded)
            stats["relay_events"] = stats["new_events"]
            
            # Get our local content counts
            counts = db.get_counts()
            stats["local_content"] = counts["posts"] + counts["quips"] + counts["images"]
            stats["total_content"] = stats["relay_events"] + stats["local_content"]
            
            return jsonify(stats)
            
        else:
            raise Exception(f"Metrics endpoint returned {response.status_code}")
            
    except Exception as e:
        print(f"Error getting relay metrics: {e}")
        # Fallback stats
        counts = db.get_counts()
        return jsonify({
            "relay_events": 0,
            "new_events": 0,
            "total_sessions": 0,
            "active_sessions": 0,
            "local_content": counts["posts"] + counts["quips"] + counts["images"],
            "total_content": counts["posts"] + counts["quips"] + counts["images"],
            "uptime_seconds": round(time.time() - APP_START_TIME),
            "uptime_hours": round((time.time() - APP_START_TIME) / 3600, 1),
            "relay_software": "rnostr v0.4.8",
            "status": "online"
        })

@app.route('/api/relay/nips')
def relay_nips():
    """Get supported NIPs - from Go relay info"""
    try:
        response = requests.get('http://172.18.0.2:8080/', timeout=5)
        if response.status_code == 200:
            data = response.json()
            return jsonify({
                'nips': data.get('supported_nips', []),
                'count': len(data.get('supported_nips', []))
            })
        else:
            # Fallback to known NIPs
            fallback_nips = [1, 2, 3, 4, 5, 9, 10, 11, 12, 13, 15, 16, 20, 22, 25, 26, 28, 33, 40, 42, 45, 50, 65]
            return jsonify({
                'nips': fallback_nips,
                'count': len(fallback_nips)
            })
    except Exception as e:
        print(f"Error connecting to Go relay for NIPs: {e}")
        # Fallback to known NIPs
        fallback_nips = [1, 2, 3, 4, 5, 9, 10, 11, 12, 13, 15, 16, 20, 22, 25, 26, 28, 33, 40, 42, 45, 50, 65]
        return jsonify({
            'nips': fallback_nips,
            'count': len(fallback_nips)
        })

@app.route("/api/relay/activity")
def relay_activity():
    """Get recent relay activity"""
    try:
        # Get our local content as activity since rnostr doesnt expose event details
        recent_posts = db.get_posts(limit=5, page=1)['posts']
        recent_quips = db.get_quips(limit=5)
        
        activity = []
        
        # Add recent posts
        for post in recent_posts:
            activity.append({
                'type': 'note',
                'id': post['id'],
                'created_at': post['created_at'],
                'content_preview': post['content'][:100] + '...' if len(post['content']) > 100 else post['content']
            })
        
        # Add recent quips
        for quip in recent_quips:
            activity.append({
                'type': 'note',
                'id': quip['id'],
                'created_at': quip['created_at'],
                'content_preview': quip['content'][:100] + '...' if len(quip['content']) > 100 else quip['content']
            })
        
        # Sort by created_at descending
        activity.sort(key=lambda x: x['created_at'], reverse=True)
        
        return jsonify({
            'activity': activity[:10],  # Return top 10 most recent
            'total_events': len(activity),
            'last_updated': datetime.now().isoformat()
        })
    
    except Exception as e:
        print(f"Error getting relay activity: {e}")
        return jsonify({'activity': [], 'error': 'Failed to get relay activity'}), 500

    """Get recent relay activity"""
    if not relay:
        return jsonify({'error': 'Relay not enabled'}), 404
    
    try:
        # Get recent posts as activity
        recent_posts = db.get_posts(page=1, limit=10)
        
        formatted_events = []
        for post in recent_posts:
            formatted_events.append({
                'id': post['id'],
                'pubkey': post['pubkey'],
                'kind': post.get('kind', 1),
                'timestamp': post['created_at'] * 1000  # Convert to milliseconds
            })
        
        return jsonify({
            'recent': formatted_events
        })
    except Exception as e:
        print(f"Error getting relay activity: {e}")
        return jsonify({
            'recent': []
        })

@app.route('/api/posts/<post_id>')
def get_single_post(post_id):
    try:
        post = db.get_post_by_id(post_id)
        if not post:
            return jsonify({'error': 'Post not found'}), 404
            
        formatted_post = {
            'id': post['id'],
            'content': post['content'],
            'created_at': format_timestamp(post['created_at']),
            'tags': parse_tags(post.get('tags', [])),
            'kind': post.get('kind', 1)
        }
        
        return jsonify(formatted_post)
    except Exception as e:
        print(f"Error getting post: {e}")
        return jsonify({'error': 'Failed to get post'}), 500

# Serve static files
@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/post')
def serve_single_post():
    return send_from_directory(app.static_folder, 'post.html')

@app.route('/posts')
def serve_posts():
    return send_from_directory(app.static_folder, 'posts.html')

@app.route('/quips')
def serve_quips():
    return send_from_directory(app.static_folder, 'quips.html')

@app.route('/gallery')
def serve_gallery():
    return send_from_directory(app.static_folder, 'gallery.html')

@app.route('/relay')
def serve_relay():
    return send_from_directory(app.static_folder, 'relay.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

# 404 handler
@app.errorhandler(404)
def not_found(error):
    return send_from_directory(app.static_folder, '404.html'), 404




if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3000)

# Simple working scheduler
import threading
import time

def simple_scheduler():
    """Simple background scheduler that updates content every 30 minutes"""
    def scheduler_loop():
        print("[Scheduler] Starting content update scheduler...")
        time.sleep(60)  # Wait 1 minute after startup
        
        while True:
            try:
                print("[Scheduler] Running scheduled content update...")
                result = nostr_client.update_cache()
                print(f"[Scheduler] Update completed: {result}")
            except Exception as e:
                print(f"[Scheduler] Error during update: {e}")
            
            # Wait 30 minutes (1800 seconds)
            time.sleep(1800)
    
    # Start scheduler in background thread
    thread = threading.Thread(target=scheduler_loop, daemon=True)
    thread.start()
    print("[Scheduler] Background scheduler initialized")

# Start scheduler automatically
simple_scheduler()

