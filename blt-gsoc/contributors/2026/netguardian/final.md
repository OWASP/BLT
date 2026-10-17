# From a Signed Finding to a Distributed Security Workflow: My GSoC 2026 Journey with OWASP BLT

**Google Summer of Code 2026 · OWASP Foundation · BLT-NetGuardian**  
**By Preetham Poojari**

When I started working on BLT-NetGuardian, I thought the hardest part would be writing the code.

It was not.

The harder part was understanding what the project genuinely needed, cutting through old ideas and stub features, accepting when my first interpretation was wrong, and turning a broad security proposal into one flow that could actually be run, tested, and demonstrated.

That is probably the biggest thing I am taking away from GSoC.

## Where I started

I was already contributing to OWASP BLT before GSoC, so I was familiar with the community and the way the project worked. NetGuardian was still a different kind of challenge. It touched security contracts, ingestion, storage, authentication, triage, a desktop client, deployment, and eventually distributed crawling.

The original goal was to build a trustworthy path for security findings:

```text
scanner/client → signed finding → secure storage → triage → BLT issue
```

The first few weeks were intentionally not glamorous. I defined the `ztr-finding-1` envelope, created the D1 schema, added canonical JSON signing, and wrote verification helpers. Findings were signed with HMAC-SHA256, tied to a body digest, and protected using timestamps and one-time nonces.

I learned very early that security work is mostly about refusing bad states. The happy path is easy. The real work is rejecting altered bodies, expired requests, replayed nonces, unknown keys, malformed ciphertext, and requests from the wrong organization—and returning an error that is useful instead of a mysterious 500.

There were also early review-driven changes that made the codebase less clever and more maintainable. I renamed and flattened modules, consolidated migrations, removed theory-heavy files that were not helping the implementation, and tightened the scope of individual merge requests. It was a good reminder that more files and more abstractions do not automatically mean better engineering.

## Building the trust and triage backbone

Once signed ingestion worked, I moved into org-scoped findings and the triage interface.

By the midterm, I had an end-to-end path where I could:

1. submit a signed finding;
2. store its evidence encrypted using AES-256-GCM;
3. open it in the triage UI;
4. decrypt and redact it on an authorized view;
5. record an access event;
6. update its status; and
7. convert it into a BLT issue without creating duplicates.

At that point, 186 tests were passing. More importantly, I could show the full flow live instead of explaining it with slides.

The triage UI became much more than a list. I added severity and status filters, risk-ranked sorting, evidence views, remediation guidance, responsible-disclosure hints from `security.txt`, CSV and PDF exports, GitHub OAuth with PKCE, verified events, and BLT-API conversion.

Some of the most useful bugs were the small ones. Severity was once sorted alphabetically, which put `medium` in the wrong place. Finding objects were being shaped in multiple parts of the backend and slowly drifting apart. The detail panel looked complete but did not scroll correctly when the evidence became long. None of these bugs sounds exciting in a proposal, but they are exactly the things that decide whether somebody can comfortably use the product.

## The point where the project changed

The biggest shift came when we started discussing discovery.

There were older documents in the repository describing autonomous certificate-transparency monitoring, blockchain scanners, GitHub discovery, WHOIS outreach, and other ambitious features. Some routes and UI surfaces existed, but much of that was sample or stub behavior. I had to stop treating those documents as proof that the product already did those things.

This was uncomfortable but necessary. I would rather finish GSoC with a smaller system that is real than a huge system whose best features only exist in a README.

Donnie pushed me to explain what was actually unique about NetGuardian. A one-time HTTP header scan was useful, but it was not enough. The stronger idea was continuous domain discovery from real page source: a client visits an authorized seed, extracts hosts from HTML, JavaScript, CSS, links and assets, scans them, and keeps expanding the queue.

That feedback changed the second half of my project.

I first built a local continuous crawler in the Flutter client. Then I made it always-on until the user pressed Stop. After that, I moved the queue into D1 so multiple clients could participate in the same crawl without repeatedly claiming the same domain.

The resulting flow became:

```text
submit seed
  → claim domain with a lease
  → fetch and scan on the user's machine
  → discover more hosts
  → submit them to the shared queue
  → complete or retry the job
  → claim the next domain
```

The Worker coordinates; it does not scan third-party sites. That boundary matters. It keeps network activity on the researcher-operated client, makes the actor visible, and avoids turning a hosted OWASP service into an unsolicited scanner.

The queue now handles normalization, deduplication, claim leases, heartbeats, completion, failure, retries, and expired claims. The client shows pending, in-progress, scanned, failed, and retry-required domains in a live grid.

## Making it usable instead of merely functional

The crawler worked, and then immediately created another problem: it worked too continuously.

The findings, operations log, and domain grid kept growing until the application felt like doomscrolling. New updates changed the page height while I was trying to reach the Stop button. My first attempt froze updates while the user scrolled, but that made the grid look dead even though the crawler was still active.

The better fix was simpler:

- keep Start and Stop pinned;
- cap the number of live rows shown;
- keep full totals separately;
- continuously update the visible state; and
- retain older findings for sending without rendering all of them.

I also fixed the same class of problem in triage, where the findings column had `overflow: auto` but its parent was not height-constrained, so the browser had nothing to scroll.

This part of the project taught me that “real-time” is not automatically good UX. A live interface still needs to let the user remain in control.

## Asking before looking deeper

Near the end, Donnie suggested one more flow: before taking a deeper look at a domain, help the researcher ask the site owner for permission.

I liked this addition because it fits the product's security model. NetGuardian should not only verify machines and payloads; it should make human authorization clearer too.

