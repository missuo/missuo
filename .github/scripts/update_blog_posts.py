#!/usr/bin/env python3
"""
Script to update README.md with recent blog posts from RSS feed.
"""

import feedparser
import re
from datetime import datetime

RSS_URL = "https://missuo.me/index.xml"
README_PATH = "README.md"
MAX_POSTS = 5

def format_date(date_str):
    """Convert RSS date to a more readable format."""
    try:
        # Parse the RSS date format: "Sat, 02 Aug 2025 18:12:17 +0800"
        dt = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
        return dt.strftime("%B %d, %Y")
    except:
        return date_str

def fetch_recent_posts():
    """Fetch recent posts from the RSS feed."""
    try:
        feed = feedparser.parse(RSS_URL)
        posts = []
        
        for entry in feed.entries[:MAX_POSTS]:
            title = entry.title
            date = format_date(entry.published)
            posts.append(f"- **{date}**: [{title}]({entry.link})")
        
        return posts
    except Exception as e:
        print(f"Error fetching RSS feed: {e}")
        return []

def update_readme():
    """Update README.md with recent blog posts."""
    try:
        with open(README_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Get recent posts
        posts = fetch_recent_posts()
        if not posts:
            print("No posts found or error occurred")
            return
        
        # Create the blog posts section
        blog_section = "📝 **Recent Blog Posts**\n" + "\n".join(posts) + "\n"
        
        # Remove existing blog posts section if it exists
        existing_pattern = r'\n📝 \*\*Recent Blog Posts\*\*\n(?:- \*\*.*?\*\*: \[.*?\]\(.*?\)\n)*\n?'
        content = re.sub(existing_pattern, '', content)
        
        # Find where to insert the blog posts (after the social media line and before the first separator)
        pattern = r'(Feel free to contact me.*?Discord.*?\n\n)(-------)'
        match = re.search(pattern, content, re.DOTALL)
        
        if match:
            # Insert blog posts section between contact info and first separator
            new_content = content[:match.start(2)] + blog_section + "\n" + content[match.start(2):]
        else:
            # Fallback: insert before first separator
            separator_match = re.search(r'\n-------\n', content)
            if separator_match:
                insert_pos = separator_match.start()
                new_content = content[:insert_pos] + "\n" + blog_section + content[insert_pos:]
            else:
                # Fallback: append to end
                new_content = content + "\n\n" + blog_section
        
        # Write the updated content
        with open(README_PATH, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print("README.md updated successfully!")
        print(f"Added {len(posts)} recent blog posts")
        
    except Exception as e:
        print(f"Error updating README: {e}")

if __name__ == "__main__":
    update_readme()