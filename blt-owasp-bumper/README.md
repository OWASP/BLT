# OWASP Bumper

**Live site:** [https://bumper.owaspblt.org/](https://bumper.owaspblt.org/)<br>
**Source code:** [https://git.owaspblt.org/BLT/tree/blt-owasp-bumper](https://git.owaspblt.org/BLT/tree/blt-owasp-bumper)

<p align="center"><img src="logo.png" alt="blt-owasp-bumper logo" width="160" height="160"></p>

Find idle repositories in the [OWASP GitHub organization](https://github.com/OWASP) and nudge their
maintainers with a reminder issue, one at a time or in batches.

## Using it

- **Best to bump** is the default order. Each repository gets a score: importance × staleness ×
  noise. Importance counts stars, forks, open issues and PRs, OWASP projects and their level, and
  stars that keep arriving after the last push. Staleness grows with the years since the last push,
  and pushes by bots don't count as upkeep. Noise pushes down repos a reminder won't help: forks,
  templates, empty repos, ones whose description says they moved or are defunct (archive those
  instead), `-old` / `-backup` copies, near-duplicate siblings (`crackme-a1`, `-a2`…; only the
  best-scoring one leads), repos with an open reminder issue, and ones you've bumped. The clearest
  cases are collapsed as *Low-signal* under the table, with a count of each kind. Each row shows its
  score and up to two reason chips; hover for the full breakdown. The plain orders (most idle,
  stars, issues, name, age) are in the sort menu and the column headers.
- **Open reminders**: open issues titled "Repository Activity Reminder" (Bumper's earlier title) or
  "still maintained" show as a 🔔 #N link on their row, and the *Reminder issue* filter lists
  them. A reminder opened less than a year ago replaces the Bump button with a link to it, so
  nobody files a second one.
- **Filter** by activity (last push: active < 1 year, idle 1, 2, 3 or 5+ years), type (project,
  chapter, other), language, creation year, archived, and whether you've bumped it already. Search
  covers names, descriptions and topics. The summary tiles are activity presets with live counts.
  The filters are in the URL, so a filtered view can be shared.
- **Select** rows with the checkboxes (shift-click ticks a range), the header box, or
  *Select all N matching*. The bar at the bottom shows the count, including selected rows the
  current filters hide.
- **Open issue forms** opens GitHub's new-issue form on each selected repository, prefilled with a
  short reminder that names the last push. You review and submit each one, signed in as yourself.
  Browsers allow only a few tabs per click, so forms open 10 at a time: click again for the next
  batch. If the browser blocks them, the page says so and keeps the rest selected; allow pop-ups
  for the site and click again.
- **Copy checklist** copies the selection as a Markdown task list with each repository's reminder
  link, for a tracking issue or for working through later.

Repositories you've opened a form for are remembered in your browser (`localStorage`) and marked
*Bumped*. Archived repositories and ones with issues turned off can't be bumped.

Why tabs and not the API: the repositories are OWASP's, on GitHub, and Bumper has no GitHub
credentials of its own. A prefilled form lets each reminder go out under the volunteer's own
account, after they've read it, with no token to store.

## How it works

| Piece | What it does |
| --- | --- |
| `generate_repo_list.py` | Fetches every repo in the org from the GitHub API and writes `public/data/repos.json` (standard library only). It also finds open reminder issues (two search queries). With `GITHUB_TOKEN` it also fetches 52-week activity, `index.md` front matter, open PRs and the last commit (about 4 requests per repo); without one, just the repo list (about 15 requests). |
| `public/index.html`, `public/app.js`, `public/bumper.js` | The static page. `bumper.js` holds the filtering, sorting and link logic (tested under Node); `app.js` draws the page. It uses the shared OWASP BLT bar (`blt-nav.js`) for the header and theme toggle. |
| `worker/index.js` | Serves `/data/repos.json` from Workers KV, falling back to the committed copy in `public/data/`. Everything else is static. |
| `scripts/refresh-kv.sh` | Regenerates the data and writes it to KV, unless it lists fewer than half as many repositories as before. Run daily by `.forkmesh/blt-owasp-bumper--generate-repo-list.yml` (monorepo root). |

## Development

```bash
python3 generate_repo_list.py                       # refresh public/data/repos.json (no token needed)
npx wrangler@4 dev --config wrangler.toml           # http://localhost:8787
node --test 'test/*.test.mjs'                       # tests (or scripts/ci/test.sh blt-owasp-bumper from the root)
```

Deploy from the monorepo root with `scripts/deploy.sh blt-owasp-bumper` (the Deploy workflow does
this when the folder changes).

## Contributing

Issues and pull requests go to the BLT forge: [issues](https://git.owaspblt.org/BLT/issues),
[pull requests](https://git.owaspblt.org/BLT/pulls). Part of [OWASP BLT](https://owaspblt.org/).

## License

MIT, see [LICENSE](LICENSE).
