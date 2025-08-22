#!/usr/bin/env python3

import sqlite3
import time
import json

# Create a test post with a web image
test_content = '''# Test Post with Featured Image

![Beautiful landscape](https://picsum.photos/800/400?random=1)

This is a test post to demonstrate the featured image functionality. The image above should appear as a featured image at the top of the post, and should be removed from the content below.

Lorem ipsum dolor sit amet, consectetur adipiscing elit. This content should appear without the duplicate image.

## Another Section

More content here to make it look like a real blog post with some **bold text** and *italic formatting*.

### Code Example

```python
def hello_world():
    print("Hello, Nostr!")
```

The featured image should only appear once at the top!'''

def create_test_post():
    conn = sqlite3.connect('data/nostr_content.db')
    cursor = conn.cursor()
    
    # Insert the test post
    cursor.execute('''
        INSERT INTO posts (id, pubkey, content, created_at, kind, tags)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        'test_featured_image_post',
        'test_pubkey_12345',
        test_content,
        int(time.time()),
        1,
        json.dumps([['title', 'Test Post with Featured Image']])
    ))
    
    conn.commit()
    conn.close()
    print('Test post with featured image created successfully!')

if __name__ == '__main__':
    create_test_post()