The client can now look for a contact in `security.txt`, `mailto:` links, and visible page text. If nothing useful is found, it can suggest addresses such as `security@domain` or `support@domain`.

It then prepares an email explaining that we are an open-source community trying to make the web safer and asks whether a further, non-destructive review would be welcome. The email contains a unique link where the owner can choose **Yes** or **No**. Choosing Yes requires accepting a short set of terms and records that response; choosing No records the decline.

NetGuardian prepares the email but does not silently send it. The researcher remains responsible for reviewing and sending the message.

## Deployment was its own project

Getting everything to work locally was only half the job.

Cloudflare's Python Workers runtime, D1 bindings, static assets, CORS, secrets, and deployment configuration introduced a completely different set of failures. At different points I dealt with:

- a Flutter window that looked open after its debug session had died;
- a client sending to a Worker that did not yet contain the new routes;
- “authentication is not configured” errors caused by the wrong auth gate;
- local servers that needed restarting before new routes existed;
- D1 migrations applied to the wrong environment;
- browser CORS behavior differing from the macOS client;
- a `requirements.txt` file preventing the Python Worker from publishing; and
- confusion between my staging Worker and the OWASP production configuration.

I eventually created separate staging deployment configuration, migration and smoke scripts, a local in-memory D1-compatible server, and a `--no-seed` mode so I could begin recordings with a genuinely empty system.

That resettable demo path saved me more than once.

## What I finished with

NetGuardian now has a working path across:

- HMAC-signed and replay-protected finding ingestion;
- AES-256-GCM encrypted evidence and redacted authorized views;
- org-scoped triage, status updates, audit events, CSV/PDF export, and BLT issue conversion;
- HTTP security-header detection and dynamic Semgrep findings;
- a Flutter producer with offline outbox, history, encryption, and triage deep links;
- distributed page-source domain discovery backed by a leased D1 queue;
- verified events and GitHub OAuth;
- remediation and responsible-disclosure guidance; and
- a site-owner permission request with contact discovery, email drafting, Yes/No, and terms.

The current pipeline has ten built-in finding categories—nine HTTP checks and one domain-discovery finding—while Semgrep rule IDs remain open-ended. The Worker exposes roughly thirty method-and-route contracts across ingestion, findings, evidence, authentication, events, crawling, outreach, exports, and health.

Those numbers are useful, but they are not what I am proudest of. I am proud that the main path is real. I can start with an empty database, run the client, discover and scan domains, sign findings, send them, open triage, and follow them through remediation or conversion.

## What was difficult

The most difficult part was not any one algorithm. It was maintaining a truthful understanding of the system while it changed.

I had to repeatedly ask:

- Is this feature real or only represented in a mockup?
- Is this request being made by the Worker or by the user's client?
- Does this work only in local development, or has the migration reached staging?
- Are we solving the mentor's actual concern, or only making the UI look busy?
- Can I demonstrate this from an empty state without manually hiding old data?

I also learned not to disappear into implementation for too long. Showing broken or incomplete work early was almost always better than polishing the wrong direction.

## Thank you

I am extremely grateful to my mentors, **Donnie, Carla, and Jisan**, for trusting me with this project.

Donnie kept pushing me to find the real product inside the proposal. His questions around continuous discovery, the role of the client, and asking site owners for permission changed NetGuardian in concrete ways.

Carla made me look harder at how we explain the system to somebody arriving for the first time. Her feedback around the landing page, documentation, and the site-owner/researcher access model exposed assumptions that were obvious to me only because I had been staring at the project every day.

Jisan's guidance and steady support throughout the program helped me keep moving through the less visible parts of the work—the revisions, integrations, and moments where the project needed patience more than another feature.

I appreciate that they did not simply approve everything I built. They challenged the framing, asked what was real, and made me defend the decisions. That made both the project and me better.

I am also grateful to the wider OWASP BLT community. I came into GSoC already knowing the community through my earlier contributions, but these months gave me a much deeper sense of ownership and responsibility. The connections I made are as important to me as the code.

## What I am taking forward

I started this project thinking mostly about secure ingestion. I am ending it thinking about the whole chain: who is allowed to scan, where the network request runs, how a finding proves its origin, who can decrypt it, how an analyst acts on it, and how a site owner can say yes or no.

There is still more that can be done. The permission flow can be connected more deeply to crawl eligibility. The queue can gain better observability and organization-level policy. The client can be packaged for more platforms. Real pilots will reveal assumptions that tests cannot.

I intend to keep contributing after GSoC.

This project gave me much more than a completed milestone. It taught me how to take feedback without treating it as a setback, how to reduce an ambitious idea into honest deliverables, and how much work exists between “the feature runs” and “another person can trust and use it.”

That is a journey I am genuinely grateful for.

---

## Links

- **GSoC 2026 work product page:** [index.html](index.html)
- **Project repository:** [https://git.owaspblt.org/BLT/BLT-NetGuardian](https://git.owaspblt.org/BLT/BLT-NetGuardian)
- **Final crawl synchronization MR:** [OWASP BLT-NetGuardian !34](https://gitlab.com/owasp-blt/blt-netguardian/-/merge_requests/34)
- **Quickstart:** [`docs/spec/quickstart.md`](https://git.owaspblt.org/BLT/BLT-NetGuardian/blob/main/docs/spec/quickstart.md)
- **Permission outreach:** [`docs/spec/permission-outreach.md`](https://git.owaspblt.org/BLT/BLT-NetGuardian/blob/main/docs/spec/permission-outreach.md)

