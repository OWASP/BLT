---
layout: lab
title: Command Injection
description: Learn how unsafe system command construction leads to command injection and how to prevent it.
difficulty: intermediate
category: Web Security
estimated_time: 45
tasks:
- name: Understanding Command Injection
  description: Learn the basics of command injection vulnerabilities
  type: theory
  order: 1
  heading: Understanding Command Injection
  content: |
    <h2>What is Command Injection?</h2>
    <p>Command injection allows an attacker to execute arbitrary OS commands on the server by manipulating inputs to insecure system calls.</p>
  mcq:
    question: What is Command Injection?
    options:
    - A) Injecting OS commands via user input
    - B) Improving system performance
    - C) Backing up data
    - D) Writing database queries
    answer: A
- name: Command Injection Types
  description: Understand different types of command injection
  type: theory
  order: 2
  heading: Command Injection Types
  content: |
    <h2>Types of Command Injection</h2>
    <ul>
        <li>Blind command injection</li>
        <li>Time-based command injection</li>
        <li>Out-of-band command injection</li>
    </ul>
  mcq:
    question: Which of the following is NOT a type of command injection?
    options:
    - A) Blind command injection
    - B) Time-based command injection
    - C) Out-of-band command injection
    - D) Cross-site command injection
    answer: D
- name: Basic Command Injection
  description: Practice basic command injection with simple payloads
  type: simulation
  order: 3
  simulation:
    scenario: ping_feature
    vulnerable_parameters:
    - ip_address
    success_criteria: Execute a command that shows the current directory contents
    success_payload: 127.0.0.1; ls
    hints:
    - Use command separators like ; to chain commands
    difficulty: beginner
    engine: legacy-payload
    type: ping_feature
    target_url: /safe-simulation
- name: Command Injection with Pipes
  description: Use pipe operators for command injection
  type: simulation
  order: 4
  simulation:
    scenario: ping_filter_semicolon
    vulnerable_parameters:
    - ip_address
    success_criteria: Execute a command that shows system information
    success_payload: 127.0.0.1 | uname -a
    hints:
    - Try the pipe operator (|) to feed output into commands
    difficulty: beginner
    engine: legacy-payload
    type: ping_filter_semicolon
    target_url: /safe-simulation
- name: Blind Command Injection
  description: Practice blind command injection techniques
  type: simulation
  order: 5
  simulation:
    scenario: blind_injection
    vulnerable_parameters:
    - ip_address
    success_criteria: Cause a measurable time delay
    success_payload: 127.0.0.1; sleep 5
    hints:
    - Use time delays like sleep to confirm injection
    difficulty: intermediate
    engine: legacy-payload
    type: blind_injection
    target_url: /safe-simulation
- name: Command Injection Prevention
  description: Learn how to prevent command injection vulnerabilities
  type: theory
  order: 6
  heading: Command Injection Prevention
  content: |
    <h2>Prevention</h2>
    <ul>
        <li>Validate and sanitize all inputs</li>
        <li>Use safe, parameterized APIs instead of shell calls</li>
        <li>Avoid invoking system commands entirely when possible</li>
    </ul>
  mcq:
    question: What is the BEST way to prevent command injection?
    options:
    - A) Input validation only
    - B) Parameterized commands only
    - C) Avoid system commands only
    - D) All of the above combined
    answer: D
- name: Advanced Command Injection
  description: Practice advanced command injection with encoding
  type: simulation
  order: 7
  simulation:
    scenario: filter_bypass
    vulnerable_parameters:
    - ip_address
    success_criteria: Execute a command that shows the current user
    success_payload: 127.0.0.1${IFS}&&${IFS}whoami
    hints:
    - Use ${IFS} instead of spaces to bypass filters
    difficulty: advanced
    engine: legacy-payload
    type: filter_bypass
    target_url: /safe-simulation
- name: Command Injection in Web Shells
  description: Understand how command injection relates to web shells
  type: theory
  order: 8
  heading: Command Injection in Web Shells
  content: |
    <h2>Web Shells</h2>
    <p>Command injection can be leveraged to upload or execute web shells, providing persistent access.</p>
  mcq:
    question: How does command injection relate to web shells?
    options:
    - A) It can be used to upload/execute shells
    - B) Web shells are a type of command injection
    - C) They are unrelated
    - D) Web shells prevent injection
    answer: A
---
