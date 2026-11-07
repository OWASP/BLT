---
title: "OWASP BLT launches Tomato 1000 and rebuilds the OWASP Project Matrix around finding work"
slug: "tomato-1000-and-the-owasp-project-matrix"
date: "2026-11-07"
updated: "2026-11-07"
author: "Donnie Brown"
author_url: "https://git.owaspblt.org/@donnieblt"
author_avatar: "/images/authors/donnieblt.webp"
description: "Tomato 1000, a drive to get 1,000 open-source developers to $1,000 a month; a rebuilt OWASP Project Matrix covering every owasp.org project; Project Sweep; mentors on any forge issue; profile scorecards; and ten community pull requests merged."
tags: ["release", "owasp", "opensource", "funding"]
cover: "/images/tomato-1000-and-the-owasp-project-matrix/tomato1000.jpg"
---
OWASP BLT (Bug Logging Tool) today shipped a set of updates aimed at a long-standing open-source problem: helping the people who build security tools get paid, and helping new contributors find something to work on. The headline is **Tomato 1000**, a drive to get 1,000 open-source developers to $1,000 a month in sponsorship. Alongside it come a rebuilt OWASP Project Matrix covering every owasp.org project, a tool to help the OWASP Project working group retire finished projects, mentors on request from any issue on the BLT forge, and Slack alerts that now reach OWASP projects hosted outside the OWASP GitHub organization.

## Tomato 1000: 1,000 developers, $1,000 a month

BLT Tomato, the project's funding directory, now has a [Tomato 1000 page](https://tomato.owaspblt.org/1000). It shows a 1,000-seat board, a random developer spotlight, and searchable developer cards, each with a Sponsor button. The drive is open to every open-source developer, not only OWASP's. Anyone on GitHub Sponsors can join by adding their GitHub username to a list in the repository. The top contributors of OWASP repositories and of BLT are included from the start. Each card shows a developer's OWASP projects, or for everyone else their most-starred repositories. Share buttons and link previews make it easy to spread the word with **#tomato1000**.

The rest of the funding directory changed too:

- **Clearer guidance on OWASP donations.** The owasp.org donation form no longer has a project field, so those gifts now fund the Foundation in general. The page explains that donors who want a gift credited to a project can still contact the Foundation, and that GitHub Sponsors pays the developer directly.
- **Every way to fund a project.** Each project's FUNDING.yml is now shown as real links (GitHub Sponsors, Patreon, Open Collective, Ko-fi and more), along with its top contributors who accept GitHub sponsorship.
- **BLT practices what it preaches.** The BLT monorepo now has its own FUNDING.yml listing its top sponsorable contributors.
- **A refreshed design**, with dark mode and a phone layout.

![The BLT Tomato funding directory: a note on owasp.org donations, a Tomato 1000 banner, and totals for projects with a FUNDING.yml](/images/tomato-1000-and-the-owasp-project-matrix/tomato.jpg)

## OWASP Project Matrix: every project, and a faster way to find work

