# Open GitLab merge requests: review and plan

On 2026-10-19 there were 40 open merge requests in gitlab.com/owasp-blt (17 projects). Each one was read in full
(description, discussion, diff), test-applied to its monorepo folder, and tested with and without the change where
the toolchain was available. Nothing was posted to GitLab.

**Totals:** 12 merge, 13 merge with changes, 15 close.

## How we land them

- A merged MR is applied as a patch into its folder and committed with the MR author as the git author. A
  `Co-Authored-By` trailer goes in when we change it. "Merge with changes" means we apply the trimmed or adjusted
  version described in the table, and say what we changed in the commit message.
- After it lands, the MR gets a comment linking the commit on git.owaspblt.org, and is then closed (GitLab can't
  merge into the monorepo).
- Each closed MR gets the comment suggested below, which points to git.owaspblt.org/BLT.

## Plan

1. **Security and production bugs first**
   - blt-jobs !6: `javascript:` URLs in contributor links.
   - blt-api !17: every CORS preflight answered 500, which broke signup and signin.
   - blt (`blt-core`) !3: the Docker build is broken on bullseye.
   - blt-university !17: the live site still serves deleted courses and repo files.
2. **blt-toasty, in this order:** !34, !35 (only the zero-width part), !37, !36 (without `shadow_pipeline.py`),
   !32 (apply D1 migration 0010 first), !30 (trimmed). !29 can go anytime.
3. **blt-mcp / blt-cli, in this order:** !10 (with the `q` fix), !12 (without stripping `__`), !13, !14. Then !11,
   trimmed to the three tautological tests.
4. **blt-jobs, in this order:** !6, !4, !5. The header line merges as `overflow-x-clip` plus !4's dark classes.
5. **The rest**
   - blt-hackathons !5 (keep the original ranks);
   - blt-design !4;
   - blt-next !2 (re-applied on the current footer);
   - blt-safecloak !10;
   - blt-action !1 (only the `require.main` guard);
   - blt-netguardian !36 (icons regenerated from `logo.png`);
   - blt-preflight !11 (keep a re-exporting `schema.py`, LF line endings).
