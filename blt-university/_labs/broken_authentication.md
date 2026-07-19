---
layout: lab
title: Broken Authentication
description: Comprehensive coverage of authentication vulnerabilities including weak credentials, session management
  flaws, and JWT misconfigurations. Practice credential stuffing, session fixation, and token forgery attacks.
difficulty: intermediate
category: Authentication
estimated_time: 50
tasks:
- name: Introduction to Broken Authentication
  description: Overview of authentication failures, their causes, and impacts.
  type: theory
  order: 1
  heading: Introduction to Broken Authentication
  content: |
    <h2>What is Broken Authentication?</h2>
    <p>Broken Authentication refers to weaknesses in authentication and session management that allow attackers to compromise passwords or impersonate users.</p>

    <h3>Common Issues</h3>
    <ul>
        <li>Weak/default passwords</li>
        <li>Brute-force or credential stuffing</li>
        <li>Predictable session IDs</li>
        <li>Insecure password reset flows</li>
        <li>JWT misconfigurations (alg=none)</li>
    </ul>
  mcq:
    question: Which control mitigates credential stuffing?
    options:
    - A) Unlimited login attempts
    - B) Progressive rate-limiting and lockouts
    - C) Client-side only validation
    - D) Remove password complexity rules
    answer: B
- name: Default & Weak Credentials
  description: Why default credentials are dangerous.
  type: theory
  order: 2
  heading: Default & Weak Credentials
  content: |
    <h2>Default Credentials</h2>
    <p>Attackers try common default passwords like admin/admin.</p>
    <h3>Prevention</h3>
    <ul>
        <li>Force password change at first login</li>
        <li>Strong password requirements</li>
        <li>Use MFA</li>
    </ul>
  mcq:
    question: What reduces risk of default credentials?
    options:
    - A) Force credential change on first use
    - B) Publish default passwords publicly
    - C) Use same default creds everywhere
    - D) Disable logs
    answer: A
- name: 'Simulation: Login with Default Credentials'
  description: Log in with a simulated default credential pair.
  type: simulation
  order: 3
  simulation:
    type: auth_default_creds
    scenario: default_login
    engine: auth-default-creds
    target_url: /login
    vulnerable_code: |
      const users = [
        { username: 'admin', password: 'admin', mustChangePassword: false }
      ];
      app.post('/login', (req, res) => login(req.body.username, req.body.password));
    vulnerable_lines:
    - 2
    - 4
    explain:
      question: Why can the admin account be compromised?
      options:
      - id: default_password
        label: A known default password remains active and there is no forced password change.
      - id: missing_logo
        label: The login page does not display a logo.
      answer: default_password
    expected_patterns:
    - password_policy
    - default_credential_rotation
    - rate_limiting
    fix_starter_code: |
      const users = [
        { username: 'admin', password: 'admin', mustChangePassword: false }
      ];
      app.post('/login', (req, res) => login(req.body.username, req.body.password));
    vulnerable_parameters:
    - username
    - password
    success_payload: username=admin&password=admin
    success_criteria: Admin login without changing default credentials.
    hints:
    - Try admin/admin
    - Try admin/password
    difficulty: beginner
- name: Session Fixation & Session Management
  description: Understand why session IDs must rotate after login.
  type: theory
  order: 4
  heading: Session Fixation & Session Management
  content: |
    <h2>Session Fixation</h2>
    <p>Attacker gives user a session ID, and it remains valid after login.</p>
    <h3>Mitigation</h3>
    <ul>
        <li>Rotate session ID after login</li>
        <li>Secure cookie flags</li>
        <li>Invalidate sessions on logout</li>
    </ul>
  mcq:
    question: How to prevent session fixation?
    options:
    - A) Keep the same session ID
    - B) Rotate session ID after login
    - C) Store ID in URL
    - D) Disable cookie flags
    answer: B
