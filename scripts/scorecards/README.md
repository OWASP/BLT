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

## From Claude Code or the desktop app

Run `/scorecards` in a BLT session (the skill is in `.claude/skills/scorecards/`). Claude shows the current
cards, writes the words for the cards that are due (or for the people you name) itself, imports them,
shows you the result and, after you say yes, commits and pushes to the forge. `/scorecards --show` only
lists the cards; `/scorecards --workers-ai` lets Workers AI write them instead.

Under the hood that is `--export` (the instructions and numbers of the cards due) and `--import` (the
words, as `{"<login>": {"headline", "strengths", "grow", "next_step"}}`); imported cards are credited to
"Claude Code". Any agent can use the same two steps.

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
python3 scripts/scorecards/generate.py --export due.json      # data of the cards due, for an agent
python3 scripts/scorecards/generate.py --import words.json    # cards with an agent's words
```
