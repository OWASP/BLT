Project F — Contributor Security Reputation Graph (Quality-First Leaderboards)

One line: A quality-driven contributor reputation and leaderboard system that ranks trust and impact instead of raw activity.

Description:
BLT runs hackathons and pre-GSoC programs where we repeatedly face issues with incorrect leaderboards, spam PRs, low-quality comments, and gaming of the system. Contributors often inflate scores by opening irrelevant issues, posting useless comments on PRs, or exploiting unclear scoring rules. The /leaderboard command and website leaderboards also suffer from incorrect timeline windows, inconsistent data, and a heavy focus on quantity over quality, with little guidance around best practices, code of conduct, or what actually makes a good contribution.

This project proposes a proper, long-term fix to these problems.

The system introduces a Contributor Security Reputation Graph that evaluates contributors based on quality signals, not volume. Signals can include accepted PRs, severity and impact of fixes, review usefulness, false-positive history, maintainer feedback, and sustained contribution behavior over time. Spam actions, low-effort comments, and irrelevant activity naturally decay or carry little weight.

This enables a new class of leaderboards that rank quality, not quantity. Leaderboards become accurate, time-bounded, and explainable, instead of noisy and easily gamed.

The system can directly support:

- BLT core leaderboards
- /leaderboard Slack command
- BLT hackathons
- BLT-Hackathon (standalone, open-source, GitHub Pages–based app that others can clone and use)

Beyond fixing existing issues, this creates an opportunity to give back to the wider open-source community by offering a reusable, quality-first leaderboard model that currently does not exist in most OSS ecosystems.

The project focuses on clear scoring logic, transparent rules, and documentation around contribution quality, best practices, and expected behavior, making it easier for new contributors to understand how to contribute well, not just how to score points.