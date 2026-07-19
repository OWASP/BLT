---
layout: lab
title: Sensitive Data Exposure
description: Discover how applications inadvertently expose sensitive information through misconfigurations and
  poor security practices. Learn to identify leaked credentials, API keys, and personal data in error messages,
  backups, and client-side code.
difficulty: intermediate
category: Data Protection
estimated_time: 40
tasks:
- name: Introduction to Sensitive Data Exposure
  description: Understand what sensitive data exposure is, why it matters, and common sources of leaks.
  type: theory
  order: 1
  heading: Introduction to Sensitive Data Exposure
  content: |
    <h2>What is Sensitive Data Exposure?</h2>
    <p>Sensitive Data Exposure occurs when applications, APIs, or servers fail to adequately protect confidential information such as credentials, API keys, personal data, or cryptographic keys.</p>

    <h3>Common sensitive data types</h3>
    <ul>
      <li>Passwords and password hashes</li>
      <li>API keys, tokens, and secrets</li>
      <li>Personally Identifiable Information (PII)</li>
      <li>Encryption keys and certificates</li>
      <li>Internal configuration and debug data</li>
    </ul>

    <h3>Typical sources of exposure</h3>
    <ul>
      <li>Misconfigured storage (public S3 buckets, exposed directories)</li>
      <li>Verbose error messages or stack traces</li>
      <li>Unencrypted transmissions (HTTP instead of HTTPS)</li>
      <li>Leftover files (.git, backups) on web root</li>
      <li>Logging secrets to accessible logs</li>
    </ul>
  mcq:
    question: Which of the following is a primary risk from sensitive data exposure?
    options:
    - A) Faster page loads
    - B) Credential theft and service compromise
    - C) Improved SEO
    - D) Reduced disk usage
    answer: B
- name: 'Data-in-Transit: TLS and Transport Security'
  description: Learn about protecting data during transport and common TLS misconfigurations.
  type: theory
  order: 2
  heading: 'Data-in-Transit: TLS and Transport Security'
  content: |
    <h2>Protecting Data in Transit</h2>
    <p>Use TLS to encrypt data between clients and servers.</p>
    <ul>
        <li>Enforce TLS 1.2+ and disable insecure ciphers</li>
        <li>Use HSTS</li>
        <li>Redirect HTTP to HTTPS and validate certificates</li>
    </ul>
  mcq:
    question: Which practice helps protect data in transit?
    options:
    - A) Serving sensitive API over HTTP
    - B) Enforcing HTTPS with HSTS
    - C) Embedding credentials in query strings
    - D) Using self-signed certificates in production
    answer: B
- name: Leakage via Debug/Error Messages (Simulation)
  description: Simulate leaking secrets in verbose error pages.
  type: simulation
  order: 3
  simulation:
    type: error_leak
    scenario: stack_trace_disclosure
    engine: sensitive-error
    target_url: /user/profile?show=error
    vulnerable_code: |
      app.get('/user/profile', (req, res) => {
        try {
          loadProfile(req.user.id);
        } catch (error) {
          res.status(500).send(error.stack + '\nDB_PASSWORD=' + process.env.DB_PASSWORD);
        }
      });
    vulnerable_lines:
    - 5
    explain:
      question: Why does this expose sensitive data?
      options:
      - id: verbose_error
        label: The error response includes stack details and a raw secret.
      - id: missing_avatar
        label: The profile does not include an avatar.
      answer: verbose_error
    expected_patterns:
    - error_redaction
    - secret_manager
    - safe_logging
    fix_starter_code: |
      app.get('/user/profile', (req, res) => {
        try {
          loadProfile(req.user.id);
        } catch (error) {
          res.status(500).send(error.stack + '\nDB_PASSWORD=' + process.env.DB_PASSWORD);
        }
      });
    vulnerable_parameters:
    - show
    success_payload: Trigger a stack trace showing 'DB_PASSWORD=secret_db_pass'
    success_criteria: Simulated trace reveals safe example of a secret.
    hints:
    - Try show=error
    - Look for debug endpoints
    difficulty: beginner
- name: Exposed Backup/.git or Public Files (Simulation)
  description: Simulate exposed config or repository files revealing secrets.
  type: simulation
  order: 4
  simulation:
    type: file_exposure
    scenario: exposed_git
    engine: sensitive-file
    target_url: /.git/HEAD
    vulnerable_code: |
      app.use('/.git', express.static(path.join(__dirname, '.git')));
      app.use('/backup', express.static(path.join(__dirname, 'backup')));
      app.get('/backup/config.bak', (req, res) => res.sendFile('/app/backup/config.bak'));
    vulnerable_lines:
    - 1
    - 2
    - 3
    explain:
      question: Why are public backup and repository files dangerous?
      options:
      - id: public_secret_files
        label: Public static routes can expose config, keys, and repository metadata.
      - id: no_cache
        label: Static files cannot be cached.
      answer: public_secret_files
    expected_patterns:
    - deny_sensitive_paths
    - authorization_required
    - secret_manager
    fix_starter_code: |
      app.use('/.git', express.static(path.join(__dirname, '.git')));
      app.use('/backup', express.static(path.join(__dirname, 'backup')));
      app.get('/backup/config.bak', (req, res) => res.sendFile('/app/backup/config.bak'));
    vulnerable_parameters: []
    success_payload: Access /.git/config or backup/config.bak and find simulated AWS key
    success_criteria: Retrieve simulated config with safe example key
    hints:
    - Try /.git/HEAD
    - /backup/config.bak
    - /config/.env
    difficulty: intermediate