6. **In-house follow-ups found during the review**
   - blt-gsoc: add `contributors`, `blog` and `certificates` to its deploy copy list (credit !6's author).
   - blt-safecloak: relabel the 11 stale "GitHub" links "Source code".
   - blt-next: a duplicate source link and "License on GitLab".
   - blt-core README: `cd BLT/blt-core`.
   - blt-toasty: the second PII scan should quarantine an event, not only log it.
7. **Close the other 15 with their comments.** Invite blt-toasty !33 back as a pull request on the forge; it's the
   one change that wires triage up again.


---

## GitLab MR triage (batch c), 2026-10-19

| ref | title | author | verdict | applies? | tests | reason | needed changes / merge order |
|---|---|---|---|---|---|---|---|
| blt-hackathons!5 | feat: add advanced hackathon search filters | nishatkhanam (nishat30) | MERGE WITH CHANGES | `git apply` fails, `patch -F3` applies all 13 hunks (main.js gained `renderSlackActivity`) | PASS (baseline PASS) | Useful client-side search over leaderboards, projects and sponsors; it escapes output and was reworked to free-text search at a maintainer's request. Bug: filtered leaderboards renumber from 1, so any user you search for shows as rank 1 with a gold trophy. | Rebase on the current main.js. Store each entry's rank before filtering and render that rank, for both leaderboards. Merge only this one of !5/!6/!7. |
| blt-hackathons!6 | Improve event card text contrast | nishatkhanam | CLOSE | fuzz-applies | PASS | It bundles the old dropdown version of !5. The CSS makes cards dark and text white in both themes, so the featured card gets white text on its white light-mode surface. Dark mode already remaps `text-gray-900/600` (blt-theme.css ~1435). | - |
| blt-hackathons!7 | Harden hackathon config validation and sanitize event metadata | nishatkhanam | CLOSE | No: 3/11 config hunks reject (gitlab→forkmesh block) | FAIL (config.js syntax error after partial apply; baseline PASS) | Written against the deleted GitLab provider. It strips every doc comment from the config, defaults `organizationUrl` to gitlab.com and wraps the config in a function that the text-editing scripts (`create-hackathon.mjs`, `process-sponsor.mjs`, `parse_hackathons_config.js`) don't expect. It also contains stale !5 and !6. | - |
| blt-hackathons!8 | fix: update gsoc 2027 warmup hackathon timeline dates | ananya-in-tech | CLOSE | fuzz-applies (1 hunk) | PASS | It moves the warm-up to 2026-09-21 → 2027-03-01. The real event starts 1 Nov 2026, and the config's own rules text says Nov 01, 2026 – May 09, 2027, so the current config (2026-11-01 → 2027-05-09) is right. No description; sent from a fork's `main`. | - |
| blt-jobs!4 | Fix Dark Mode UI Inconsistencies | nishatkhanam | MERGE | yes, clean | PASS (19/19 node + 5 py; baseline same) | Real dark-mode fixes for the header, logo text, hamburger bars and mobile Find Talent button: 5 class-only edits, reformatting noise removed after review. | Order: !6 → !4 → !5 |
| blt-jobs!5 | Fix: Hide Default Browser Scrollbar | nishatkhanam | MERGE WITH CHANGES | clean alone; conflicts with !4 on the `<header>` class line | PASS (with !4+!6) | Switching `overflow-x-hidden`→`overflow-x-clip` on html, body, header and hero fixes the nested double scrollbar. The thin scrollbar was the reviewer's request, and the reviewer approved it. | Merge last. Resolve the header line as `overflow-x-clip … bg-white/90 dark:border-white/10 dark:bg-gray-950/90`. |
| blt-jobs!6 | fix: validate contributor URLs before rendering | nishatkhanam | MERGE | yes, clean (also on top of !4) | PASS | Security hardening: `added_by_url` and `profileUrl` were only HTML-escaped before going into `href`, so `javascript:` URLs got through. Uses the existing `Sanitize.safeUrl` (http/https only), which is already loaded before these scripts. | Merge first. The fallback `safeUrl` copies are redundant but harmless. |
| blt-docs!4 | docs: add screenshot and media guidelines | Preetam-77 | CLOSE | yes, clean | n/a (no tests.tsv entry) | The committed `media.md` is only 10 lines and ends inside an unclosed code fence. Almost everything the description lists is missing. | - |
| blt-docs!5 | docs: add reusable MkDocs components #9 | Preetam-77 | CLOSE | yes, clean | n/a | Mostly repeats the Admonitions and Cards sections of `writing-docs.md`. It adds gitlab.com repo links and GitLab icons, a `status-badge` class that doesn't exist, and a broken `!!! note` block. | - |
| blt-design!4 | Add copy-to-clipboard for code blocks and color swatches | nishatkhanam | MERGE | yes, clean | n/a (no tests; `node --check` OK) | Small, self-contained progressive enhancement with an aria-live status. Static labels only, so no XSS; the Tailwind CDN builds the new classes at runtime. | Optional: drop one trailing space (copy-code.js:59). |
| blt-design-contest!1 | feat: store contest entries and assets in the repository | Vanshika2720 | CLOSE | No: build_showcase.py and README hunks reject; `.gitlab-ci.yml` no longer exists | n/a | Superseded by the redesign: submissions are now forge issues, pages live in KV, "nothing is committed", and the Worker can't serve newly committed static files. `--offline` and the GitLab archive already exist. | - |
| blt-gsoc!6 | fix(deploy): move contributor pages under public asset root | preetham (project bot account) | CLOSE (fix the bug in-house) | No: `.gitlab-ci.yml` gone; `.gitignore` fuzz only | n/a | Real bug that still exists: `gsoc2026.html` links to `contributors/2026/netguardian/`, but the blt-gsoc build in `scripts/deploy/projects.tsv` runs `rm -rf public` and never copies `contributors/`, so the link 404s. Moving the files into `public/` would let the deploy delete them. | Follow-up: add `contributors` (and `blog`, `certificates`) to the blt-gsoc cp list in `scripts/deploy/projects.tsv`, credit preetham. |
| blt-next!2 | fix: replace GitHub footer link with X | Preetam-77 | MERGE WITH CHANGES | No: footer since rewritten to git.owaspblt.org | PASS (adapted change; lint+tests+py_compile) | The footer still has two identical source-code icon links, one with a GitHub icon. Using one of them for the official X account (the URL blt-core uses) is a real cleanup. | Re-apply to the current footer: change the `fa-github` link (src/index.html ~251) to `https://x.com/OWASP_BLT` / `fa-x-twitter` / `aria-label="X"` and keep the code-branch source link. |

## Notes

**Merge order and dependencies**
- blt-hackathons: !5, !6 and !7 are a stack from one branch family, and !6/!7 contain the *old dropdown* version of !5. Merge only !5 (rebased and with the rank fix) and close !6/!7. !8 is independent and closed.
- blt-jobs: !6 → !4 → !5. !6 applies on top of either. !4 and !5 both edit the `<header>` class, so whichever goes second needs the one-line resolution above.
- blt-gsoc: the real fix is in `scripts/deploy/projects.tsv`, outside the folder, so commit it separately with the contributor credited.

**Security**
- blt-jobs!6 closes a `javascript:` href hole in two places on index.html. `job.js` and `app.js` already use `safeUrl`.
- blt-hackathons!5 escapes user data. No secrets or malicious code in any MR. blt-design-contest!1 would `urlopen` arbitrary image URLs from issue bodies in CI (SSRF-ish), one more reason to close it.
- Side finding: blt-next `src/index.html` still has duplicate "Source Code" list items (lines 225/226) and a "License on GitLab" label (line 244) that the 2026-10-19 wording pass missed.

**Suggested closing comments**
- **blt-hackathons!6**: "Thanks for this. The dashboard now has proper light/dark tokens, and dark mode already remaps these text colours. Forcing dark cards in light mode would give white-on-white text on the featured card. BLT has moved to git.owaspblt.org/BLT. If contrast is still off in a specific theme, please open a pull request there that uses the theme tokens."
- **blt-hackathons!7**: "Thanks for the validation work. Since this was opened, the config moved from the GitLab provider to the forkmesh source on git.owaspblt.org, and the issue-driven scripts edit this file as text, so the wrapper and the comment removal no longer fit. The search part continues in !5. BLT now lives at git.owaspblt.org/BLT, where a smaller validation pull request (e.g. in `parse_hackathons_config.js`) is welcome."
- **blt-hackathons!8**: "Thanks! The GSoC 2027 warm-up starts on 1 Nov 2026 and runs to 9 May 2027, as the rules text says, so the current dates are correct. The project has moved to git.owaspblt.org/BLT; please open a pull request there for future changes."
- **blt-docs!4**: "Thanks for picking up #10. The committed `media.md` only has the first few lines and stops inside an open code block. BLT docs now live at git.owaspblt.org/BLT (`blt-docs/`). A complete version would be welcome there as a pull request, ideally as a section of `writing-docs.md`."
- **blt-docs!5**: "Thanks! Most of these patterns are already in `developer-guide/writing-docs.md`, and the examples link to gitlab.com, which is closing. The project moved to git.owaspblt.org/BLT. If you want to add the route-card or screenshot guidance, please open a pull request there that extends `writing-docs.md`."
- **blt-design-contest!1**: "Thanks for the careful work (path confinement, atomic writes, tests). Contest submissions have since moved to git.owaspblt.org issues, and the showcase pages are built into Workers KV with nothing committed, so storing entries in the repo no longer fits. The project is now at git.owaspblt.org/BLT (`blt-design-contest/`); pull requests are welcome there."
- **blt-gsoc!6**: "Thanks for tracking down the 404. In the monorepo the deploy rebuilds `public/` from scratch, so we're fixing it by adding `contributors/` to the deploy copy list, with credit to you. BLT now lives at git.owaspblt.org/BLT; please send future pull requests there."

---

## GitLab MR triage, batch b (15 MRs)

Base: monorepo `e40c791c2c`. Diffs from `gitlab.com/<project>/-/merge_requests/<iid>.diff`; discussions from `.../discussions.json` (the API `/notes` answers 401 anonymously). blt-mcp's `blt-cli/` paths apply at the monorepo root, because blt-cli is a top-level folder now. Rust was tested with `cargo test` (installed). Docker and Flutter were not available.

| ref | title | author | verdict | applies? | tests | reason | needed changes / merge order |
|---|---|---|---|---|---|---|---|
| blt-mcp!10 | fix: add confirmation before vulnerability submission | Preetam-77 | MERGE WITH CHANGES | yes (root, blt-cli/) | blt-cli 18/18 before and after; fmt and clippy clean | A useful safety prompt before an irreversible submit (closes #15). The CodeRabbit finding is still open: the global `q` handler in `input.rs` closes every non-text overlay before the `SubmitConfirm` arm runs, so `q` drops the draft (pressing `s` resets the form). | Exclude `SubmitConfirm` from the global `q`-closes-overlay check. Best: run !13's required-field check before opening the dialog. Order: 10, 12, 13, 14 (all four apply together with 3-way and give 22/22 passing tests). |
| blt-mcp!11 | test: remove redundant and tautological integration tests | Nachiket_R | MERGE WITH CHANGES | yes (`--directory=blt-mcp`) | blt-mcp 32 passed, 27 with the patch | Three of the removed tests only assert `"result" in r or "error" in r`. `test_tool_schemas` is not tautological: it pins the required fields of about 15 tools. `test_capability_negotiation` checks real behaviour. | Drop only `test_resource_read`, `test_resource_read_parameterized` and `test_tool_call`; keep `test_tool_schemas` and `test_capability_negotiation`. |
| blt-mcp!12 | fix(tui): strip markdown from Vision AI output | Saurabhyadav0 | MERGE WITH CHANGES | yes | 19/19 | A real bug: with `**TITLE:**` the title never parsed and the raw markdown went into the form. | Don't remove `__` globally: it mangles dunder identifiers that are common in vulnerability reports (`__proto__` becomes `proto`). Strip only `**`, or `__` around whole words. |
| blt-mcp!13 | fix(tui): block submission when Title, URL or Description is empty | Saurabhyadav0 | MERGE | yes | 19/19 | Stops a 400 from the API and the loss of the typed draft; small, unit-tested helper. | After !10 (or have !10 call the check before opening the dialog). |
| blt-mcp!14 | feat(tui): move the cursor with Left/Right in submit form fields | Saurabhyadav0 | MERGE | yes | 20/20; all four combined 22/22 | A real usability fix, done well: char-safe for multibyte text, cursor tied to its field, and seven copy-pasted display blocks reduced to one helper. | Last in the order. |
| blt-mcp!15 | ci: stop caching .cargo/bin and .cargo/git/db | Saurabhyadav0 | CLOSE | no (`.gitlab-ci.yml` gone) | n/a | `blt-mcp/.gitlab-ci.yml` was deleted (`f7733a40ae`); CI is forge workflows now, and no workflow caches these paths. | n/a |
| blt!2 | docs: fix broken clone URL in README and CONTRIBUTING | himaneeshmishra | CLOSE | no | n/a | Superseded: both files already clone `https://git.owaspblt.org/BLT.git`, and the MR's target is a gitlab.com URL that is being retired. | (Separately: `blt-core/README.md` line 101 says `cd BLT` where it should say `cd BLT/blt-core`; maintainers can fix that.) |
| blt!3 | fix(docker): move base images to Debian bookworm | Saurabhyadav0 | MERGE | yes (`--directory=blt-core`) | Docker unavailable (no socket permission). All six renamed packages confirmed on packages.debian.org/bookworm. | Fixes a broken `docker build`: the bullseye-security 404s. The rename list is correct, and pinning `-bookworm` avoids silently moving to trixie. | none |
| blt-api!17 | fix: pass CORS headers as sequence in OPTIONS preflight | yashspidey | MERGE | yes | 412 passed before, 413 after; the new test fails on the old code | A production bug: every browser preflight got a 500 (error 1101), which broke signup and signin. A one-line fix in the same pattern `homepage.py` already uses. | none |
| blt-action!1 | fix: make linked issue extraction testable | Preetam-77 | MERGE WITH CHANGES | no (conflict) | rebased version: 35 passing before and after | Half is already in the monorepo: `817e28277d` exports the function. The other half is still useful: `run()` still fires when the tests `require()` the module. | Rebase to just `if (require.main === module) { run(); }`, keeping `module.exports = { run, extractLinkedIssuesFromPRBody }`. Checked: the ncc bundle keeps the guard true for `dist/index.js`. |
| blt-autopatch!2 | Feature/blt autopatch worker foundation | nishatkhanam | CLOSE | no (README and index.html conflict; junk binary file) | its own 8 tests pass when run on their own | A skeleton with no patch logic. Merged, it would change the live static site's `wrangler.toml` to need D1 and four queues that don't exist (placeholder D1 id), so the deploy breaks. It adds an unauthenticated `POST /api/patch-requests` that queues any payload, a consumer that retries and dead-letters every message (Preetam's open review comment), gitlab.com links, the GitLab README template text, and a stray binary `wrangler-init-help.txt`. | n/a |
| blt-safecloak!10 | Move Legal Basis and Quick Templates to the top (#4) | Preetam-77 | MERGE | yes | 174 passed before and after; same 18 ids, balanced markup | Closes issue #4. Pure markup move, approved by saviodsouza8a ("Lgtm"). | Merge before anyone fixes the safecloak footer wording (both touch `consent.html`). |
| blt-safecloak!11 | fix: update GitHub references to GitLab | Preetam-77 | CLOSE | no | n/a | Obsolete: the links already point at git.owaspblt.org, and "GitLab" is the wrong label now. The stale "GitHub" labels it found are real, though (index 4, notes 2, video-chat 2, consent 2, video-room 1): the forge-wording sweep `7958bcd8f1` missed safecloak. | Maintainers: relabel these "Source code" in-tree. |
| blt-netguardian!36 | fix(client): use NetGuardian icon for desktop app | Vanshika2720 | MERGE WITH CHANGES | no as a patch (binary data not in the diff; files fetched from the fork 87606655 @ `ee585ae1`) | Flutter not installed | Replacing the default Flutter icon on macOS and Windows is real (#1). But it uses the OWASP wasp from `public/assets/img/logo.png`, and the project logo is now the shield `blt-netguardian/logo.png` (`882bc7ee81`). | Regenerate the 7 PNGs and the `.ico` from `blt-netguardian/logo.png`, keeping the author. Optionally also `client/web/icons`. |
| blt-university!17 | fix(ci): build the site in a clean directory and validate its output | Vanshika2720 | MERGE WITH CHANGES | no (`.gitlab-ci.yml` gone; README and public/ conflicts) | 141 Jest passed with the change; validator: 14 problems on current `public/`, 0 after the deletions; 5 unit tests OK | A real live problem: `public/` (served as is) still publishes 3 deleted courses plus repo files (package.json, tests/, scripts/, wrangler.toml…). | Drop the `.gitlab-ci.yml` hunk; `git rm` the 21 stale `public/` paths; keep `scripts/validate_site_output.py` and its tests; rewrite the README hunk against the current "Site build" bullet (build to `_site`, then replace `public/`, then run the validator). Optionally add the validator to the forge CI. |

## Notes

**Dependencies and order.** blt-mcp: 10 (with the fix), then 12, 13, 14. They all touch `blt-cli/src/app.rs` and `input.rs`; applied in that order with 3-way, they are clean and 22/22 tests pass. !10 and !13 work together, but the required-field check should run before the dialog opens. Apply safecloak!10 before any in-tree footer relabel. Every patch except the blt-cli ones needs `--directory=<folder>`.

**Security.** Nothing malicious, and no secrets. blt-autopatch!2 exposes an unauthenticated queue-write endpoint and sets `workers_dev = true`, which is one more reason to close it. blt-api!17 restores auth availability; it doesn't weaken anything: the CORS headers are the existing ones.

## Closing comments

- **blt-mcp!15:** Thanks for tracking down those cache warnings! The GitLab pipeline no longer exists: gitlab.com/owasp-blt is closing, `.gitlab-ci.yml` has been removed, and CI runs as forge workflows in the monorepo at https://git.owaspblt.org/BLT. If you spot CI noise there, please open a pull request against the `blt-mcp` or `blt-cli` folder.
- **blt!2:** Thank you for catching the broken clone URL. gitlab.com/owasp-blt is being closed, and BLT now lives in the monorepo at https://git.owaspblt.org/BLT. The README and CONTRIBUTING already clone from there, so this change is superseded. Further doc fixes are welcome as a pull request against `blt-core/`.
- **blt-autopatch!2:** Thanks for the careful groundwork and for addressing the review. We're closing this for now. As it stands, it would switch the live autopatch.owaspblt.org static site to a Worker that needs D1 and queues that aren't provisioned. It would also accept unauthenticated requests whose messages are only retried and dead-lettered. The project has moved to https://git.owaspblt.org/BLT. Please open a pull request against `blt-autopatch/` once there is a working consumer and authentication on the endpoint, leaving out `wrangler-init-help.txt` and the template README text.
- **blt-safecloak!11:** Thanks, you're right that the "GitHub" labels are stale! gitlab.com/owasp-blt is closing, and the links now point at the monorepo, https://git.owaspblt.org/BLT. So the right label is "Source code" rather than GitLab, and we'll relabel them there. Future fixes are welcome as pull requests against `blt-safecloak/`.

---

## Triage: blt-toasty !29–!37, blt-preflight !10–!12

Baselines in a detached worktree at e40c791c2c:
- blt-toasty: 462 passed, ruff and black clean.
- blt-preflight: 98 passed. The `pf` binary must be on PATH; without it, `test_pf_check_command` fails.

Each patch was built from `git diff merge-base..refs/merge-requests/N/head`.

| ref | title | author | verdict | applies? | tests | reason | needed changes / merge order |
|---|---|---|---|---|---|---|---|
| blt-toasty!34 | fix(redaction): write PII audit rows in a single D1 batch | Saurabhyadav0 | MERGE | yes, clean | 463 passed (+1); ruff and black clean | Real fix: N D1 round-trips become one `db.batch()`, using the same pattern as duplicate_detector. The rows written are identical and the tests were adjusted correctly. | Merge first. |
| blt-toasty!35 | perf(redaction): speed up zero-width stripping, drop unused second scan | Saurabhyadav0 | MERGE WITH CHANGES | yes, clean | 462 passed; the new `_strip_zero_width` matched the old one on 100k fuzzed inputs | Part 1 (zero-width fast path) is a correct, verified speed-up. Part 2 removes the Markdown secondary scan, which is the only signal for real leaks: `**bob**@example.com` and `10.0.**0**.1` are missed by the primary scan and caught only by the secondary. | Keep only the `src/native_recognizers.py` hunk and drop the `redaction_engine.py` changes. Separately, make the secondary scan fail closed (quarantine) instead of only logging. Merge after !34. |
| blt-toasty!37 | perf(duplicates): run borderline LLM adjudications concurrently | Saurabhyadav0 | MERGE | yes, clean | 463 passed (+1) | Same selection and output, with the 3 LLM calls run through `asyncio.gather`. `adjudicate_duplicate` never raises (it returns safe defaults), so gather is safe. | After !34/!35. |
| blt-toasty!36 | perf(embedding): reuse the vector from index_report for duplicate search | Saurabhyadav0 | MERGE WITH CHANGES | no: `src/shadow_pipeline.py` was deleted in 3a6831f721; the other files apply | 488 passed with the stack below | A clean API improvement (`index_report` returns the vector, `find_duplicates(embedding=)`). Its only caller was shadow mode, which is gone, so it has no effect until a pipeline is wired. | Drop the `shadow_pipeline.py` hunk. After !37. |
| blt-toasty!32 | feat(summarizer): extract repro steps with explicit missing/insufficient state | Vanshika2720 | MERGE | yes, clean | 486 passed (+24) | A well-designed fix for #55: grounded steps, an explicit `repro_status`, a non-dict JSON guard and good tests. | Apply migration `0010_repro_status.sql` to D1 before deploying, because `_store_summary` inserts the new column. Merge before !30. |
| blt-toasty!30 | fix(summarizer): soft-truncate limits, fallback repro extraction, safe token counts | ikgrscorporation | MERGE WITH CHANGES | yes, clean alone; conflicts with !32 in the repro hunk | 462 passed; black fails | The core fix is real: `validate_triage_output` rejects >150/400-word output before `_truncate_to_word_limit` can trim it, so trimming is dead code. The repro fallback is superseded by !32, and the rest is whitespace churn plus a dropped final newline. | Keep only the removal of the two word-limit errors (plus the token-count line) and add a regression test. Drop the comment realignment, docstring churn and repro fallback. Apply after !32. |
| blt-toasty!29 | feat(auth): global AuthGate and access denied screen | Ojaswa072 | MERGE | yes, clean | 462 passed; `vite build` OK | Visitors without a token now see "Access Denied" instead of the fake demo data the pages fall back to. The backend stays the real gate. | Independent of the others. Optional nit: the `useAuth` comment says it does not decode the JWT, but `getToken` now does. |
| blt-toasty!31 | feat(notifications): modular Slack webhook integration | ikgrscorporation | CLOSE | yes, clean | 462 passed (no new tests); black fails | Not wired to anything. It uses `urllib.request` and `os.getenv`, which do not work in Python Workers. It also bundles all of !30, the maintainer asked for that to be removed, and the request was ignored. | none |
| blt-toasty!33 | feat(webhook): decouple ingress from triage via Cloudflare Queues | Vanshika2720 | CLOSE (invite resubmit) | no: `src/worker.py` conflicts; also conflicts with !35 in `redaction_engine.py` and collides with !32 on migration 0010 | 546 passed after a manual merge, but only because `fetch_issue_text` is mocked | Serious, well-tested work (leases, DLQ, fencing). As written it would fail every job: `triage_pipeline.fetch_issue_text` imports `gitlab_client`, deleted in 3a6831f721 (`ModuleNotFoundError`), and it reads issue text from the GitLab API. The queue bindings sit only under `env.*` while toasty deploys its top-level config, so the webhook would return 500 for lack of `WEBHOOK_QUEUE`. | A resubmission needs: an issue-text source without a GitLab API call (for example, redact at ingress and enqueue the redacted text), migrations renumbered after !32, top-level wrangler bindings and Queues provisioned, and a rebase on the current worker.py and on !34–!37. |
| blt-preflight!11 | fixing minor issues in schema.py and adding a test file | saviodsouza8a | MERGE WITH CHANGES | yes, clean (files are CRLF) | collection error: `tests/test_root_schema.py` raises `No module named 'schema'`; 98 others pass | Real fix: `advisory/generator.py` and `schema_validator.py` import `advisory_engine.rag.schema`, which does not exist in the monorepo. The root `schema.py` is not valid Python (`HIGHT` typo, syntax errors). The MR moves it into `rag/schema.py` and fixes it, but its new test imports the root module that the same MR deletes. | Keep a two-line root `schema.py` that re-exports from `advisory_engine.rag.schema`, or point the test at the rag module. Convert CRLF to LF and add final newlines. Note that generator.py then fails on `rag.prompt_template`, which is a separate gap. |
| blt-preflight!12 | fix: wiring retrieve_command to a real retriever | saviodsouza8a | CLOSE | yes, clean (CRLF) | collection error: `test_week1.py` raises `No module named 'advisory_engine.retriever'` | Incomplete. The CLI imports `Retriever` (the class is `RAGRetriever`) and `advisory_engine.rag.advisory_generator`, which does not exist, so `pf retrieve` and `pf advise` would both crash. It deletes the existing `retriever.py` that tests import. | none |
| blt-preflight!10 | Adding gitlab integration and wiring it into blt_preflight.py | saviodsouza8a | CLOSE | yes, clean (CRLF) | 98 passed (no tests for the new code) | Adds a gitlab.com Notes-API poster on CI variables after GitLab was retired, duplicating the existing `advisory_engine/gitlab/merge_request.py`. It also rewrites `cmd_github` to call `GitHubIntegration().run()`, which does not exist, breaking `pf github`. | none |

## Notes

**Merge order (blt-toasty):** !34, then !35 (native_recognizers hunk only), !37, !36 (without shadow_pipeline), !32, !30 (trimmed). !29 is independent. I tested !34 + !35 (full) + !37 + !36 (without shadow) + !32 + !29 stacked: 488 passed, ruff and black clean. **blt-preflight:** only !11; it does not overlap with the others.

**Dependencies and conflicts:**
- !30 and !32 conflict in the summarizer repro post-processing; !32 wins.
- !31 contains all of !30.
- !32 and !33 both add `migrations/0010_*`.
- !33 conflicts with !35 (redaction_engine) and with the current worker.py.
- After shadow mode was removed, nothing in production calls redact → summarize → index → detect_duplicates. Webhooks only store a `pending` row. !33 is the only MR that wires that pipeline, so its value is real even though it is not mergeable as it stands.

**Security:**
- No secrets or malicious code found. The only key-like strings are test fixtures (`glpat-SECRET` used in a leak-check assertion).
- Do not accept !35's removal of the secondary scan. It hides a real fail-open: Markdown-split emails and IPs pass redaction unredacted. Worth an issue: quarantine when the plain-text scan finds entities the original-text scan missed.
- !31 would interpolate an unredacted issue title into Slack mrkdwn.

**Suggested closing comments:**
- **toasty!31:** Thanks, Izhan. We're closing this: the notifier isn't wired into the pipeline, `urllib.request` and `os.getenv` don't work in Cloudflare Python Workers (use `fetch` and `env`), and the branch still carries the !30 commit. The project has moved to git.owaspblt.org/BLT (folder `blt-toasty`). You're welcome to open a pull request there with a Workers-native, tested notifier wired after triage.
- **toasty!33:** Thank you, Vanshika. This is careful work. We can't merge it as is because the monorepo has since removed `gitlab_client` (so `fetch_issue_text` would fail every job), the queue bindings need to live in the top-level wrangler config, and migration 0010 is taken by !32. The project now lives at git.owaspblt.org/BLT (folder `blt-toasty`). Please re-open it there as a pull request, rebased, with the issue text taken from the webhook (for example, redacted at ingress) instead of the GitLab API. We'd like to land it.
- **preflight!10:** Thanks, Savio. GitLab hosting has been retired and `blt-preflight` already has a GitLab MR adapter in `advisory_engine/gitlab/`. This change also makes `pf github` call a `run()` method that `GitHubIntegration` doesn't have. The project has moved to git.owaspblt.org/BLT (folder `blt-preflight`). If you want CI output, please open a pull request there that extends the existing adapter, with tests.
- **preflight!12:** Thanks, Savio. The CLI here imports `Retriever` and `advisory_engine.rag.advisory_generator`, which aren't in the branch, so `pf retrieve` and `pf advise` would crash, and removing `advisory_engine/retriever.py` breaks `test_week1.py`. The project has moved to git.owaspblt.org/BLT (folder `blt-preflight`). Please re-open it there as a complete pull request with all files and a test for `retrieve_command`.
