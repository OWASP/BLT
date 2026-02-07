### Idea I — First-Time Contributor Experience & AI-Assisted Security Guide

**Idea Type:** Single 350-hour development effort

**One line:** Security-first onboarding, documentation clarity, and an AI-assisted guide to help contributors understand BLT and OWASP expectations before contributing.

**Description:**
Improves BLT’s first-time contributor experience by addressing onboarding, navigation, and documentation gaps that lead to insecure or low-quality contributions. The idea introduces a clear 
“start here” walkthrough for new users, security-focused information architecture, and contribution clarity pages that explain what qualifies as a security contribution and why PRs may be rejected.
Includes a constrained, explain-only AI Security Guide embedded into the website that answers contributor questions in beginner-friendly language using BLT documentation, GitHub Discussions, 
and OWASP public resources (e.g. OWASP Top 10, Cheat Sheet Series). The AI does not review code, analyze diffs, approve PRs, or generate exploit guidance; it is strictly scoped to explanation, 
clarification, and linking to authoritative sources.

**Problem Statement**
Current challenges observed in BLT onboarding and contribution flow:
- No clear starting point: First-time contributors land on BLT without a clear “start here” path explaining how the platform works from a security perspective.
- Security context is implicit: Security-critical pages, tools, and apps are listed alongside general features, making it hard to tell what matters first versus what is advanced.
- Fragmented documentation: Documentation exists across README files, GitHub Discussions, and OWASP resources, but is not clearly surfaced (e.g., broken Setup.md links).
- Unclear contribution expectations: Contributors often don’t understand what qualifies as a security contribution or why PRs get rejected.
- AI slop without understanding: With increased AI usage, contributors submit code without understanding whether it introduces security risks or violates OWASP principles.
- For a security-focused OWASP project, this leads to contributor frustration, reviewer overload, and avoidable security risk.

**Solution: BLT First-Time Contributor Experience & Security Guide**
A UI/UX-first onboarding and learning system, supported by a constrained, explain-only AI guide, designed to educate contributors before mistakes happen.
The solution focuses on clarity, guidance, and learning, not automation or enforcement.

**Key components:**
1 First-time user walkthrough (“New to BLT? Start Here”) explaining BLT’s security focus, contribution flow, common beginner mistakes, and next steps
  - A dedicated onboarding page that acts as the single entry point for new contributors. It explains, step-by-step:
    What BLT is and why it is security-focused
    How a secure contribution works end-to-end (issue → fix → review → learning)
    What counts as a security contribution (with concrete examples)
    Common beginner mistakes (including AI copy-paste issues)
    Where contributors should go next (correct docs, repos, beginner-friendly issues)
    This reduces confusion and prevents insecure contributions before they are submitted.

2 Security-focused navigation and page annotations to distinguish beginner paths from advanced tools and apps
  - Improves how BLT is structured and perceived by new users:
    Groups security-critical sections clearly and visibly Adds short “why this matters” explanations to major areas Distinguishes beginner paths
    from advanced tools and apps This makes BLT’s security-first nature immediately obvious.
  - Example: Security Contributions: Pages related to finding, fixing, and understanding security issues (Bugs, Issues,...) 
             Learn & Understand: Pages that explain how security works in BLT (Documentation, “New to BLT? Start Here”, AI Security Guide,...)
             Contribute & Collaborate: Pages related to working with others (Projects, Repositories, GitHub links, Teams,...)
             Advanced / Platform Tools: Pages that are not for beginners (SimilarityScan, Time Logs, Check-In, Staking, BACON, Admin / stats tools

3 Documentation surfacing and fixes (repair broken links, define canonical entry points)
  - Surfaces and organizes existing knowledge rather than creating new theory:
    Fixes broken documentation links and defines canonical entry points
    Adds clarity pages such as:
    “What counts as a security contribution?”
    “Why PRs get rejected at BLT”
    Uses plain, beginner-friendly language and anonymized real examples to explain security expectations
    This turns rejections into learning, not frustration.

4 Embedded AI Security Guide for contextual, beginner-friendly explanations grounded in BLT + OWASP content
  - An embedded, context-aware AI Security Guide that acts as a smart help layer, not a general chatbot.
    What it does:
    Answers contributor questions in beginner-friendly language
    Explains OWASP concepts and BLT contribution rules
    Points users to relevant BLT docs, GitHub Discussions, and OWASP resources
    
  - What it does NOT do:
    Review code or analyze diffs
    Approve or reject PRs
    Generate exploit guidance or security fixes
    
  - The AI is grounded only in:
    BLT documentation and contribution guidelines
    BLT GitHub Discussions
    Well-established OWASP resources (e.g., OWASP Top 10, Cheat Sheet Series)
    All responses are source-linked and auditable.
  
## Scope notes
- Frontend and UX heavy (React / Next.js / Tailwind)
- Light GitHub API usage (public data only)
- No vulnerability scanning, no PR automation, no model training from scratch
- AI is constrained, auditable, and source-linked

**Impact:**
Fewer insecure or misunderstood PRs
Better first-time contributor experience
Reduced reviewer burden
Stronger alignment with OWASP’s secure-by-design and education mission

**Why this matters now**
As AI-assisted coding becomes common, understanding why something is insecure is more important than ever. This idea ensures BLT remains a place where contributors learn security — not just ship code and aligns well with BLT's goals for 2026. 