- name: API Key / Secret in JavaScript or HTML (Simulation)
  description: Simulate discovering secrets embedded in static files.
  type: simulation
  order: 5
  simulation:
    type: asset_leak
    scenario: frontend_key_disclosure
    engine: sensitive-asset
    target_url: /static/js/app.js
    vulnerable_code: |
      window.APP_CONFIG = {
        apiBase: 'https://api.example',
        API_KEY: 'AKIA...EXAMPLE'
      };
    vulnerable_lines:
    - 3
    explain:
      question: Why should this key not be shipped to the browser?
      options:
      - id: client_secret
        label: Any secret embedded in JavaScript can be read by every visitor.
      - id: missing_bundle
        label: JavaScript cannot define configuration.
      answer: client_secret
    expected_patterns:
    - remove_client_secret
    - backend_proxy
    - secret_manager
    fix_starter_code: |
      window.APP_CONFIG = {
        apiBase: 'https://api.example',
        API_KEY: 'AKIA...EXAMPLE'
      };
    vulnerable_parameters: []
    success_payload: Find 'API_KEY = "AKIA...EXAMPLE"'
    success_criteria: Locate simulated hardcoded API key
    hints:
    - Inspect JS/CSS
    - Search for TOKEN or KEY strings
    difficulty: beginner
- name: 'Insecure Storage: Plaintext Secrets (Simulation)'
  description: Simulate plaintext stored credentials.
  type: simulation
  order: 6
  simulation:
    type: storage_plaintext
    scenario: plaintext_passwords
    engine: sensitive-storage
    target_url: /admin/export-users
    vulnerable_code: |
      app.get('/admin/export-users', requireAdmin, (req, res) => {
        const rows = users.map(user => `${user.email},${user.password}`);
        res.send(rows.join('\n'));
      });
    vulnerable_lines:
    - 2
    - 3
    explain:
      question: Why is this export unsafe?
      options:
      - id: plaintext_export
        label: Passwords are stored or exported in plaintext instead of being hashed and protected.
      - id: csv_format
        label: CSV files cannot contain email addresses.
      answer: plaintext_export
    expected_patterns:
    - password_hashing
    - authorization_required
    - sensitive_field_redaction
    fix_starter_code: |
      app.get('/admin/export-users', requireAdmin, (req, res) => {
        const rows = users.map(user => `${user.email},${user.password}`);
        res.send(rows.join('\n'));
      });
    vulnerable_parameters: []
    success_payload: Download simulated CSV with plaintext password example
    success_criteria: Reveal plaintext or weak-hash example
    hints:
    - Try admin/export endpoints
    difficulty: intermediate
- name: Token Replay & Poorly Scoped Tokens
  description: 'Theory: long-lived tokens & overly broad scopes.'
  type: theory
  order: 7
  heading: Token Replay & Poorly Scoped Tokens
  content: |
    <h2>Token Risks</h2>
    <p>Tokens should expire fast, be scoped, and revocable.</p>
    <ul>
        <li>Short expiry</li>
        <li>Minimal permissions</li>
        <li>Revocation & monitoring</li>
    </ul>
  mcq:
    question: Which reduces the blast radius if a key is leaked?
    options:
    - A) Long-lived, broad tokens
    - B) Short-lived minimal scope tokens
    - C) Hardcode secrets
    - D) Reuse same key everywhere
    answer: B
- name: Prevention & Remediation Best Practices
  description: Learn controls to prevent leaks.
  type: theory
  order: 8
  heading: Prevention & Remediation Best Practices
  content: |
    <h2>Remediation & Prevention</h2>
    <ul>
      <li>Encrypt at rest + in transit</li>
      <li>Use secrets managers</li>
      <li>Do not store secrets in repos</li>
      <li>Limit PII and retention</li>
    </ul>
  mcq:
    question: Which is a secure way to manage secrets?
    options:
    - A) Put secrets in git
    - B) Use a secrets manager
    - C) Store plaintext secrets in web root
    - D) Hardcode in source
    answer: B
- name: Sensitive Data Exposure Challenge - Safe Remediation
  description: 'Simulation: find exposed secret & provide remediation text.'
  type: simulation
  order: 9
  simulation:
    type: remediation_plan
    scenario: identify_and_remediate
    engine: sensitive-remediation
    target_url: /.env
    vulnerable_code: |
      app.get('/.env', (req, res) => {
        logger.info('Serving SECRET_KEY=' + process.env.SECRET_KEY);
        res.type('text/plain').send('SECRET_KEY=' + process.env.SECRET_KEY);
      });
    vulnerable_lines:
    - 2
    - 3
    explain:
      question: What must happen after a secret is exposed?
      options:
      - id: rotate_revoke
        label: Remove the exposure, rotate or revoke the secret, and move it to managed storage.
      - id: ignore_secret
        label: Keep using the secret because it was only exposed once.
      answer: rotate_revoke
    expected_patterns:
    - secret_rotation
    - secret_manager
    - redacted_logging
    fix_starter_code: |
      app.get('/.env', (req, res) => {
        logger.info('Serving SECRET_KEY=' + process.env.SECRET_KEY);
        res.type('text/plain').send('SECRET_KEY=' + process.env.SECRET_KEY);
      });
    vulnerable_parameters: []
    success_payload: Find simulated SECRET_KEY and provide remediation steps
    success_criteria: User mentions rotate, revoke, secrets manager
    hints:
    - Search for exposed /.env
    - Provide fix steps
    difficulty: advanced
---
