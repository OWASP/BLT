---
title: "Eleven Projects, One Remarkable Team: Celebrating OWASP BLT’s GSoC 2026"
published: false
description: "Meet the contributors and mentors who turned OWASP BLT’s 2026 summer into working security tools, learning platforms, and edge-native infrastructure."
tags: opensource, security, gsoc, webdev
cover_image: https://gsoc.owaspblt.org/blog/gsoc-2026/assets/owasp-blt-gsoc-2026-hero.png
canonical_url: https://gsoc.owaspblt.org/gsoc2026.html
---

Open source is often measured in commits. The better measure is what those commits make possible.

During GSoC 2026, the OWASP BLT community worked across **11 projects**: four Google Summer of Code projects and seven paid internship projects. The team built zero-trust security pipelines, practical learning experiences, privacy tools, AI-assisted contributor workflows, edge-native services, and the infrastructure needed to run them in production.

By the end of the summer, the portfolio was not a collection of slide decks. Nine projects had live applications or documentation sites, Hackerhouse had a new production domain and healthy database-backed deployment, and the Cloudflare-backed projects had current deployments and completed migrations.

This is the team behind that progress.

## The GSoC projects

### Preetham Poojari — BLT-NetGuardian

Preetham helped turn NetGuardian into a serious zero-trust ingestion and triage pipeline. The system verifies signed finding envelopes, applies replay protection and role-based access, stores metadata in D1, and supports CVE-aware review. The result is a working bridge between distributed security research and accountable triage.

The repository records **90 commits by Preetham during the coding period**, and the deployed service now has scheduled maintenance running through BLT Monitor without consuming another Cloudflare cron slot.

Mentors: **Jisan** and **CarlaV**.

