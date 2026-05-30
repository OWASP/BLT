# BLT Profiles

A GitHub Pages community directory for cybersecurity professionals, bug hunters, and security researchers.

## 🌐 Live Site

**[https://owasp-blt.github.io/BLT-Profiles/](https://owasp-blt.github.io/BLT-Profiles/)**

Individual profiles are available at:
```
https://owasp-blt.github.io/BLT-Profiles/profile.html?user=<github-username>
```

---

## ➕ Adding Your Profile

1. **[Open an Issue](../../issues/new/choose)** using the *Add Profile* template.
2. Fill in your details — role section, social links, and three cybersecurity Q&A answers.
3. A GitHub Action automatically:
   - Fetches your public GitHub data (avatar, followers, repos)
   - Creates `profiles/<username>.json`
   - Updates `profiles/index.json` with role section data
   - Comments on the issue with your live profile URL
4. Your profile appears on the homepage immediately.

---

## 🧭 Role-Based Profile Sections

Profiles are organized into the following sections:

- Leads
- Co-Leads
- Ambassadors
- Interns
- Contributors
- Mentors

Legacy profiles are being migrated with a `role_section` field while preserving existing profile fields (such as `role`) to avoid data loss.

---

## 🗂️ Project Structure

```
BLT-Profiles/
├── index.html                        # Homepage — profile listing
├── profile.html                      # Dynamic profile page (?user=username)
├── 404.html                          # Custom 404 with URL routing
├── _config.yml                       # GitHub Pages config
├── profiles/
│   ├── index.json                    # Master list of all profiles
│   └── <username>.json               # Individual profile data files
└── .github/
    ├── ISSUE_TEMPLATE/
    │   └── add-profile.yml           # Profile submission template
    ├── workflows/
    │   └── process-profile.yml       # Auto-publishes profiles from issues
    └── scripts/
        └── create_profile.py         # Issue parser + profile generator
```

---

## 🎨 Style Guide

| Token              | Value       |
|--------------------|-------------|
| Primary            | `#E10101`   |
| Primary hover      | `#b91c1c`   |
| Neutral border     | `#E5E5E5`   |
| Dark base          | `#111827`   |
| Dark surface       | `#1F2937`   |

**Stack:** Pure HTML · Tailwind CSS CDN · Font Awesome CDN

---

## 🛡️ License

[AGPL-3.0](LICENSE) — OWASP BLT Project