- name: 'Simulation: Session Fixation Reuse'
  description: Provide a fixed session ID and use it after login.
  type: simulation
  order: 5
  simulation:
    type: session_fixation
    scenario: fixation_reuse
    engine: auth-session-fixation
    target_url: /login
    vulnerable_code: |
      app.post('/login', (req, res) => {
        if (validPassword(req.body)) {
          req.session.userId = user.id;
          res.redirect('/admin');
        }
      });
    vulnerable_lines:
    - 3
    explain:
      question: Why is this session fixation-prone?
      options:
      - id: no_rotation
        label: The app keeps the existing session ID after login instead of rotating it.
      - id: no_username
        label: The username field is missing from the request.
      answer: no_rotation
    expected_patterns:
    - session_rotation
    - secure_cookie_flags
    - login_rate_limit
    fix_starter_code: |
      app.post('/login', (req, res) => {
        if (validPassword(req.body)) {
          req.session.userId = user.id;
          res.redirect('/admin');
        }
      });
    vulnerable_parameters:
    - sessionid
    success_payload: sessionid=fixed-session-0001
    success_criteria: Reuse same sessionid after login to access protected page.
    hints:
    - Set sessionid first
    - Log in and reuse sessionid
    difficulty: intermediate
- name: JWT Misconfiguration (alg=none)
  description: Learn about forging JWTs when signature isn't checked.
  type: theory
  order: 6
  heading: JWT Misconfiguration (alg=none)
  content: |
    <h2>JWT Pitfalls</h2>
    <p>Accepting alg=none or weak secrets allows forging tokens.</p>
    <h3>Fixes</h3>
    <ul>
        <li>Reject alg=none</li>
        <li>Validate signature always</li>
        <li>Use strong secrets + rotate periodically</li>
    </ul>
  mcq:
    question: Which vulnerability allows unsigned JWTs?
    options:
    - A) Short expiration
    - B) Accepting alg=none
    - C) Using strong RSA keys
    - D) Validating payload
    answer: B
- name: 'Simulation: Forge JWT for Admin Access'
  description: Craft admin JWT (alg=none or weak-secret).
  type: simulation
  order: 7
  simulation:
    type: jwt_forge
    scenario: jwt_admin
    engine: auth-jwt-none
    target_url: /admin
    vulnerable_code: |
      app.get('/admin', (req, res) => {
        const token = req.headers.authorization;
        const claims = jwt.decode(token);
        if (claims.role === 'admin') res.send('admin');
      });
    vulnerable_lines:
    - 3
    explain:
      question: Why can an unsigned token work here?
      options:
      - id: no_signature
        label: The token is decoded without verifying its signature or allowed algorithm.
      - id: expired_css
        label: The stylesheet cache expired.
      answer: no_signature
    expected_patterns:
    - jwt_signature_verification
    - algorithm_allowlist
    - token_expiry
    fix_starter_code: |
      app.get('/admin', (req, res) => {
        const token = req.headers.authorization;
        const claims = jwt.decode(token);
        if (claims.role === 'admin') res.send('admin');
      });
    vulnerable_parameters:
    - Authorization
    success_payload: "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJyb2xlIjoiYWRtaW4ifQ."
    success_criteria: Access /admin using forged token.
    hints:
    - Set alg:none
    - Remove signature or use weak-secret
    difficulty: intermediate
- name: Password Reset Flaws
  description: Weak reset tokens, long lifetime, predictable values.
  type: theory
  order: 8
  heading: Password Reset Flaws
  content: |
    <h2>Password Reset Risks</h2>
    <ul>
        <li>Predictable or short tokens</li>
        <li>Long-lived reset links</li>
        <li>Tokens exposed in URLs/logs</li>
    </ul>
    <h3>Best Practices</h3>
    <ul>
        <li>Short-lived, single-use tokens</li>
        <li>Server-side validation</li>
        <li>Rate-limit attempts</li>
    </ul>
  mcq:
    question: Which is secure practice?
    options:
    - A) Long-lived tokens
    - B) Single-use short-lived tokens
    - C) Embed reset token in GET URL
    - D) Reuse tokens
    answer: B
