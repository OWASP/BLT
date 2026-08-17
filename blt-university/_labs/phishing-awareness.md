---
layout: lab
title: Phishing Awareness
description: Practice identifying suspicious messages and choosing a safe response before a scam captures your information.
difficulty: beginner
category: Cyber Hygiene
track: hygiene
estimated_time: 45
tags:
  - phishing
  - social engineering
  - safe browsing
learning_objectives:
  - Recognize common phishing warning signs.
  - Inspect links without opening them.
  - Verify requests through a trusted channel.
success_criteria:
  - Recognize suspicious sender, urgency, and link signals.
  - Choose a safe reporting and verification action.

tasks:
  - name: Spot the Warning Signs
    description: Learn how phishing messages use urgency and impersonation to make unsafe actions feel normal.
    type: theory
    order: 1
    heading: Slow down when a message creates pressure
    content: |
      Phishing messages imitate a trusted person or service and ask you to act quickly. The message may claim that your account will be closed, a payment failed, or an urgent document needs your review.

      Look for several signals together:

      - The sender address uses a lookalike domain or an unexpected account.
      - The message creates urgency or asks you to keep the request secret.
      - The greeting, spelling, or tone does not match the supposed sender.
      - A link or attachment asks for a password, payment, or personal information.

      One unusual detail is worth checking. Several unusual details are a reason to stop and verify the request independently.
    mcq:
      question: An unexpected account message lands in your inbox. Which mix of details should make you stop and verify it?
      options:
        - A) It contains the company logo and uses a short sentence.
        - B) It arrives during business hours and has a signature.
        - C) It asks you to read a public announcement.
        - D) It uses urgency, a lookalike sender domain, and a login link.
      answer: D

  - name: Inspect the Link Safely
    description: Practice checking where a link leads without opening the destination.
    type: theory
    order: 2
    heading: Read the real destination before trusting it
    content: |
      A link's visible text can be different from its real destination. On a computer, hover over the link to preview the address. On a phone, press and hold when the application provides a preview. Do not sign in just to find out whether a link is safe.

      Read the domain from right to left. In `accounts.example.com`, the important registered domain is `example.com`. A name such as `example.com.attacker.test` belongs to `attacker.test`, not `example.com`.

      When a message might be legitimate, open the service using a bookmark or a manually typed address instead of the message link.
    mcq:
      question: You receive a password-reset link you did not request. What is the safest way to check whether it is real?
      options:
        - A) Open it in a private window and enter the password only if the page looks correct.
        - B) Visit the service using a known address or bookmark and check for notifications there.
        - C) Forward it to a friend and ask them to test it.
        - D) Download the page so it can be inspected offline.
      answer: B

  - name: Verify and Report
    description: Choose a safe next step after recognizing a suspicious message.
    type: theory
    order: 3
    heading: Verify through a channel you already trust
    content: |
      Do not reply to a suspicious message, call a number included in it, or use its links to verify the request. Instead, contact the person or organization through a known phone number, official application, or bookmarked website.

      Report the message using your mail provider's phishing control or your organization's security process, then delete it. If you already entered information, change the affected password from the trusted service, enable MFA, and tell the organization quickly.
    mcq:
      question: Once you have identified a suspicious message, what should happen next?
      options:
        - A) Reply to ask whether the sender really sent it.
        - B) Click the link once without entering any information.
        - C) Verify independently, report the message, and delete it.
        - D) Share it publicly so other people can investigate.
      answer: C

  - name: Handle a Suspicious Request
    description: Apply the warning signs to a realistic message before deciding what to do.
    type: theory
    order: 4
    heading: Combine clues before you act
    content: |
      Imagine that a message appears to come from your manager. It asks you to buy gift cards immediately, says they are needed for a confidential project, and tells you to reply with the codes. The sender address uses a slightly different domain from your organisation.

      This request has several independent warning signs: an unusual payment request, secrecy, urgency, and a lookalike address. Do not continue the conversation or send anything. Verify the request using a known phone number or an established workplace channel.
    mcq:
      question: A manager appears to request gift cards through a lookalike address. What is the safest response?
      options:
        - A) Buy one card first and ask for confirmation after sending the code.
        - B) Reply to the message and ask the sender to prove their identity.
        - C) Verify through a trusted channel and report the message if it is fraudulent.
        - D) Forward the message to coworkers and wait for someone else to respond.
      answer: C

  - name: Build a Safe Habit
    description: Turn phishing detection into a repeatable decision process.
    type: theory
    order: 5
    heading: Pause, verify, and report
    content: |
      Use a simple three-step routine whenever a message asks for credentials, money, confidential information, or an unexpected download:

      1. Pause. Do not click, reply, open the attachment, or share information.
      2. Verify. Contact the supposed sender or service through a trusted channel you found independently.
      3. Report. Use the organisation's reporting process, then remove the message.

      If you already clicked or entered information, tell the organisation quickly. Change the affected password from the official site, revoke unfamiliar sessions, and enable MFA.
    mcq:
      question: Before doing anything else, what is the right first move when an unexpected message asks for sensitive information?
      options:
        - A) Pause and avoid interacting with the message until it is verified independently.
        - B) Reply with a small amount of information to test the sender.
        - C) Open the attachment in the same browser to inspect it.
        - D) Wait for the sender to send a second reminder.
      answer: A

  - name: Complete the Phishing Response
    description: Work through a realistic message that combines impersonation, urgency, and a malicious attachment.
    type: theory
    order: 6
    heading: Choose the complete response, not just one safe action
    content: |
      You receive an email that appears to come from your payroll provider. It says your direct-deposit details will be suspended in one hour, includes a spreadsheet attachment, and asks you to reply with a one-time verification code. The sender domain has one extra character compared with the provider's real domain.

      Treat the message as phishing. Do not open the attachment, reply, or share the code. Report it through your organisation's process, then contact payroll through a known channel to confirm whether any action is needed. If you opened the file or shared information, tell the security team immediately so they can help protect your account.
    mcq:
      question: The payroll message combines urgency, a lookalike domain, and an attachment. Which response handles the whole situation safely?
      options:
        - A) Open the spreadsheet, then call the phone number in the email if it looks suspicious.
        - B) Reply without the code, wait for a second email, and then report it.
        - C) Avoid interacting with it, verify through a trusted payroll channel, report it, and disclose any exposure.
        - D) Forward it to a colleague and let them decide whether the domain is real.
      answer: C
---
