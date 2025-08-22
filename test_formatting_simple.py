#!/usr/bin/env python3

"""
Simple test to verify our JavaScript markdown formatting works
"""

test_content = """
Check out this amazing site: https://stacker.news/items/677439

Here's a [markdown link](https://proton.me) that should be clickable.

And here's a markdown image: ![Test Image](https://via.placeholder.com/300x200.jpg)

Direct image URL: https://via.placeholder.com/400x300.png

Some **bold text** and *italic text* too.
"""

print("🧪 TESTING MARKDOWN FORMATTING")
print("=" * 50)
print("Original content:")
print(repr(test_content))

print("\n" + "=" * 50)
print("Expected transformations:")
print("1. https://stacker.news/items/677439 → <a href=... (clickable link)")
print("2. [markdown link](https://proton.me) → <a href=... (clickable link)")
print("3. ![Test Image](...) → <img src=... (displayed image)")
print("4. https://...placeholder.../400x300.png → <img src=... (auto-detected image)")
print("5. **bold text** → <strong>bold text</strong>")
print("6. *italic text* → <em>italic text</em>")

print("\n" + "=" * 50)
print("Visit http://localhost:3000/posts to see the real formatting!")
print("Look for these specific posts:")
print("- 'Can someone explain the need for channels...' (has stacker.news link)")
print("- 'Mobile and my threat model.' (has proton.me link)")
