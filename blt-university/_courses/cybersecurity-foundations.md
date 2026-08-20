---
layout: course
title: Cybersecurity Foundations
category: Cyber Hygiene
level: Beginner
track: hygiene
duration: 60 to 90 minutes
instructor: OWASP BLT Community
featured: true
next_course: web-security-intro
prerequisites: No prior cybersecurity experience
description: Build safer online habits through three short lessons, realistic examples, and focused practice labs.
outcomes:
  - Spot pressure tactics and verify suspicious messages before acting.
  - Build stronger password and MFA habits.
  - Practice safe browsing and account-recovery decisions.
lessons:
  - id: read-the-pressure
    title: Read the pressure before the message
    intro: Phishing works by making an ordinary request feel urgent enough to skip verification.
    body: |
      Start with the request, not the logo. A message can look polished and still ask you to do something unsafe. Pause when it asks for a password, payment, recovery code, or quick download.

      Check the sender using a channel you already trust. If the message claims to come from your bank or workplace, open the official site yourself instead of following its link.
    example:
      title: A useful pause
      language: Message
      code: |
        Your account closes in 10 minutes.
        Confirm your password at secure-account-check.example.
      note: The deadline and password request matter more than the professional-looking wording.
    observation: This is the part people usually overlook. Urgency is evidence, not a reason to move faster.
    labs:
      - phishing-awareness
  - id: protect-the-account
    title: Protect the account, not just the password
    intro: A unique password and a second factor limit how far one stolen credential can travel.
    body: |
      Password reuse turns one breach into several account takeovers. A password manager helps because it can create a different password for every service without asking you to remember each one.

      Multi-factor authentication adds another check. Prefer an authenticator app or security key when the service supports one, and keep recovery codes somewhere separate from the device you use every day.
    example:
      title: Reuse creates a chain
      language: Accounts
      code: |
        shopping site leaked password
                  ↓
        same password opens email
                  ↓
        email resets other accounts
      note: The first compromised site does not need to be important if the password is reused elsewhere.
    labs:
      - passwords-and-mfa
  - id: make-the-browser-earn-trust
    title: Make downloads earn your trust
    intro: A familiar-looking page does not make its download, permission request, or public network safe.
    body: |
      Prefer official stores and vendor pages. Check the domain, file type, and reason for the download before opening it. Unexpected browser notifications and extension permissions deserve the same pause.

      Updates close known weaknesses, but fake update prompts are common. Open the application or device settings and update from there when a website suddenly claims your software is outdated.
    observation: Before moving on, ask what the site gains from the permission it requests. If the answer is unclear, deny it.
    labs:
      - safe-browsing-and-downloads
---

Security advice is easier to remember when it connects to a decision you actually make. This course covers three of those decisions: whether to trust a message, how to protect an account, and when to trust a download.

Each short lesson is followed by an existing BLT University lab. Read the idea, try the scenario, and return here to see your course progress update.
