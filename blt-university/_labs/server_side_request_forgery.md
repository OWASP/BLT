---
layout: lab
title: Server-Side Request Forgery (SSRF)
description: Advanced SSRF techniques to make servers request internal resources and cloud metadata services. Learn
  to bypass filters using encoding tricks and redirect chains.
difficulty: advanced
category: Web Security
estimated_time: 55
tasks:
- name: Introduction to SSRF
  description: Learn what SSRF attacks are, how they work, and their potential impact.
  type: theory
  order: 1
  heading: Introduction to SSRF
  content: |
    <h2>What is Server-Side Request Forgery (SSRF)?</h2>
    <p>SSRF is a vulnerability that allows attackers to trick a server into making unintended HTTP requests. The attacker controls the target URL or request destination and uses the server's privileges to access internal systems or sensitive data.</p>

    <h3>How SSRF Works</h3>
    <ol>
        <li>Web application accepts a URL or resource path as input.</li>
        <li>Server fetches that resource on behalf of the user.</li>
        <li>Attacker provides a crafted URL pointing to an internal or restricted resource.</li>
        <li>Server makes a request to the attacker-controlled or internal endpoint.</li>
    </ol>

    <h3>Example</h3>
    <pre><code>
    GET /fetch?url=http://internal-service/admin
    </code></pre>
    The attacker changes the URL to something like:
    <pre><code>
    GET /fetch?url=http://169.254.169.254/latest/meta-data/
    </code></pre>
    (This accesses AWS instance metadata.)

    <h3>Impact</h3>
    <ul>
        <li>Access internal networks</li>
        <li>Read cloud instance metadata</li>
        <li>Bypass firewalls</li>
        <li>Trigger internal POST requests to sensitive services</li>
    </ul>
  mcq:
    question: What is the main purpose of an SSRF attack?
    options:
    - A) Trick the server into making unauthorized requests
    - B) Steal client-side cookies
    - C) Modify HTML content of the user's browser
    - D) Exploit SQL databases directly
    answer: A
- name: Common SSRF Attack Scenarios
  description: Understand the types and sources of SSRF vulnerabilities in web applications.
  type: theory
  order: 2
  heading: Common SSRF Attack Scenarios
  content: |
    <h2>Common SSRF Scenarios</h2>
    <ul>
        <li><strong>Image URL Fetching:</strong> Application fetches remote image URLs for preview.</li>
        <li><strong>PDF Generation:</strong> Server fetches external content to embed.</li>
        <li><strong>Webhook / Callback URLs:</strong> API calls user-specified endpoints.</li>
        <li><strong>URL Shorteners:</strong> Follow attacker-controlled redirects.</li>
    </ul>

    <h3>Advanced Exploits</h3>
    <ul>
        <li>Access cloud metadata service: <code>http://169.254.169.254/</code></li>
        <li>Port scanning internal network via response timing.</li>
        <li>POST requests to internal admin panels.</li>
    </ul>
  mcq:
    question: Which of the following could be an SSRF entry point?
    options:
    - A) File upload feature
    - B) URL preview generator
    - C) Client-side JavaScript
    - D) HTML forms only
    answer: B
- name: Basic SSRF Attack - Internal Access
  description: Exploit a vulnerable endpoint that fetches URLs without validation.
  type: simulation
  order: 3
  simulation:
    type: basic_ssrf
    scenario: internal_metadata_access
    engine: ssrf-basic
    target_url: /fetch?url=
    vulnerable_code: |
      app.get('/fetch', async (req, res) => {
        const target = req.query.url;
        const response = await fetch(target);
        res.send(await response.text());
      });
    vulnerable_lines:
    - 3
    explain:
      question: Why can this reach cloud metadata?
      options:
      - id: arbitrary_fetch
        label: The server fetches any user-provided URL, including internal metadata addresses.
      - id: missing_css
        label: The fetched page has no stylesheet.
      answer: arbitrary_fetch
    expected_patterns:
    - host_allowlist
    - private_ip_blocking
    - redirect_restriction
    fix_starter_code: |
      app.get('/fetch', async (req, res) => {
        const target = req.query.url;
        const response = await fetch(target);
        res.send(await response.text());
      });
    vulnerable_parameters:
    - url
    success_payload: http://169.254.169.254/latest/meta-data/
    success_criteria: Fetch internal AWS metadata endpoint using /fetch?url parameter.
    hints:
    - Try targeting internal IPs such as 127.0.0.1 or 169.254.169.254
    - Experiment with the url parameter value
    - Observe server response for signs of internal access
    difficulty: beginner
