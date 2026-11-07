---
title: "OWASP BLT launches Tomato 1000 and rebuilds the OWASP Project Matrix around finding work"
slug: "tomato-1000-and-the-owasp-project-matrix"
date: "2026-11-07"
author: "Donnie Brown"
author_url: "https://git.owaspblt.org/@donnieblt"
author_avatar: "/images/authors/donnieblt.webp"
description: "Tomato 1000, a drive to get 1,000 open-source developers to $1,000 a month; a rebuilt OWASP Project Matrix covering all 343 owasp.org projects; Project Sweep; and Slack alerts that reach all of OWASP."
tags: ["release", "owasp", "opensource", "funding"]
---
OWASP BLT (Bug Logging Tool) today shipped a set of updates aimed at a long-standing open-source problem: helping the people who build security tools get paid, and helping new contributors find something to work on. The headline is **Tomato 1000**, a drive to get 1,000 open-source developers to $1,000 a month in sponsorship. Alongside it come a rebuilt OWASP Project Matrix covering every owasp.org project, a tool to help the OWASP Project working group retire finished projects, and Slack alerts that now reach OWASP projects hosted outside the OWASP GitHub organization.

## Tomato 1000: 1,000 developers, $1,000 a month

BLT Tomato, the project's funding directory, now has a [Tomato 1000 page](https://tomato.owaspblt.org/1000). It shows a 1,000-seat board, a random developer spotlight, and searchable developer cards, each with a Sponsor button. The drive is open to every open-source developer, not only OWASP's. Anyone on GitHub Sponsors can join by adding their GitHub username to a list in the repository. The top contributors of OWASP repositories and of BLT are included from the start. Each card shows a developer's OWASP projects, or for everyone else their most-starred repositories. Share buttons and link previews make it easy to spread the word with **#tomato1000**.

The rest of the funding directory changed too:

- **Clearer guidance on OWASP donations.** The owasp.org donation form no longer has a project field, so those gifts now fund the Foundation in general. The page explains that donors who want a gift credited to a project can still contact the Foundation, and that GitHub Sponsors pays the developer directly.
- **Every way to fund a project.** Each project's FUNDING.yml is now shown as real links (GitHub Sponsors, Patreon, Open Collective, Ko-fi and more), along with its top contributors who accept GitHub sponsorship.
- **BLT practices what it preaches.** The BLT monorepo now has its own FUNDING.yml listing its top sponsorable contributors.
- **A refreshed design**, with dark mode and a phone layout.

## OWASP Project Matrix: every project, and a faster way to find work

[projects.owaspblt.org](https://projects.owaspblt.org) has been rebuilt:

- **Complete coverage.** The matrix now draws on owasp.org's own project inventory: 343 projects, up from 173. It also adds 40 active OWASP project repositories that the inventory doesn't link to yet.
- **A card for every project.** Each project has a consistent card showing its level, main languages, stars, open issues and PRs, recent commit activity, and top contributors. Search, filters and sorting run in the browser.
- **"Find something to work on."** New views list open issues and pull requests across every OWASP repository: good first issues, help wanted, unassigned, PRs that need a review, quick reviews, and PRs from first-time contributors. Each view shows live counts.
- **More accurate numbers.** Contributor, issue and PR counts are now exact. Before, they were capped at GitHub's first page of results.

## Project Sweep: helping the working group tidy the catalogue

OWASP Bumper has a new [**/sweep**](https://bumper.owaspblt.org/sweep) page that lists projects that look finished, for the OWASP Project working group to review. Each project gets a 0–100 score built from evidence a reviewer can check: years since the last commit or release, archived or missing repositories, unanswered reminder issues, and pull requests left unreviewed. Recent commits, releases, maintainer replies and large followings count against archiving. Flagship and Production projects are always held for human review. The working group can export the list as a Markdown checklist or a CSV.

## Slack alerts that cover all of OWASP

The new-repository and new-issue alerts for OWASP's Slack had gone quiet. Both now run on Cloudflare Workers and post every hour. The new-issue alert also covers the 63 owasp.org projects whose code lives outside the OWASP GitHub organization, such as Juice Shop, DefectDojo, Core Rule Set and WebGoat. In a test against the last 23 hours, 15 of the 38 new issues came from those outside repositories. ZAP, which has its own channels, is excluded.

## More from today

- **A new home for the blog.** This post is the first on [blog.owaspblt.org](https://blog.owaspblt.org). The 32 posts from [dev.to/owaspblt](https://dev.to/owaspblt), back to 2025, are now here too, with their images and their authors' bylines, and each links back to where it was first published. Anyone can write a post: add a Markdown file to `blt-blog/posts/` and open a pull request.
- **BLT Sammich**, BLT's Slack app, now shows real workspace names and channel and member counts on its public page. A new dashboard for each workspace shows top channels, newcomer trends, peak joining hours and more, built only from public channels and aggregate data.
- **Automated dependency updates.** A weekly Renovate job now proposes grouped dependency updates, with at most five open at a time, as signed patches on the BLT forge at git.owaspblt.org.
- **Smarter issue pages.** Every issue on the forge now carries a project tag that links to that project's live site, across all 48 BLT sites.
- **AI-assisted pull request review.** A new review workflow checks open forge pull requests for security, relevance and robustness before a maintainer signs off.
- **Hacktoberfest wrap-up.** With Hacktoberfest over, its banners and references were retired across the BLT sites.
- **Community contributions merged.** Thanks to [**hrinkar01**](https://git.owaspblt.org/@hrinkar01) (security dependency upgrades for blt-legacy), [**hiralmodi14**](https://git.owaspblt.org/@hiralmodi14) (cleanup and cross-platform test fixes for blt-pages) and [**Salava-marquina**](https://git.owaspblt.org/@Salava-marquina) (stronger redaction tests for blt-netguardian).

## About OWASP BLT

OWASP BLT is an open-source OWASP project that helps people find, report and fix bugs and security issues, and that builds tools to support the open-source security community. All of BLT's projects live in a single monorepo at [git.owaspblt.org](https://git.owaspblt.org), mirrored to [github.com/OWASP/BLT](https://github.com/OWASP/BLT). Contributors of every experience level are welcome.

**Links**

- Tomato 1000: https://tomato.owaspblt.org/1000
- OWASP Project Matrix: https://projects.owaspblt.org
- Project Sweep: https://bumper.owaspblt.org/sweep
- Source: https://git.owaspblt.org