- name: 'Simulation: Guess Weak Reset Token'
  description: Guess short predictable token to reset password.
  type: simulation
  order: 9
  simulation:
    type: password_reset_guess
    scenario: guess_reset_token
    engine: auth-reset-token
    target_url: /reset-password?token=
    vulnerable_code: |
      app.post('/reset-password', (req, res) => {
        const token = req.query.token;
        if (token.length === 4) resetPassword(token, req.body.password);
        res.send('reset');
      });
    vulnerable_lines:
    - 3
    explain:
      question: Why can this reset token be guessed?
      options:
      - id: weak_token
        label: The token is short, predictable, and not checked for expiry or single use.
      - id: long_form
        label: The reset form has too many fields.
      answer: weak_token
    expected_patterns:
    - cryptographic_random_token
    - single_use_token
    - token_expiry
    fix_starter_code: |
      app.post('/reset-password', (req, res) => {
        const token = req.query.token;
        if (token.length === 4) resetPassword(token, req.body.password);
        res.send('reset');
      });
    vulnerable_parameters:
    - token
    success_payload: token=AB12
    success_criteria: Submit valid simulated token and reset password.
    hints:
    - Try small alphanumeric combinations
    - Lab only simulates tiny safe token space
    difficulty: intermediate
- name: Brute-Force & Rate-Limiting Controls
  description: Why progressive delays and lockouts stop brute-force.
  type: theory
  order: 10
  heading: Brute-Force & Rate-Limiting Controls
  content: |
    <h2>Brute-force Defenses</h2>
    <ul>
        <li>Rate-limiting per IP/account</li>
        <li>Progressive delay after failures</li>
        <li>MFA</li>
    </ul>
  mcq:
    question: Which helps block credential stuffing?
    options:
    - A) Unlimited retries
    - B) Per-account/IP rate-limiting + delays
    - C) Client-side only validation
    - D) Logout users constantly
    answer: B
- name: 'Simulation: Brute-Force with Rate-Limit'
  description: Simulated brute-force with lockout logic.
  type: simulation
  order: 11
  simulation:
    type: bruteforce_sim
    scenario: rate_limit_test
    engine: auth-rate-limit
    target_url: /login
    vulnerable_code: |
      app.post('/login', (req, res) => {
        const user = findUser(req.body.username);
        if (user && checkPassword(user, req.body.password)) {
          createSession(user);
        }
      });
    vulnerable_lines:
    - 3
    explain:
      question: Why can attackers keep guessing credentials?
      options:
      - id: unlimited_attempts
        label: The login flow checks passwords without rate limits, lockouts, or progressive delay.
      - id: no_redirect
        label: The login flow does not redirect after failure.
      answer: unlimited_attempts
    expected_patterns:
    - rate_limiting
    - account_lockout
    - password_hashing
    fix_starter_code: |
      app.post('/login', (req, res) => {
        const user = findUser(req.body.username);
        if (user && checkPassword(user, req.body.password)) {
          createSession(user);
        }
      });
    vulnerable_parameters:
    - username
    - password
    success_payload: username=victim&password=P@ssw0rd!
    success_criteria: Find valid credential while respecting simulated rate limits.
    hints:
    - Small controlled attempts
    - Lab simulates lockout
    difficulty: advanced
- name: Authentication Remediation & Best Practices
  description: Final summary of secure approaches.
  type: theory
  order: 12
  heading: Authentication Remediation & Best Practices
  content: |
    <h2>Remediation Checklist</h2>
    <ul>
        <li>Strong passwords + MFA</li>
        <li>Session rotation on login</li>
        <li>Strict JWT validation</li>
        <li>Brute-force protections</li>
        <li>Secure password reset tokens</li>
    </ul>
  mcq:
    question: Which improves authentication security?
    options:
    - A) Weak passwords + long-lived tokens
    - B) MFA + rate-limiting + session rotation
    - C) No logging
    - D) Reuse tokens everywhere
    answer: B
---
