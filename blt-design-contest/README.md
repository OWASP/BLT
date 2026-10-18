# BLT Design Contest

**Live Site:** [https://contest.owaspblt.org/](https://contest.owaspblt.org/)<br>
**Source Code:** [https://git.owaspblt.org/BLT/tree/main/blt-design-contest](https://git.owaspblt.org/BLT/tree/main/blt-design-contest)

Community design showcase for [OWASP BLT](https://owasp.org/www-project-blt/).


## How it works

1. **Submit**: open a [new issue on git.owaspblt.org](https://git.owaspblt.org/BLT/issues/new), title it `[blt-design-contest] <contest prefix> <name>` (for example `[blt-design-contest] [Logo] Shield mark`) and paste the contest's body from [`issue-templates/`](issue-templates/README.md). The forge has no issue templates, so the showcase links to these files. A maintainer adds the `blt-design-contest` and contest labels (`logo-submission`, ...); the title prefix is enough until then.
2. **Vote**: signed-in users press **Vote** on a submission's issue. A comment that is just `+1` also counts once per account. Maintainers add the `winner` label to a winning submission.
3. **Showcase**: `.forkmesh/blt-design-contest--build-showcase.yml` runs `scripts/refresh-kv.sh` when a contest issue is opened, edited, labelled, unlabelled, closed or reopened, once a day at 07:47 UTC (votes raise no issue event), and on pushes to `scripts/` or `data/`. It builds the pages with `scripts/build_showcase.py` and writes the pages that changed to the Worker's KV namespace. Nothing is committed. The Worker (`worker/index.js`) serves `/`, `/index.html`, `/show-all-entries.html` and `/<contest>.html` from KV, falling back to the copies committed in `public/`.

Pages show the vote counts from their last build; there is no browser call to any issue API.

### GitLab archive

The contest ran on gitlab.com/owasp-blt until that group closed. `data/gitlab-archive.json` keeps those 45 submissions with their final GitLab thumbs-up counts, reactions, last comment and the one winner. They were read from the showcase pages committed at `729f99853f`, the last build before GitLab returned no issues. The pages show them next to new submissions, marked **GitLab archive**, without links to the dead GitLab issues. Their images are the vendored files in `public/assets/entries/`.

## Stack

| Layer | Technology |
|---|---|
| HTML | Pure HTML5 |
| CSS | Tailwind CSS (CDN) |
| Icons | Font Awesome 6 (CDN) |
| Build | Python 3 (`scripts/build_showcase.py`, reads `scripts/forkmesh/ledger.py`) |
| Refresh | ForkMesh Actions + Workers KV (`scripts/refresh-kv.sh`) |
| Hosting | Cloudflare Workers Static Assets (`public/`) + `worker/index.js` |

## Local development

```bash
# Generate all showcase HTML pages into public/ (reads git.owaspblt.org anonymously)
python3 scripts/build_showcase.py
# Archive only, or into another directory
python3 scripts/build_showcase.py --offline --out /tmp/contest

# What the workflow would write to KV (no Cloudflare credentials needed)
KV_NAMESPACE_ID=dry KV_PUT_DRY_RUN=1 scripts/refresh-kv.sh

# Tests (from the repository root)
scripts/ci/test.sh blt-design-contest

# Serve locally
python3 -m http.server 8080 --directory public
```

`scripts/vendor_github_assets.py` copies GitHub attachment media into `public/assets/entries/`. It is no longer run by the workflow, because pages in KV cannot add new static files. Run it by hand and commit the files if a submission's GitHub-hosted image must be kept.

## Cloudflare deployment

`scripts/deploy.sh blt-design-contest` (or `npx wrangler deploy`) deploys `public/` and the Worker. The KV namespace `blt-design-contest-data` (binding `DATA`) is created by `scripts/worker-data/create-kv.sh`, which writes its id into `wrangler.toml`.

## Brand

Follows the [BLT Official Style Guide](https://www.figma.com/file/2lfEZKvqcb4WxRPYEwJqeE/OWASP-BLT):

- Primary: `#E10101`
- Dark base: `#111827` · Dark surface: `#1F2937`
- Neutral border: `#E5E5E5`
