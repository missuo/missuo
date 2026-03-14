#!/usr/bin/env python3

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime


FEED_URL = "https://missuo.me/index.xml"
COMMENTS_API_URL = "https://talk.owo.nz/v1/comments"
POST_PREFIX = "https://missuo.me/posts/"
CONTENT_NS = "http://purl.org/rss/1.0/modules/content/"
USER_AGENT = "missuo-blog-skill/1.0"


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read()


def normalize_datetime(value):
    if not value:
        return None

    try:
        return parsedate_to_datetime(value).isoformat()
    except (TypeError, ValueError, IndexError, OverflowError):
        return value


def parse_feed_items(feed_bytes):
    root = ET.fromstring(feed_bytes)
    channel = root.find("channel")
    if channel is None:
        raise ValueError("RSS channel not found")

    items = []
    for item in channel.findall("item"):
        data = {
            "title": text_or_none(item.find("title")),
            "link": text_or_none(item.find("link")),
            "guid": text_or_none(item.find("guid")),
            "published_at": normalize_datetime(text_or_none(item.find("pubDate"))),
            "description": text_or_none(item.find("description")),
            "content_html": text_or_none(item.find(f"{{{CONTENT_NS}}}encoded")),
        }
        items.append(data)
    return items


def text_or_none(node):
    if node is None or node.text is None:
        return None
    return node.text.strip()


def canonical_post_url(slug):
    clean = slug.strip("/")
    return urllib.parse.urljoin(POST_PREFIX, clean + "/")


def load_posts():
    return parse_feed_items(fetch(FEED_URL))


def find_post(posts, page_url=None, slug=None):
    target_url = page_url or canonical_post_url(slug)
    for post in posts:
        if post.get("link") == target_url:
            return post
    return None


def strip_content(post):
    data = dict(post)
    data.pop("content_html", None)
    return data


def strip_description(post):
    data = dict(post)
    data.pop("description", None)
    return data


def print_posts_text(posts):
    for index, post in enumerate(posts, start=1):
        print(f"{index}. {post['title']}")
        print(f"   URL: {post['link']}")
        print(f"   Published: {post['published_at']}")
        if post.get("guid"):
            print(f"   GUID: {post['guid']}")
        if post.get("description"):
            preview = collapse_whitespace(post["description"])
            print(f"   Description: {preview}")


def collapse_whitespace(value):
    return " ".join(value.split())


def comments_endpoint(page_url, page, page_size):
    query = urllib.parse.urlencode(
        {
            "pageKey": page_url,
            "page": page,
            "pageSize": page_size,
        }
    )
    return f"{COMMENTS_API_URL}?{query}"


def fetch_comments_page(page_url, page, page_size):
    payload = fetch(comments_endpoint(page_url, page, page_size))
    data = json.loads(payload)
    if not data.get("ok"):
        raise ValueError("comments API returned ok=false")
    return data


def fetch_all_comments(page_url, page_size):
    first_page = fetch_comments_page(page_url, 1, page_size)
    total_pages = first_page.get("pagination", {}).get("totalPages", 1)
    all_comments = list(first_page.get("comments", []))

    for page in range(2, total_pages + 1):
        page_data = fetch_comments_page(page_url, page, page_size)
        all_comments.extend(page_data.get("comments", []))

    return {
        "ok": True,
        "page": first_page.get("page"),
        "comments": all_comments,
        "pagination": {
            **first_page.get("pagination", {}),
            "page": 1,
            "fetchedPages": total_pages,
        },
    }


def print_comments_text(data):
    page = data.get("page") or {}
    print(f"Page: {page.get('pageTitle') or page.get('pageUrl')}")
    print(f"URL: {page.get('pageUrl')}")
    print(f"Comments: {page.get('commentCount')}")

    for comment in data.get("comments", []):
        indent = "  " * int(comment.get("depth") or 0)
        author = comment.get("authorName") or "Anonymous"
        created_at = comment.get("createdAt") or "unknown"
        source = comment.get("source") or "unknown"
        location = comment.get("ipCountryCode") or comment.get("ipCountry") or "unknown"
        admin = " [admin]" if comment.get("isAdmin") else ""
        print()
        print(f"{indent}- {author}{admin} | {created_at} | {source} | {location}")
        for line in (comment.get("content") or "").splitlines() or [""]:
            print(f"{indent}  {line}")


def command_posts(args):
    posts = load_posts()
    if args.limit is not None:
        posts = posts[: args.limit]
    if not args.include_content:
        posts = [strip_content(post) for post in posts]
    if not args.include_description:
        posts = [strip_description(post) for post in posts]

    if args.json:
        print(json.dumps(posts, ensure_ascii=False, indent=2))
        return

    print_posts_text(posts)


def command_post(args):
    posts = load_posts()
    post = find_post(posts, page_url=args.page_url, slug=args.slug)
    if post is None:
        raise ValueError("post not found in RSS feed")
    if not args.include_content:
        post = strip_content(post)

    if args.json:
        print(json.dumps(post, ensure_ascii=False, indent=2))
        return

    print(json.dumps(post, ensure_ascii=False, indent=2))


def command_comments(args):
    page_url = args.page_url or canonical_post_url(args.slug)
    if args.all_pages:
        data = fetch_all_comments(page_url, args.page_size)
    else:
        data = fetch_comments_page(page_url, args.page, args.page_size)

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return

    print_comments_text(data)


def build_parser():
    parser = argparse.ArgumentParser(
        description="Read missuo.me posts and comments.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    posts_parser = subparsers.add_parser("posts", help="List posts from RSS.")
    posts_parser.add_argument("--limit", type=int, default=10, help="Number of posts to return.")
    posts_parser.add_argument("--include-description", action="store_true", help="Include description HTML.")
    posts_parser.add_argument("--include-content", action="store_true", help="Include full content_html.")
    posts_parser.add_argument("--json", action="store_true", help="Print JSON output.")
    posts_parser.set_defaults(func=command_posts)

    post_parser = subparsers.add_parser("post", help="Fetch a single post from RSS.")
    add_post_target_arguments(post_parser)
    post_parser.add_argument("--include-content", action="store_true", help="Include full content_html.")
    post_parser.add_argument("--json", action="store_true", help="Print JSON output.")
    post_parser.set_defaults(func=command_post)

    comments_parser = subparsers.add_parser("comments", help="Fetch comments for a post.")
    add_post_target_arguments(comments_parser)
    comments_parser.add_argument("--page", type=int, default=1, help="Comment page to fetch.")
    comments_parser.add_argument("--page-size", type=int, default=20, help="Comments per page.")
    comments_parser.add_argument("--all-pages", action="store_true", help="Fetch every comment page.")
    comments_parser.add_argument("--json", action="store_true", help="Print JSON output.")
    comments_parser.set_defaults(func=command_comments)

    return parser


def add_post_target_arguments(parser):
    target_group = parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument("--page-url", help="Canonical page URL from RSS.")
    target_group.add_argument("--slug", help="Post slug under /posts/.")


def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except urllib.error.HTTPError as error:
        sys.stderr.write(f"HTTP error {error.code}: {error.reason}\n")
        return 1
    except urllib.error.URLError as error:
        sys.stderr.write(f"Network error: {error.reason}\n")
        return 1
    except (ET.ParseError, ValueError, json.JSONDecodeError) as error:
        sys.stderr.write(f"Failed to read blog data: {error}\n")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
