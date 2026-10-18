# BLT Profiles

**Live Site:** [https://profiles.owaspblt.org/](https://profiles.owaspblt.org/)<br>
**Source Code:** [https://git.owaspblt.org/BLT/tree/main/blt-profiles](https://git.owaspblt.org/BLT/tree/main/blt-profiles)

A Git-native community directory and professional identity platform for cybersecurity professionals, security researchers, bug hunters, mentors, students, and open-source contributors.

BLT Profiles combines structured profile data, personal portfolios, research artifacts, community involvement, and optional identity verification into a portable profile stored in Git.

Unlike traditional social networks, BLT Profiles focuses on contributions, learning, mentorship, research, and collaboration rather than followers, likes, or engagement metrics.

---

## 🌐 Vision

BLT Profiles aims to become an open, community-owned identity and portfolio platform for the cybersecurity ecosystem.

Every member owns their profile through Git, can update it through issues or pull requests, and can build a public portfolio that grows alongside their career.

Profiles are designed to be:

* Git-native
* Human-readable
* Machine-readable
* Searchable
* Portable
* Extensible
* Open-source
* Community-owned

The goal is to create a place where people can showcase what they build, learn, teach, research, and contribute.

---

## 🚀 Live Site

**https://profiles.owaspblt.org/**

Profile URLs:

```text
https://profiles.owaspblt.org/zerocool
```

Cloudflare serves the static profile browser through a small Worker that maps `/<username>` to the profile page. New profiles arrive as issues on git.owaspblt.org and a workflow commits them.

---

# ✨ Why BLT Profiles?

Most platforms measure popularity.

BLT Profiles highlights:

* Technical skills
* Open-source contributions
* Research interests
* Community involvement
* Mentorship
* Learning journeys
* Projects
* Writeups
* Certifications
* Professional growth

A profile should represent your work and contributions, not your follower count.

---

# 📁 Profile Structure

Each member has their own directory within the repository.

```text
profiles/
├── <username>/
│   ├── profile.yaml
│   ├── README.md
│   ├── avatar.png
│   │
│   ├── keys/
│   │   ├── pgp.asc
│   │   └── ssh.pub
│   │
│   ├── writeups/
│   │   ├── writeup-1.md
│   │   └── writeup-2.md
│   │
│   └── projects/
│       ├── project-1.md
│       └── project-2.md
```

Only `profile.yaml` is required.

Everything else is optional and can be added over time.

---

# 📄 Profile Format

Each profile contains a structured metadata file named `profile.yaml`.

Example:

```yaml
version: 1

identity:
  handle: "zerocool"
  name: "Dade Murphy"

location:
  city: "New York"

contacts:
  email: "zero@example.com"
  website: "https://zerocool.dev"
  gitlab: "zerocool"

role_section: "Contributor"

skills:
  - reverse-engineering
  - exploit-development
  - malware-analysis
  - cryptography

languages:
  - Rust
  - Go
  - Python
  - C

interests:
  - embedded-security
  - operating-systems
  - distributed-systems

availability:
  mentoring: true
  hiring: false

projects:
  - kernel-lab
  - rust-fuzzer

proofs:
  pgp_fingerprint: "ABCD EFGH IJKL..."
```

---

# 📝 README Profiles

Each profile may include a `README.md`.

The README serves as the member's public profile page and can include:

* Biography
* Career journey
* Research interests
* Project showcases
* Conference talks
* Certifications
* Learning goals
* Community involvement
* Portfolio links

This allows profiles to grow beyond simple metadata.

---

# 🔐 Identity Verification

BLT Profiles supports optional verification methods.

Potential verification options include:

* git.owaspblt.org account verification
* Signed commits
* SSH public keys
* PGP keys
* Sigstore attestations
* Community endorsements

Verification is intended to establish ownership and trust while remaining accessible to everyone.

---

# 🧭 Community Roles

Profiles can be organized into community sections.

Current sections:

* Leads
* Co-Leads
* Ambassadors
* Interns
* Contributors
* Mentors

Additional categories may be introduced as the community evolves.

---

# ➕ Creating a Profile

## Issue Submission

1. Copy the template [`issue-templates/add-profile.md`](https://git.owaspblt.org/BLT/blob/main/blt-profiles/issue-templates/add-profile.md).
2. Open a new issue at https://git.owaspblt.org/BLT/issues/new (signed in), titled
   `[blt-profiles] Add profile: <username>`, and paste the template as the description.
3. Fill out the fields without changing the `## ...` headings, and tick the confirmation box (`- [x]`).
   Leave `Username` empty to use your git.owaspblt.org account name.
4. The workflow [`.forkmesh/blt-profiles--add-profile.yml`](https://git.owaspblt.org/BLT/blob/main/.forkmesh/blt-profiles--add-profile.yml)
   runs `scripts/actions/add-profile.mjs`, which commits to `main`:

   * `public/profiles/<username>.json`
   * `public/profiles/index.json`

   then deploys the site, comments with the profile link and closes the issue. If a field is invalid it
   comments instead and runs again when you edit the issue.
5. The profile is available at:

   ```text
   https://profiles.owaspblt.org/<username>
   ```

An issue is treated as a profile submission when it has the label `profile`, `add-profile` or
`profile-submission`, a title starting with `[blt-profiles]`, or the template headings. Only the account that
created a profile can update it (open another issue the same way).

## Manual Submission

1. Fork the repository.
2. Create a profile directory under `profiles/`.
3. Add a `profile.yaml`.
4. Optionally add:

   * README.md
   * avatar image
   * writeups
   * projects
   * verification files
5. Open a pull request on git.owaspblt.org.

---

# 🗂 Repository Structure

```text
BLT-Profiles/
├── public/
│   ├── index.html
│   ├── profile.html
│   ├── 404.html
│   └── profiles/
│       ├── index.json
│       └── <username>.json
│
├── src/
│   └── index.py
│
├── scripts/actions/
│   └── add-profile.mjs        # run by .forkmesh/blt-profiles--add-profile.yml
│
├── test/
│   └── add-profile.test.mjs   # node --test test/*.test.mjs
│
├── wrangler.toml
│
└── issue-templates/
    └── add-profile.md
```

---

# 🔎 Search & Discovery

Future profile discovery features may include:

* Skill-based search
* Technology tags
* Research interests
* Community roles
* Mentorship availability
* Geographic regions
* Languages
* Open-source interests

Examples:

* Find Rust developers
* Find mentors
* Find web security researchers
* Find OWASP contributors
* Find bug bounty participants

---

# 🏆 Recognition

BLT Profiles is designed to recognize meaningful contributions.

Examples include:

* Mentorship
* Research publications
* Community service
* Open-source contributions
* Documentation
* Conference speaking
* Project leadership
* Educational content

The platform intentionally avoids popularity-based metrics.

---

# 🚀 Roadmap

## Phase 1 — Foundation

* [ ] Profile directory structure
* [ ] YAML profile schema
* [ ] Avatar support
* [ ] README rendering
* [ ] Profile validation
* [ ] Automated profile index generation
* [ ] Automated deployment (`.forkmesh` workflow)

## Phase 2 — Discovery

* [ ] Search interface
* [ ] Skill filtering
* [ ] Technology filtering
* [ ] Mentor directory
* [ ] Contributor directory
* [ ] Role-based browsing

## Phase 3 — Portfolios

* [ ] Research writeups
* [ ] Project showcases
* [ ] Certification support
* [ ] Event history
* [ ] Learning journals

## Phase 4 — Verification

* [ ] PGP verification
* [ ] SSH verification
* [ ] Signed profile attestations
* [ ] Verified contributor badges
* [ ] Trust and endorsement system

## Phase 5 — Community Growth

* [ ] Guided profile creation
* [ ] git.owaspblt.org sign-in onboarding
* [ ] Profile templates
* [ ] Community badges
* [ ] Mentor matching
* [ ] Collaboration matching

## Phase 6 — Ecosystem

* [ ] Public API
* [ ] Profile export/import
* [ ] Federation support
* [ ] Integration with OWASP projects
* [ ] Integration with community events
* [ ] External profile embeds

---

# 📈 Adoption Strategy

## Build Useful Profiles

Profiles should serve multiple purposes:

* Community profile
* Professional portfolio
* Speaker page
* Mentor page
* Resume hub
* Research archive

People maintain profiles when they provide value beyond directory listings.

## Integrate with Existing Communities

Promote BLT Profiles through:

* OWASP projects
* OWASP chapters
* Community meetups
* Security conferences
* Capture-the-Flag communities
* Open-source projects

## Recognize Contributions

Highlight:

* New contributors
* Mentor spotlights
* Research highlights
* Community achievements
* Open-source contributions

## Keep Participation Simple

The ideal onboarding experience:

1. Sign in to git.owaspblt.org
2. Generate a starter profile
3. Upload an avatar
4. Publish

The barrier to participation should remain low.

---

# 🛠 Technology Stack

* git.owaspblt.org issues and `.forkmesh` workflows
* Cloudflare Workers
* Cloudflare Static Assets
* Python
* HTML
* Tailwind CSS
* Browser JavaScript
* YAML
* Markdown

---

# ☁️ Cloudflare Deployment

The site is configured for Cloudflare Workers Static Assets.

```bash
wrangler deploy
```

The Worker serves:

* `/` from `index.html`
* `/<username>` from `profile.html`
* `/profiles/*.json` as static profile data
* `/api/health`

It needs no secrets or variables. The add-profile workflow deploys with the repository's
`CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` Actions secrets.

Run the workflow script's tests with `node --test test/*.test.mjs`.

---

# 🤝 Contributing

Contributions are welcome from students, researchers, mentors, developers, community organizers, and security professionals.

Whether you're sharing research, mentoring others, contributing code, or learning something new, BLT Profiles exists to help showcase and connect people through meaningful work.

---

# 🛡 License

AGPL-3.0 — OWASP BLT Project
