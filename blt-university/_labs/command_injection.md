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
    engine: command-basic
    type: ping_feature
    target_url: /safe-simulation
    vulnerable_code: |
      app.post('/ping', (req, res) => {
        const ip = req.body.ip_address;
        exec('ping -c 1 ' + ip, (error, stdout) => res.send(stdout));
      });
    vulnerable_lines:
    - 3
    explain:
      question: Why can the attacker run another command?
      options:
      - id: shell_concat
        label: User input is concatenated into a shell command, so separators can append commands.
      - id: missing_css
        label: The response is missing a stylesheet.
      answer: shell_concat
    expected_patterns:
    - separate_command_arguments
    - input_allowlist
    - shell_metacharacter_blocking
    fix_starter_code: |
      app.post('/ping', (req, res) => {
        const ip = req.body.ip_address;
        exec('ping -c 1 ' + ip, (error, stdout) => res.send(stdout));
      });
    vulnerable_parameters:
    - ip_address
    success_criteria: Execute a command that shows the current directory contents
    success_payload: 127.0.0.1; ls
    hints:
    - Use command separators like ; to chain commands
    difficulty: beginner
- name: Command Injection with Pipes
  description: Use pipe operators for command injection
  type: simulation
  order: 4
  simulation:
    scenario: ping_filter_semicolon
    engine: command-pipe
    type: ping_filter_semicolon
    target_url: /safe-simulation
    vulnerable_code: |
      app.post('/lookup', (req, res) => {
        const ip = req.body.ip_address.replace(';', '');
        exec('ping -c 1 ' + ip, (error, stdout) => res.send(stdout));
      });
    vulnerable_lines:
    - 3
    explain:
      question: Why is blocking only semicolons insufficient?
      options:
      - id: alternate_operator
        label: Other shell operators such as pipes can still change command execution.
      - id: too_many_packets
        label: Ping always sends too many packets.
      answer: alternate_operator
    expected_patterns:
    - separate_command_arguments
    - strict_ip_validation
    - shell_metacharacter_blocking
    fix_starter_code: |
      app.post('/lookup', (req, res) => {
        const ip = req.body.ip_address.replace(';', '');
        exec('ping -c 1 ' + ip, (error, stdout) => res.send(stdout));
      });
    vulnerable_parameters:
    - ip_address
    success_criteria: Execute a command that shows system information
    success_payload: 127.0.0.1 | uname -a
    hints:
    - Try the pipe operator (|) to feed output into commands
    difficulty: beginner
- name: Blind Command Injection
  description: Practice blind command injection techniques
  type: simulation
  order: 5
  simulation:
    scenario: blind_injection
    engine: command-blind
    type: blind_injection
    target_url: /safe-simulation
    vulnerable_code: |
      app.post('/health-check', (req, res) => {
        const ip = req.body.ip_address;
        execSync(`ping -c 1 ${ip}`);
        res.send('OK');
      });
    vulnerable_lines:
    - 3
    explain:
      question: Why can a time delay prove command injection?
      options:
      - id: blind_timing
        label: The injected command changes server response timing even when command output is hidden.
      - id: browser_cache
        label: Browser cache makes every request slower.
      answer: blind_timing
    expected_patterns:
    - separate_command_arguments
    - strict_ip_validation
    - shell_metacharacter_blocking
    fix_starter_code: |
      app.post('/health-check', (req, res) => {
        const ip = req.body.ip_address;
        execSync(`ping -c 1 ${ip}`);
        res.send('OK');
      });
    vulnerable_parameters:
    - ip_address
    success_criteria: Cause a measurable time delay
    success_payload: 127.0.0.1; sleep 5
    hints:
    - Use time delays like sleep to confirm injection
    difficulty: intermediate
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
    engine: command-filter-bypass
    type: filter_bypass
    target_url: /safe-simulation
    vulnerable_code: |
      app.post('/diag', (req, res) => {
        const ip = req.body.ip_address.replaceAll(' ', '');
        exec('ping -c 1 ' + ip, (error, stdout) => res.send(stdout));
      });
    vulnerable_lines:
    - 3
    explain:
      question: Why can encoding bypass this filter?
      options:
      - id: shell_expansion
        label: Shell expansions and alternate separators can restore spaces or command chaining after filtering.
      - id: invalid_route
        label: The route name is too short.
      answer: shell_expansion
    expected_patterns:
    - separate_command_arguments
    - strict_ip_validation
    - shell_metacharacter_blocking
    fix_starter_code: |
      app.post('/diag', (req, res) => {
        const ip = req.body.ip_address.replaceAll(' ', '');
        exec('ping -c 1 ' + ip, (error, stdout) => res.send(stdout));
      });
    vulnerable_parameters:
    - ip_address
    success_criteria: Execute a command that shows the current user
    success_payload: 127.0.0.1${IFS}&&${IFS}whoami
    hints:
    - Use ${IFS} instead of spaces to bypass filters
    difficulty: advanced
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
