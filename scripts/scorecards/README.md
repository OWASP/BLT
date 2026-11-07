# Profile scorecards

Every person with an account on [git.owaspblt.org](https://git.owaspblt.org) who has done something in BLT
gets a small, encouraging scorecard on their profile page: an overall score, five area bars, a few
strengths, some room to grow and one next step.

- **Generator:** `scripts/scorecards/generate.py` writes `.forkmesh/scorecards/<account>.json`.
- **Inputs (all public):** commits and projects from `.forkmesh/contributors/contributors.json`, issues,
  comments and votes from `.forkmesh/issues/`, pulls, reviews and pull comments from the `forkmesh/pulls`
  ledger branch, and bio/links from `/api/accounts/<name>`.
- **Scoring:** the five areas (Code, Collaboration, Community, Breadth, Momentum) and the overall score are
  computed the same way for everyone in `score_areas`. Anyone who showed up starts at 20.
- **Words:** the AI writes only the headline, strengths, room to grow and next step, from those numbers.
  Claude when `ANTHROPIC_API_KEY` is set (`SCORECARD_MODEL`, default `claude-haiku-5-5`), Workers AI when
  `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` are set, and friendly built-in text otherwise.
- **Display:** the forge reads the files through its `scorecards` instance setting
  (`{"repository": "owasp-blt/BLT", "ref": "main", "dir": ".forkmesh/scorecards"}`).

## Updating everyone

The `Refresh profile scorecards` workflow (`.forkmesh/scorecards.yml`) runs on the 1st and 15th of each
month. Run it from the Actions tab to update now. It rewrites a card only when its numbers changed or it
is more than 30 days old (`SCORECARD_REFRESH_DAYS`).

Locally:

```bash
set -a; . ~/.config/blt/cloudflare.env; set +a
python3 scripts/scorecards/generate.py --limit 3 --dry-run   # preview three cards
python3 scripts/scorecards/generate.py --only somebody        # rewrite one card
python3 scripts/scorecards/generate.py --force                # rewrite every card
```
