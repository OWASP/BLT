---
type: comment
id: comment-web-1792862962-11zgbpq
author: xP8W3X91Iym28V8rRGc5g9kJmYCRBUiCSI1sKA7ZQvM
authorName: ojaswa
ts: 1792862962
sig: OXGpLI9k4YRurh3mlatvWeMqOOZo_tUdg7fpdTA4_YvcYp78pOuEzfsMUlrof5cZlSoM_-f0j5SuIck7oJbIBQ
---

Hey @DonnieBLT ,

Automating this across the monorepo is a huge win- managing ~60 projects manually is definitely not sustainable.

A few quick thoughts:

1. **Option (a) first, then (b):** Running report-only first is definitely the safest move so we can see the sheer volume without cluttering PR branches. After that, a lightweight script that commits signed events to `forkmesh/pulls` makes the most sense—writing custom Gitea API endpoints for ForkMesh feels like unnecessary overhead right now.
2. **Automerge guardrail:** The 3-day hold is great against supply-chain surprises. For patch automerge, I'd say only let it automerge if that specific folder has an active, passing CI test suite. If a subproject has no tests, it should still wait for a quick human check.
3. **CDN pins:** Probably best to leave CDN regexes out of Phase 1. Let's get the standard package manifests and lockfiles stable first.
4. **Runner memory:** With 1 GB of RAM on a shared runner, resolving lockfiles across ~40 manifests might spike memory, so setting a concurrency limit and scheduling it off-peak will be important.

I'd be happy to help test the config and review those first batches of PRs, especially on the Python and Cloudflare Worker sides! Starting with the dry-run report sounds like the way to go.
