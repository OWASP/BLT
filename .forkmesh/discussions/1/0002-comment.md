---
type: comment
id: comment-web-1792784230-ew8x9k
author: Cu6HYOAI_KXF_0n4il24bXIniH5dBGJ0ELffhPIkLLQ
authorName: vanshika2720
ts: 1792784230
sig: osN3lkHD5VainQsieawvpZ8V8_rdkfpatnuPqR-EJxWcS1zvnXiApnqQbk3ryp9Ru1aCAG1iuCoWMUUtIm5OBw
---

@DonnieBLT Thanks for proposing this, Donnie! We looked into the repository and found a few things worth addressing before enabling automated dependency updates.

The biggest concern is that a green CI result doesn't always mean every affected project was tested. `scripts/ci/test.sh` can report `SKIPPED` when a toolchain is missing while still exiting successfully. The runner also lacks Rust and Flutter, and some projects don't have entries in `tests.tsv`. We should first introduce per-project statuses (`pass`, `fail`, `skipped`, and `untested`) and prevent automerge whenever an affected project hasn't actually been tested.

There's also a ForkMesh integration constraint: Renovate's experimental `local` platform is intended for lookup/dry-run use and doesn't create branches or PRs. We could start with a read-only, report-only pilot and investigate a supported ForkMesh API for opening or updating PRs as a separate step.

We should also exclude CDN updates from the initial pilot, since changing a library version without updating its SRI hash can break resource loading.

This seems like a good way to measure the update volume and identify CI gaps before giving automation permission to modify the repository. One thing we should verify early is whether bot-created PRs reliably trigger CI in ForkMesh.
