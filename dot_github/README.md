# dot_github

**Source Code:** [https://git.owaspblt.org/BLT/dot_github](https://git.owaspblt.org/BLT/dot_github)

The organization profile for OWASP BLT, formerly the `.github` repository.

- [`profile/README.md`](profile/README.md) is the organization profile page: an introduction, the latest blog posts
  and the all-time contributor wall.
- [`scripts/update_blog_posts.py`](scripts/update_blog_posts.py) fills in the latest two posts from
  [dev.to/owaspblt](https://dev.to/owaspblt).
- [`scripts/update_contributors.py`](scripts/update_contributors.py) fills in the contributor sections.

Both scripts edit `profile/README.md` between their `<!-- ...-START -->` and `<!-- ...-END -->` markers. Run them from
this folder.