![BLT-NetGuardian live site](https://gsoc.owaspblt.org/blog/gsoc-2026/screenshots/01-netguardian.png)

[Try NetGuardian](https://netguardian.owaspblt.org/) · [Source code](https://gitlab.com/owasp-blt/blt-netguardian)

### Sakshee Suman — BLT-University

Sakshee advanced BLT-University as a hands-on security learning platform built around a clear loop: identify a vulnerability, explain it, and fix it. The project connects practical labs with real vulnerability insights and makes security education something learners can actively do.

The local history shows **40 coding-period commits across Sakshee’s author identities**. The result is live, browsable, and designed to make the next generation of security contributors more capable from day one.

Mentors: **BishalDas** and **Chigorin.1337**.

![BLT-University live site](https://gsoc.owaspblt.org/blog/gsoc-2026/screenshots/02-university.png)

[Explore BLT-University](https://university.owaspblt.org/) · [Source code](https://gitlab.com/owasp-blt/blt-university)

### Md Kaif Ansari — BLT-Next

Md Kaif worked on the broadest architectural challenge in the programme: moving BLT from a tightly coupled Django application toward modular, edge-first services. BLT-Next demonstrates the direction with a static frontend, Cloudflare Workers, D1-backed services, and independently deployable capabilities.

That work reaches beyond one repository. The programme roster credits Md Kaif across BLT-Next and supporting BLT services including API, docs, hackathons, jobs, monitor, newsletter, and Zero. The success here is architectural: a clearer path to a capable platform with dramatically lower hosting overhead.

Mentors: **DonnieBLT** and **Rinkit Adhana**.

![BLT-Next live site](https://gsoc.owaspblt.org/blog/gsoc-2026/screenshots/03-next.png)

[Visit BLT-Next](https://next.owaspblt.org/) · [Source code](https://gitlab.com/owasp-blt/blt-next)

### Ananya — BLT-Vanish

Ananya evolved BLT-Vanish toward a universal identity shield: phishing detection, credential hygiene, suspicious-login correlation, encrypted workflows, and explainable risk scoring across web and Flutter clients.

With **59 coding-period commits** in the web repository, Ananya moved the project from an idea toward a cohesive privacy and personal-security experience. The production web app is now served from its dedicated OWASP BLT subdomain.

Mentors: **Ankitsinghsisodya** and **Ramansh**.

![BLT-Vanish live site](https://gsoc.owaspblt.org/blog/gsoc-2026/screenshots/04-vanish.png)

[Try BLT-Vanish](https://vanish.owaspblt.org/) · [Source code](https://gitlab.com/owasp-blt/blt-vanish)

## The paid internship projects

### Savio D’souza — BLT-Preflight

Savio built an ambitious local-first contribution assistant spanning the editor, pre-commit checks, and CI. Its hybrid classifier and OWASP-documentation retrieval layer are designed to catch risk while a contributor can still act on the feedback—not after a review cycle has already stalled.

Savio authored **28 coding-period commits** across his recorded identities. Preflight is deployed as a live interactive experience, with the repository retaining a second optional API target for future provisioning.

Volunteer mentor: **Raj Gupta**.

![BLT-Preflight live site](https://gsoc.owaspblt.org/blog/gsoc-2026/screenshots/05-preflight.png)

[Open BLT-Preflight](https://preflight.owaspblt.org/) · [Source code](https://gitlab.com/owasp-blt/blt-preflight)

### Ojaswa — BLT-Toasty

Ojaswa’s Toasty tackles one of vulnerability management’s hardest operational problems: turning raw reports into safe, useful, structured intelligence. It combines fail-closed PII redaction, AI summarization, duplicate detection, webhook ingestion, durable state, and MCP export.

The coding period includes **74 commits by Ojaswa**, ending with a polished architecture showcase and quick-start experience. Toasty’s Worker, state migrations, and public site are deployed and tested.

![BLT-Toasty live site](https://gsoc.owaspblt.org/blog/gsoc-2026/screenshots/06-toasty.png)

[Meet Toasty](https://toasty.owaspblt.org/) · [Source code](https://gitlab.com/owasp-blt/blt-toasty)

### Nachiket Roy — BLT-MCP

Nachiket made Model Context Protocol practical for the BLT contributor ecosystem. BLT-MCP gives tools and agents a consistent way to discover capabilities and work with project context instead of relying on brittle, one-off automation.

With **88 coding-period commits**, Nachiket delivered one of the summer’s most active repositories. The live service makes the work immediately discoverable to both contributors and tool builders.

![BLT-MCP live site](https://gsoc.owaspblt.org/blog/gsoc-2026/screenshots/07-mcp.png)

[Explore BLT-MCP](https://mcp.owaspblt.org/) · [Source code](https://gitlab.com/owasp-blt/blt-mcp)

### Karuna Rapolu — BLT-SafeCloak

Karuna’s SafeCloak work focused on privacy guardrails and safer user workflows. The project gives users a security-focused place to reason about exposure and make better privacy decisions without turning the experience into an expert-only tool.

The summer established a deployed, tested baseline and a public experience on its own subdomain—an important foundation for deeper privacy automation.

![BLT-SafeCloak live site](https://gsoc.owaspblt.org/blog/gsoc-2026/screenshots/08-safecloak.png)

[Visit SafeCloak](https://safecloak.owaspblt.org/) · [Source code](https://gitlab.com/owasp-blt/blt-safecloak)

### Rudra Pratap Singh — BLT-Hackerhouse

Rudra helped build Hackerhouse as a collaboration pipeline for hands-on offensive and defensive security work. The application now has a real production stack: a Python Worker, Durable Objects, a D1 database, queue-backed events, applied migrations, and regression-tested health reporting.

Rudra authored **48 coding-period commits**. Hackerhouse also reached a particularly visible milestone this summer: a healthy production deployment at its new dedicated domain.

![BLT-Hackerhouse live site](https://gsoc.owaspblt.org/blog/gsoc-2026/screenshots/09-hackerhouse.png)

[Visit Hackerhouse](https://hackerhouse.owaspblt.org/) · [Source code](https://gitlab.com/owasp-blt/blt-hackerhouse)

### Sidd190 — BLT-Autopatch

Sidd190 took on automated patch generation and validation: an idea with enormous potential to shorten the distance between discovering a vulnerability and safely remediating it.

Autopatch is the portfolio’s earliest-stage project. Its success this summer was establishing the project home and a clear direction for the work ahead. Calling that out honestly matters: healthy open source celebrates shipped systems and the people laying foundations for the next contributors.

![BLT-Autopatch source project](https://gsoc.owaspblt.org/blog/gsoc-2026/screenshots/10-autopatch.png)

[Source code](https://gitlab.com/owasp-blt/blt-autopatch)

### Jayant — BLT-MAYO

Jayant developed BLT-MAYO as a shell dangerous-execution analyzer—a practical quality and safety tool for BLT engineering workflows. The repository now contains its Python package, tests, documentation, configuration example, and a focused analyzer design.

Jayant authored **three coding-period commits across his recorded identities**, progressing the project from initial structure into working analysis and test foundations.

![BLT-MAYO source project](https://gsoc.owaspblt.org/blog/gsoc-2026/screenshots/11-mayo.png)

[Source code](https://gitlab.com/owasp-blt/blt-mayo)

## What the team achieved together

The individual stories are impressive. The shared outcome is bigger:

- **11 contributors** received ownership of meaningful, security-focused projects.
- **Nine projects** now have live applications or documentation experiences.
- Cloudflare-backed releases were brought current and smoke-tested.
- D1 migrations were applied and verified with no pending migration queues.
- Hackerhouse gained a production database, queue, Durable Objects, and its own domain.
- NetGuardian’s maintenance schedule was integrated without exceeding the account’s five-cron limit.
- Project discovery now leads with live experiences and clearly identifies GitLab as the source-code home.

Most importantly, the team produced multiple on-ramps into open-source security: learn with University, protect identities with Vanish, review findings with NetGuardian, improve reports with Toasty, guide contributions with Preflight, and build new automation through MCP.

## From the contributors

The strongest account of a programme comes from the people who built it. Continue with these contributor stories, demos, and community reflections:

- [My GSoC Journey with OWASP BLT](https://dev.to/owaspblt/my-gsoc-journey-with-owasp-blt-4lm8)
- [Building an AI-Powered Security TUI with Rust and MCP](https://dev.to/owaspblt/building-an-ai-powered-security-tui-with-rust-and-mcp-oj9)
- [GSoC 2026 contributor reflection on LinkedIn](https://lnkd.in/p/gQkmQWXM)
- [GSoC 2026 project progress shared on LinkedIn](https://www.linkedin.com/feed/update/urn:li:activity:7497988651306430465/)
- [GSoC 2026 project showcase on LinkedIn](https://lnkd.in/p/dQgYPZfM)

## Thank you

Thank you to every contributor, GSoC mentor, volunteer mentor, reviewer, tester, and community member who made room for this work to grow. Great mentoring is invisible in a diff, but visible everywhere in a project that becomes clearer, safer, and more welcoming over time.

Explore the [full OWASP BLT GSoC 2026 team and project page](https://gsoc.owaspblt.org/gsoc2026.html), visit the [live project directory](https://waypoint.owaspblt.org/), and find the complete [source-code organization on GitLab](https://gitlab.com/owasp-blt).

The summer is over. The work—and the community behind it—is just getting started.
