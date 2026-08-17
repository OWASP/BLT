---
layout: lab
title: Passwords and Multi-Factor Authentication
description: Learn how unique passwords, password managers, and MFA reduce the impact of account attacks.
difficulty: beginner
category: Cyber Hygiene
track: hygiene
estimated_time: 45
tags:
  - passwords
  - multi-factor authentication
  - account security
learning_objectives:
  - Create a safer password strategy.
  - Understand why password reuse is risky.
  - Choose an appropriate MFA method.
success_criteria:
  - Distinguish unique passwords from reused credentials.
  - Select MFA and recovery actions that reduce account takeover risk.

tasks:
  - name: Use Unique Passwords
    description: Understand why a password leak on one service can affect every account that reuses it.
    type: theory
    order: 1
    heading: One account should not unlock every account
    content: |
      Attackers regularly try leaked username-and-password pairs on other services. Reusing a password turns one unrelated breach into a chain of account takeovers.

      Use a different password for every important account. A password manager can generate and remember long, random passwords so you do not have to memorize each one. Protect the manager with a strong unique master password and MFA.

      Never share passwords through chat or email. Legitimate support staff should not need your password.
    mcq:
      question: What can happen when the same password is reused across several services?
      options:
        - A) Reused passwords are always shorter than unique passwords.
        - B) A password exposed by one breach can be tried on other accounts.
        - C) Password managers cannot store reused passwords.
        - D) Reused passwords prevent MFA from working.
      answer: B

  - name: Add a Second Factor
    description: Compare MFA methods and understand how they add protection beyond a password.
    type: theory
    order: 2
    heading: A password is not the only proof of identity
    content: |
      Multi-factor authentication asks for another kind of proof after the password. Common factors include something you know, something you have, and something you are.

      Prefer a security key or an authenticator app when available. Push approvals can be useful, but never approve an unexpected prompt. SMS codes are better than a password alone but can be exposed through phone-number attacks, so treat them as a fallback where stronger methods are unavailable.
    mcq:
      question: An MFA approval request appears, but you did not try to sign in. What should you do?
      options:
        - A) Approve it so the prompts stop.
        - B) Share the code with the person who requested it.
        - C) Deny it, change the password from the official service, and report the event.
        - D) Disable MFA permanently.
      answer: C

  - name: Protect Recovery Options
    description: Review the recovery settings that can help or undermine account security.
    type: theory
    order: 3
    heading: Recovery is part of the account boundary
    content: |
      An attacker who controls a recovery email address or phone number may be able to reset the account even without the current password. Keep recovery details current, protect the recovery account with its own unique password and MFA, and store backup codes somewhere private and offline.

      Review active sessions and connected applications after a suspected compromise. Sign out unknown sessions, remove unfamiliar access, and contact the service through its official support channel.
    mcq:
      question: Which recovery setup makes it harder for someone else to take over the account?
      options:
        - A) Store backup codes in a public notes application.
        - B) Reuse the main account password for the recovery email.
        - C) Protect the recovery account with a unique password and MFA.
        - D) Share recovery codes with a coworker for convenience.
      answer: C

  - name: Respond to an Account Alert
    description: Practice the safest response to an unexpected sign-in or MFA notification.
    type: theory
    order: 4
    heading: Treat unexpected prompts as a possible compromise
    content: |
      An unexpected sign-in alert or MFA prompt may mean that someone knows your password. Deny the prompt and do not approve repeated requests just to make them stop.

      From the service's official website or application, change the password, review recent activity, sign out other sessions, remove unfamiliar applications, and check recovery details. Report the event to the service if the activity was not yours.
    mcq:
      question: You receive an unexpected MFA prompt. Which response protects the account instead of giving an attacker access?
      options:
        - A) Approve it so the prompts stop.
        - B) Deny it, then use the official service to change the password and review sessions.
        - C) Send the prompt code to a support account in a chat message.
        - D) Turn off MFA before investigating the alert.
      answer: B

  - name: Make an Account Plan
    description: Combine password, MFA, and recovery choices into a practical account-protection plan.
    type: theory
    order: 5
    heading: Protect the account and its recovery path
    content: |
      For each important account, make sure the password is unique and stored safely, a strong MFA method is enabled, and recovery details are current. Keep backup codes private and review active sessions and connected applications from time to time.

      Protect the email account that receives recovery messages especially carefully. If it is compromised, an attacker may be able to reset other accounts even when those accounts use strong passwords.
    mcq:
      question: Which combination gives an important account a sensible, strong baseline of protection?
      options:
        - A) One memorable password reused everywhere and SMS disabled.
        - B) A unique password, phishing-resistant MFA when available, and protected recovery options.
        - C) A shared password stored in a team chat and no backup codes.
        - D) A short password changed only after an account is breached.
      answer: B

  - name: Recover a Compromised Account
    description: Practice containing an account takeover while preserving evidence and protecting connected services.
    type: theory
    order: 6
    heading: Contain the compromise, then rebuild trust
    content: |
      You notice a sign-in from an unfamiliar location and an email saying that your recovery address was changed. You still have access to the account on one trusted device.

      Use that trusted device to open the official service, change the password, sign out other sessions, restore the correct recovery details, and remove unknown applications. Revoke active sessions and API tokens when the service provides that option. Save the alert details for support, contact the service through its official recovery process, and change any other account that reused the exposed password.

      Do not follow links in the alert email or send a recovery code to anyone who contacts you. If the account controls work or financial information, escalate quickly to the organisation responsible for it.
    mcq:
      question: You still have one trusted device after a suspected account takeover. What is the most complete response?
      options:
        - A) Delete the alert email and keep using the account because the trusted device still works.
        - B) Change only the password and wait to see whether another alert arrives.
        - C) Use the official service to reset access, end other sessions, restore recovery settings, remove unknown access, and report the incident.
        - D) Send the alert and a recovery code to a helpful person who offers to fix the account.
      answer: C
---
