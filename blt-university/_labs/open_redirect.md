---
layout: lab
title: Open Redirect
description: Understand how open redirect vulnerabilities enable phishing attacks and security bypasses. Learn to
  exploit redirect parameters without validation to redirect users to malicious sites.
difficulty: beginner
category: Web Security
estimated_time: 25
tasks:
- name: Introduction to Open Redirect
  description: Learn what open redirect vulnerabilities are, why they matter, and common attack scenarios.
  type: theory
  order: 1
  heading: Introduction to Open Redirect
  content: |
    <h2>What is an Open Redirect?</h2>
    <p>An open redirect occurs when an application sends users to a destination URL controlled by user input, without validation.</p>

    <h3>Example</h3>
    <pre><code>
    GET /redirect?next=https://trusted.com/dashboard
    </code></pre>

    <h3>Impact</h3>
    <ul>
        <li>Phishing attacks using trusted domains</li>
        <li>Bypass domain allow-lists</li>
        <li>Chaining to server-side request (SSRF)</li>
    </ul>
  mcq:
    question: What is a primary risk posed by open redirects?
    options:
    - A) Enabling phishing to attacker-controlled sites
    - B) Executing SQL queries
    - C) Breaking CDN caching
    - D) Triggering HTTP/2
    answer: A
- name: Typical Open Redirect Patterns
  description: Where open redirects occur and how to detect them.
  type: theory
  order: 2
  heading: Typical Open Redirect Patterns
  content: |
    <h2>Where to find open redirects</h2>
    <ul>
      <li>Login flows: ?next=/path</li>
      <li>Return-To parameters</li>
      <li>Tracking/callback URLs</li>
    </ul>

    <h3>Code Smell</h3>
    <pre><code>
    return redirect(request.GET.get('next'))
    </code></pre>

    <h3>Defenses</h3>
    <ul>
      <li>Whitelist domains or internal paths</li>
      <li>Normalize and validate destination</li>
      <li>Prefer internal route names instead of raw URLs</li>
    </ul>
  mcq:
    question: Which prevents open redirects?
    options:
    - A) Accept any 'next' URL
    - B) Whitelist redirect hosts or limit to internal paths
    - C) Use attacker controlled scripts
    - D) Base64 encode next value only
    answer: B
- name: Basic Open Redirect - Redirect to Attacker
  description: Exploit a naive redirect parameter to send a user to attacker domain.
  type: simulation
  order: 3
  simulation:
    type: open_redirect_basic
    scenario: redirect_to_attacker
    target_url: /redirect?next=https://example.com
    vulnerable_parameters:
    - next
    success_payload: https://evil.attacker.example/phish
    success_criteria: Redirect to attacker-controlled website
    hints:
    - Replace ?next= with full attacker URL
    - Try http & https
    difficulty: beginner
    engine: legacy-payload
- name: Phishing Simulation via Open Redirect
  description: Show how attackers make a trusted-looking link forward to evil site.
  type: simulation
  order: 4
  simulation:
    type: open_redirect_phish
    scenario: phishing_link
    target_url: /redirect?next=
    vulnerable_parameters:
    - next
    success_payload: https://trusted.example/login?next=https://evil.attacker.example
    success_criteria: Trusted domain forwards into malicious page
    hints:
    - Create trusted-looking URL that chains attacker destination
    difficulty: intermediate
    engine: legacy-payload
- name: Open Redirect Chaining to SSRF or Internal Targets
  description: Use nested redirect to reach simulated internal host.
  type: simulation
  order: 5
  simulation:
    type: open_redirect_chain
    scenario: chain_to_internal
    target_url: /redirect?next=
    vulnerable_parameters:
    - next
    success_payload: http://evil.attacker.example/redirect?to=http://127.0.0.1:8080/secret
    success_criteria: Chain redirect to internal resource
    hints:
    - Use nested redirects
    - Internal host access simulated safely
    difficulty: advanced
    engine: legacy-payload
- name: Bypass Attempts & URL Encodings
  description: Encoding tricks that bypass naive validation (educational only).
  type: theory
  order: 6
  heading: Bypass Attempts & URL Encodings
  content: |
    <h2>Bypass Tricks</h2>
    <ul>
      <li>Percent-encoding</li>
      <li>Protocol-relative URLs (//evil.com)</li>
      <li>username@host patterns</li>
      <li>Nested redirects</li>
    </ul>
  mcq:
    question: Which encoding can bypass naive checks?
    options:
    - A) Percent-encoding
    - B) Remove slashes
    - C) Use only relative paths
    - D) Strip query params
    answer: A
- name: Open Redirect Prevention & Best Practices
  description: How to safely handle redirects.
  type: theory
  order: 7
  heading: Open Redirect Prevention & Best Practices
  content: |
    <h2>Prevention</h2>
    <ul>
        <li>Whitelist allowed redirect domains</li>
        <li>Only allow internal routes</li>
        <li>Normalize URLs before validation</li>
        <li>Optionally show confirmation for external redirects</li>
    </ul>
  mcq:
    question: Which is a secure redirect pattern?
    options:
    - A) Allow any raw URL
    - B) Whitelist internal paths
    - C) Base64 encode and trust input
    - D) Use attacker-controlled site redirects
    answer: B
---
