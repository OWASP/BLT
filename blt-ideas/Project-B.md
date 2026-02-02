### Project B — Security Contribution Gamification & Recognition

**One line:** Consume verified security contributions to award BACON/badges, reputation tiers, leaderboards, and challenges.

**Description:** Listens for verified GHSC (or equivalent) events and awards rewards idempotently: BACON, badges, reputation tiers (Beginner → Trusted), severity-weighted leaderboards, and security challenges. Includes admin audit and basic fraud controls. Does not do detection or NVD; assumes a feed of verified contributions (real or mocked).

**Add-on (optional): light C (education bridge)**  
Project B can be extended with a **light C** add-on in the same 350-hour slot. Light C is *not* a separate project: it adds read-only APIs and an optional webhook that expose badge/reputation and leaderboard data (no raw CVE or vulnerability details). Future education platforms can use these to unlock courses or show contributor standing. No labs, no curriculum — just the APIs so B's outputs can drive education tooling. The **recommended** proposal is **B + light C** as one project.