[projects.owaspblt.org](https://projects.owaspblt.org) has been rebuilt:

- **Complete coverage.** The matrix now draws on owasp.org's own project inventory: 343 projects, up from 173. It also adds 40 active OWASP project repositories that the inventory doesn't link to yet.
- **"Find something to work on."** The home page opens with live counts of good first issues, help wanted, pull requests waiting for a review, quick reviews and pull requests from new contributors, each a click away.
- **A card for every project.** Each project has a consistent card showing its level, its languages, stars, open issues and PRs, recent commit activity, and top contributors. Search, filters and sorting run in the browser.
- **Every open issue and pull request in one place.** New tables list everything open across OWASP's repositories, with quick views such as needs review, quick reviews, new contributors and approved but not merged.
- **More accurate numbers.** Contributor, issue and PR counts are now exact. Before, they were capped at GitHub's first page of results.
- **Link previews.** Links to the matrix now show a title, description and preview image in Slack and on social media.

![The OWASP Project Matrix home page: project and activity totals, then five "Find something to work on" tiles](/images/tomato-1000-and-the-owasp-project-matrix/projects.jpg)

![Project cards with language bars, stars, open issues and pull requests, activity over 30 and 90 days, and top contributors](/images/tomato-1000-and-the-owasp-project-matrix/projects-cards.jpg)

![Open pull requests across every OWASP repository, with quick views for needs review, quick reviews and new contributors](/images/tomato-1000-and-the-owasp-project-matrix/open-work.jpg)

## Project Sweep: helping the working group tidy the catalogue

OWASP Bumper has a new [**/sweep**](https://bumper.owaspblt.org/sweep) page that lists projects that look finished, for the OWASP Project working group to review. Each project gets a 0–100 score built from evidence a reviewer can check: years since the last commit or release, archived or missing repositories, unanswered reminder issues, and pull requests left unreviewed. Recent commits, releases, maintainer replies and large followings count against archiving. Flagship and Production projects are always held for human review. The working group can export the list as a Markdown checklist or a CSV.

![Project Sweep: suggested archives with a score, the last activity and the evidence for each project](/images/tomato-1000-and-the-owasp-project-matrix/sweep.jpg)

## A mentor for any issue on the forge

The BLT mentor pool now works on [git.owaspblt.org](https://git.owaspblt.org). Comment `/mentor` on any forge issue and a mentor from the [pool](https://pool.owaspblt.org) is matched to you: one whose specialties fit first, then whoever has the most room. `/rematch` and `/unmentor` work too. Mentors can now sign up with their forge account, and every contributor gets a personal link to refer new mentors.

![The BLT Pool home page: comment /mentor on any git.owaspblt.org issue to be matched with one of 31 mentors](/images/tomato-1000-and-the-owasp-project-matrix/pool.jpg)

## Profile scorecards on the forge

Every profile on git.owaspblt.org now has a scorecard. It scores public BLT activity (code, collaboration, community, breadth and momentum) the same way for everyone, and adds a short written note on strengths, room to grow and one next step. The notes are written by AI and are refreshed twice a month.

![A profile scorecard on git.owaspblt.org: an overall score, a level, and five areas](/images/tomato-1000-and-the-owasp-project-matrix/scorecard.jpg)

## Slack alerts that cover all of OWASP

The new-repository and new-issue alerts for OWASP's Slack had gone quiet. Both now run on Cloudflare Workers and post every hour. The new-issue alert also covers the 63 owasp.org projects whose code lives outside the OWASP GitHub organization, such as Juice Shop, DefectDojo, Core Rule Set and WebGoat. In a test against the last 23 hours, 15 of the 38 new issues came from those outside repositories. ZAP, which has its own channels, is excluded.

BLT Sammich, BLT's Slack app, now shows real workspace names and channel and member counts on its public page. A new dashboard for each workspace shows its top channels, newcomer trends, peak joining hours and more, built only from public channels and aggregate data.

![The BLT Sammich dashboard for the OWASP Slack workspace: members, channels, recent joins and the top 10 channels](/images/tomato-1000-and-the-owasp-project-matrix/sammich.jpg)

## Ten community pull requests merged

Thank you to everyone whose work landed in the last day:

- [**hrinkar01**](https://git.owaspblt.org/@hrinkar01): security dependency upgrades for blt-legacy, and a fixed, tested router for blt-dash.
- [**hiralmodi14**](https://git.owaspblt.org/@hiralmodi14): cleanup and cross-platform test fixes for blt-pages.
- [**Salava-marquina**](https://git.owaspblt.org/@Salava-marquina): stronger redaction tests for blt-netguardian.
- **Nachiket Roy**: canonical JSON and HMAC signing for zero-trust findings in blt-cli.
- **Navodit Sahai**: a fix for day-of-week ranges in blt-cron's schedule parser, with edge-case tests.
- **Arnav**: blt-leaf's Wrangler launcher now works on Windows.
- **Namrata**: new tests for blt-monitor, including sharding and authentication checks.
- **nishat30**: centered icons and tidier empty states on the blt-pages leaderboard.
- [**vanshika2720**](https://git.owaspblt.org/@vanshika2720): blt-mcp's agent guide now matches its tool definitions.

## More from today

- **A new home for the blog.** This post is the first on [blog.owaspblt.org](https://blog.owaspblt.org). The 32 posts from [dev.to/owaspblt](https://dev.to/owaspblt), back to 2025, are now here too, with their images and their authors' bylines, and each links back to where it was first published. Anyone can write a post: add a Markdown file to `blt-blog/posts/` and open a pull request.
- **Automated dependency updates.** A weekly Renovate job now proposes grouped dependency updates as pull requests on the BLT forge, with at most five open at a time. Its first run opened five: npm and Python minor updates, Wrangler, the next major Wrangler, and `@actions/core`.
- **A directory of GSoC dashboards.** MY-GSOC-TOOL now has a [directory](https://gsoc-tool.owaspblt.org/directory) of every live dashboard built from it, with each student's project, pull requests, issues and updates.
- **Smarter issue pages.** Every issue on the forge now carries a project tag that links to that project's live site, across all 48 BLT sites.
- **AI-assisted pull request review.** A new review workflow checks open forge pull requests for security, relevance and robustness before a maintainer signs off.
- **Hacktoberfest wrap-up.** With Hacktoberfest over, its banners and references were retired across the BLT sites.

## About OWASP BLT

OWASP BLT is an open-source OWASP project that helps people find, report and fix bugs and security issues, and that builds tools to support the open-source security community. All of BLT's projects live in a single monorepo at [git.owaspblt.org](https://git.owaspblt.org), mirrored to [github.com/OWASP/BLT](https://github.com/OWASP/BLT). Contributors of every experience level are welcome.

**Links**

- Tomato 1000: https://tomato.owaspblt.org/1000
- OWASP Project Matrix: https://projects.owaspblt.org
- Project Sweep: https://bumper.owaspblt.org/sweep
- Mentor pool: https://pool.owaspblt.org
- Source: https://git.owaspblt.org
