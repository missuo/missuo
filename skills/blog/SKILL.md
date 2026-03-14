---
name: blog
description: Read Vincent Young's blog feed and per-post comments. Use when the user asks to list recent posts from missuo.me, inspect RSS metadata or content for a specific post, derive the canonical post URL from a slug, or fetch and summarize comments from talk.owo.nz.
---

# Blog

This skill reads:

- RSS feed: `https://missuo.me/index.xml`
- Comments API: `https://talk.owo.nz/v1/comments`

Use the bundled script instead of rebuilding these requests by hand.

## Workflow

1. List or inspect posts from RSS first so you use the exact canonical post URL.
2. Fetch comments with that URL as `pageKey`.
3. When a post has many comments, fetch all pages before summarizing the discussion.

## Commands

```bash
# List recent posts
python3 skills/blog/scripts/blog.py posts --limit 10 --json

# Inspect one post by slug
python3 skills/blog/scripts/blog.py post --slug openclaw-for-developer --json --include-content

# Fetch the first page of comments by slug
python3 skills/blog/scripts/blog.py comments --slug openclaw-for-developer --json

# Fetch all comment pages by canonical URL
python3 skills/blog/scripts/blog.py comments \
  --page-url https://missuo.me/posts/openclaw-for-developer/ \
  --all-pages \
  --json
```

## Notes

- For normal posts, `--slug <slug>` maps to `https://missuo.me/posts/<slug>/`.
- Prefer a URL copied from RSS over reconstructing it manually.
- The comments API expects the canonical page URL, including the trailing slash when the post URL has one.
- `posts` keeps output lean by default; add `--include-description` or `--include-content` when you need the HTML excerpt or full body.
- Comment threading is represented by `parentId`, `rootId`, and `depth`.
