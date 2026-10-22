---
schema: forkmesh-discussion-v1
number: 1
title: Explore Renovate for dependency updates
category: Ideas
status: open
createdAt: 1792704184605
author: YpN9eh6-B3zwn-kIgvInmuJ3rXCyfjNrjktHBQLT0pY
authorName: donnieblt
type: open
id: open-web-1792704184605-37ip7n
ts: 1792704184605
sig: dA2AmWs8-FUy_SYijzphEOhrShu5pqxYn74L5qfG8a_Xg99GvGk_A0hm12ecUX6Ifla4z5LInWg2NOC2xOV2Bw
---

BLT is one repo with nearly 60 `blt-*` projects. Their dependencies are spread across npm (≈20 `package.json`), Python (≈22 `pyproject.toml`/`requirements*.txt`, with pip, uv and poetry lockfiles), Flutter (4 `pubspec.yaml`), Rust (`blt-cli`), `wrangler` versions in each Worker, and pinned CDN script versions in our HTML (`cdnjs`, `jsdelivr`, `unpkg`). Today nobody updates these on a schedule. I'd like to try [Renovate](https://docs.renovatebot.com/) and want to hear what you think first.

**What it would do**
- Read every manifest and lockfile in the monorepo and open pull requests that bump them, with release notes in the PR.
- Cover the CDN pins in HTML with a regex manager (`<script src=".../lib@1.2.3/...">`), plus `wrangler` and `compatibility_date` if we want.
- Keep a "Dependency Dashboard" issue that lists pending and held-back updates.

**Running it on our forge**
- Renovate runs self-hosted, as a scheduled workflow in `.forkmesh/` on our own runner. No GitHub app.
- The catch: Renovate talks to its supported platforms (GitHub, GitLab, Gitea, Forgejo, Bitbucket, Azure…) through their APIs. ForkMesh doesn't expose a Gitea/Forgejo-compatible API: pull requests are signed events on the `forkmesh/pulls` branch. So Renovate can't open our PRs out of the box.
- Options: (a) run Renovate's experimental `local` platform in the workflow as a lookup and report job, and post the result to the dashboard issue; (b) have a small script after Renovate push one branch per group and open the PR through ForkMesh; (c) add the minimal Gitea-style endpoints Renovate needs to ForkMesh (bigger, but useful beyond BLT).
- The runner is small (1 CPU, 1 GB, shared with the site), so it should run off-peak, once a week, with a cache cap.

**Keeping the PR count low**
- One weekly run (for example Monday early UTC) and at most ~5 open Renovate PRs at a time.
- Grouping: all non-major npm updates in one PR, all non-major Python in one, Flutter in one, CDN pins in one, `wrangler` across every Worker in one. Majors get their own PR, one per package.
- Lockfile maintenance monthly.

**Automerge policy (proposal)**
- Patch updates (and dev-only minors) merge on their own once `scripts/ci/test.sh` passes for every folder they touch.
- Minor and major updates, and anything touching auth, crypto or the Worker runtime, wait for a human approval.
- A new package version has to be a few days old (`minimumReleaseAge: 3 days`) before Renovate proposes it, to dodge bad releases and supply-chain surprises.

**Open questions**
1. Which option above for opening PRs: report-only first, a push script, or Gitea-compatible endpoints in ForkMesh?
2. Is weekly the right pace, and is ~5 open PRs the right cap?
3. Are we comfortable with patch automerge, given that CI only covers folders that have tests?
4. Should CDN pins in HTML be in scope, or should we first move them to a few shared includes?
5. Who wants to own the config and review the first few batches?

Replies welcome below. If it sounds good, I'll start with a report-only run so we can see the volume before anything opens PRs.