- name: SSRF with Redirection
  description: Use open redirects or intermediate URLs to reach internal systems.
  type: simulation
  order: 4
  simulation:
    type: redirect_ssrf
    scenario: redirect_to_internal
    engine: ssrf-redirect
    target_url: /preview?url=
    vulnerable_code: |
      app.get('/preview', async (req, res) => {
        const url = new URL(req.query.url);
        const response = await fetch(url, { redirect: 'follow' });
        res.send(await response.text());
      });
    vulnerable_lines:
    - 3
    explain:
      question: Why do redirects matter for SSRF?
      options:
      - id: redirect_hop
        label: A trusted first URL can redirect the server to an internal host unless each hop is checked.
      - id: image_size
        label: Redirects only affect large images.
      answer: redirect_hop
    expected_patterns:
    - host_allowlist
    - private_ip_blocking
    - redirect_restriction
    fix_starter_code: |
      app.get('/preview', async (req, res) => {
        const url = new URL(req.query.url);
        const response = await fetch(url, { redirect: 'follow' });
        res.send(await response.text());
      });
    vulnerable_parameters:
    - url
    success_payload: http://evil.com/redirect?to=http://localhost:8080/admin
    success_criteria: Use a redirection chain to access an internal service through SSRF.
    hints:
    - Construct an attacker-hosted redirect
    - Chain redirect → internal host
    - Observe if the server follows redirects automatically
    difficulty: intermediate
- name: SSRF Bypass Filters - Using Encodings
  description: Bypass blacklist filters to reach internal hosts.
  type: simulation
  order: 5
  simulation:
    type: ssrf_bypass
    scenario: encoding_trick
    engine: ssrf-bypass
    target_url: /fetch?url=
    vulnerable_code: |
      app.get('/fetch', async (req, res) => {
        const url = req.query.url;
        if (!url.includes('127.0.0.1')) {
          res.send(await fetch(url).then(r => r.text()));
        }
      });
    vulnerable_lines:
    - 3
    - 4
    explain:
      question: Why is this blacklist bypassable?
      options:
      - id: encoded_host
        label: Internal hosts can be represented with alternate encodings, DNS names, or URL parser tricks.
      - id: no_scheme
        label: URLs cannot include schemes.
      answer: encoded_host
    expected_patterns:
    - url_parsing
    - host_allowlist
    - private_ip_blocking
    fix_starter_code: |
      app.get('/fetch', async (req, res) => {
        const url = req.query.url;
        if (!url.includes('127.0.0.1')) {
          res.send(await fetch(url).then(r => r.text()));
        }
      });
    vulnerable_parameters:
    - url
    success_payload: http://127.0.0.1@evil.com/
    success_criteria: Bypass SSRF filters using encoding, obfuscation, or DNS tricks.
    hints:
    - 'Try IPv6, decimal, hex: 0x7f000001'
    - 'Use @, # tricks to mask the internal host'
    - Try DNS rebinding or redirect-based payloads
    difficulty: advanced
- name: SSRF to RCE via Webhook
  description: Trigger server-side requests that execute commands on internal systems.
  type: simulation
  order: 6
  simulation:
    type: ssrf_rce
    scenario: webhook_rce
    engine: ssrf-webhook
    target_url: /webhook/test
    vulnerable_code: |
      app.post('/webhook/test', async (req, res) => {
        const target = req.body.target;
        const response = await request(target);
        res.send(response.body);
      });
    vulnerable_lines:
    - 3
    explain:
      question: Why can this reach internal admin actions?
      options:
      - id: internal_admin
        label: The server can be tricked into calling privileged internal endpoints that clients cannot reach directly.
      - id: missing_post
        label: POST requests cannot have bodies.
      answer: internal_admin
    expected_patterns:
    - host_allowlist
    - private_ip_blocking
    - redirect_restriction
    fix_starter_code: |
      app.post('/webhook/test', async (req, res) => {
        const target = req.body.target;
        const response = await request(target);
        res.send(response.body);
      });
    vulnerable_parameters:
    - target
    success_payload: http://localhost:8080/admin/run?cmd=whoami
    success_criteria: Trigger command execution by calling an internal admin endpoint.
    hints:
    - Use internal admin interfaces
    - Use query parameters to run commands
    - Observe the system's execution response
    difficulty: advanced
- name: SSRF Prevention Techniques
  description: Learn defenses against SSRF attacks.
  type: theory
  order: 7
  heading: SSRF Prevention Techniques
  content: |
    <h2>Preventing SSRF</h2>
    <ul>
        <li>Validate and whitelist URLs strictly (domain and protocol)</li>
        <li>Disallow internal IP ranges (127.0.0.1, 10.x.x.x, 169.254.x.x)</li>
        <li>Disable redirects or restrict them to trusted hosts</li>
        <li>Avoid fetching arbitrary URLs from user input</li>
        <li>Use SSRF-aware proxy services</li>
    </ul>

    <h3>Secure Example</h3>
    <pre><code>
    allowed_hosts = ["example.com", "api.trusted.com"]
    parsed = urlparse(user_url)
    if parsed.hostname not in allowed_hosts:
        raise ValueError("Untrusted URL")
    </code></pre>
  mcq:
    question: Which of these is an effective defense against SSRF?
    options:
    - A) Allowing all internal IPs
    - B) Whitelisting allowed domains
    - C) Disabling SSL verification
    - D) Following all redirects
    answer: B
---
