---
layout: lab
title: Cross-Site Scripting (XSS)
description: Learn XSS through interactive browser security exercises.
difficulty: beginner
category: Web Security
estimated_time: 50

tasks:
  - name: Introduction to Cross-Site Scripting
    description: Learn the basics of XSS vulnerabilities and how they occur in web applications.
    type: theory
    order: 1
    heading: What is Cross-Site Scripting (XSS)?
    content: |
      Cross-Site Scripting (XSS) is a security vulnerability that allows attackers to inject malicious scripts into web pages viewed by other users. When executed, these scripts can steal sensitive information, manipulate page content, or perform actions on behalf of the victim.

      ### Types of XSS Attacks

      - **Reflected XSS:** Malicious script is reflected off a web server, such as in an error message.
      - **Stored XSS:** Malicious script is stored on the target server, such as in a database.
      - **DOM-based XSS:** The vulnerability exists in client-side code rather than server-side code.

      ### Common XSS Payloads

      ```html
      <script>alert('XSS')</script>
      <img src=x onerror=alert('XSS')>
      <svg onload=alert('XSS')>
      ```

      ### Impact of XSS

      - Session hijacking and cookie theft
      - Defacement of web pages
      - Redirecting users to malicious sites
      - Keylogging and credential theft
    mcq:
      question: Which type of XSS vulnerability stores malicious scripts on the server?
      options:
        - A) Reflected XSS
        - B) Stored XSS
        - C) DOM-based XSS
        - D) Session XSS
      answer: B

  - name: Identifying XSS Vulnerabilities
    description: Learn how to identify potential XSS vulnerabilities in web applications.
    type: theory
    order: 2
    heading: How to Identify XSS Vulnerabilities
    content: |
      XSS vulnerabilities typically occur when user input is not properly validated, sanitized, or encoded before being displayed on a web page.

      ### Common Vulnerable Input Points

      - Search boxes and form fields
      - URL parameters
      - Comment sections
      - User profile fields
      - HTTP headers, such as User-Agent and Referer

      ### Testing for XSS

      1. Insert test payloads in input fields.
      2. Check if the payload is reflected in the response.
      3. Verify if the script executes in the browser.
      4. Test different encoding and bypasses.

      ### Example Vulnerable Code

      ```php
      // Vulnerable PHP code
      echo "Hello " . $_GET['name'];
      ```

      ```javascript
      // Vulnerable JavaScript
      document.getElementById('output').innerHTML = userInput;
      ```
    mcq:
      question: Which of the following is the most common place to test for XSS vulnerabilities?
      options:
        - A) Database connections
        - B) User input fields
        - C) Server configuration files
        - D) Network protocols
      answer: B

  - name: Reflected XSS - Comment System
    description: Practice exploiting reflected XSS in a vulnerable comment system.
    type: simulation
    order: 3
    simulation:
      engine: xss-reflected
      type: reflected_xss
      scenario: vulnerable_blog
      target_url: /xss-lab/blog
      vulnerable_code: |
        const comment = request.query.comment;
        const preview = document.getElementById('comment-preview');
        preview.innerHTML = comment;
      vulnerable_lines:
        - 3
      explain:
        question: Why does this reflected XSS payload execute?
        options:
          - id: unsafe_html_sink
            label: The comment is inserted with innerHTML, so browser parses attacker-controlled HTML.
          - id: missing_database
            label: The application does not store comments in a database.
          - id: weak_password
            label: The user password is too weak.
        answer: unsafe_html_sink
      expected_patterns:
        - safe_text_sink
        - output_encoding
      attack_payloads:
        - "<script>alert('XSS')</script>"
      vulnerable_parameters:
        - comment
      success_payload: "<script>alert('XSS')</script>"
      success_criteria: JavaScript alert should execute showing 'XSS'.
      difficulty: beginner
      fix_starter_code: |
        const comment = request.query.comment;
        const preview = document.getElementById('comment-preview');
        preview.innerHTML = comment;
      hints:
        - Try injecting a simple script tag in the comment field.
        - The application does not sanitize user input.
        - Look for ways to execute JavaScript when the page loads.
        - Use textContent or encode HTML before displaying user-controlled comments.

  - name: Stored XSS - User Profile
    description: Exploit stored XSS by injecting scripts into profile fields.
    type: simulation
    order: 4
    simulation:
      engine: xss-stored
      type: stored_xss
      scenario: vulnerable_profile
      target_url: /xss-lab/profile
      vulnerable_code: |
        const bio = user.profile.bio;
        const profileBio = document.getElementById('profile-bio');
        profileBio.innerHTML = bio;
      vulnerable_lines:
        - 3
      explain:
        question: Why is stored XSS more dangerous for other users?
        options:
          - id: persistent_payload
            label: The payload is saved and later rendered for every user who views the profile.
          - id: only_local_browser
            label: The payload only affects the attacker's browser.
          - id: database_index
            label: The database index executes JavaScript.
        answer: persistent_payload
      expected_patterns:
        - safe_text_sink
        - output_encoding
      attack_payloads:
        - "<script>alert('Stored XSS')</script>"
      vulnerable_parameters:
        - bio
      success_payload: "<script>alert('Stored XSS')</script>"
      success_criteria: Script executes when profile is viewed.
      difficulty: intermediate
      fix_starter_code: |
        const bio = user.profile.bio;
        const profileBio = document.getElementById('profile-bio');
        profileBio.innerHTML = bio;
      hints:
        - Try updating your profile bio with a script.
        - The script should execute when anyone views your profile.
        - This is stored XSS, so it persists in the database.

  - name: XSS Filter Bypass - Basic
    description: Learn to bypass basic XSS filters and input validation.
    type: simulation
    order: 5
    simulation:
      engine: xss-filter-bypass
      type: filter_bypass
      scenario: filtered_input
      target_url: /xss-lab/filtered
      vulnerable_code: |
        const search = request.query.search;
        const filtered = search.replace('<script>', '').replace('javascript:', '').replace('onerror', '');
        document.getElementById('result').innerHTML = filtered;
      vulnerable_lines:
        - 3
      explain:
        question: Why can this basic filter be bypassed?
        options:
          - id: blocklist_incomplete
            label: It blocks a few exact strings but still renders attacker-controlled HTML.
          - id: no_database
            label: The page does not use a database.
          - id: css_only
            label: XSS only works inside CSS files.
        answer: blocklist_incomplete
      expected_patterns:
        - safe_text_sink
        - output_encoding
      attack_payloads:
        - "<svg onload=alert('Bypass')>"
      vulnerable_parameters:
        - search
      blocked_patterns:
        - <script>
        - "javascript:"
        - onerror
      success_payload: "<svg onload=alert('Bypass')>"
      success_criteria: Successfully bypass the filter and execute JavaScript.
      difficulty: intermediate
      fix_starter_code: |
        const search = request.query.search;
        const filtered = search.replace('<script>', '').replace('javascript:', '').replace('onerror', '');
        document.getElementById('result').innerHTML = filtered;
      hints:
        - Try using different case variations.
        - Some filters only block exact matches.
        - Unicode encoding might help bypass filters.
        - Look for alternative event handlers.

  - name: DOM-based XSS
    description: Exploit DOM-based XSS vulnerabilities in client-side JavaScript.
    type: simulation
    order: 6
    simulation:
      engine: xss-dom
      type: dom_xss
      scenario: client_side_vuln
      target_url: /xss-lab/dom
      vulnerable_code: |
        const fragment = decodeURIComponent(location.hash.slice(1));
        const output = document.getElementById('fragment-output');
        output.innerHTML = fragment;
      vulnerable_lines:
        - 3
      explain:
        question: Why is this DOM-based XSS?
        options:
          - id: client_side_sink
            label: Client-side JavaScript reads the URL fragment and writes it into an HTML sink.
          - id: server_database
            label: The server stores the fragment in a database.
          - id: weak_tls
            label: TLS is not configured.
        answer: client_side_sink
      expected_patterns:
        - safe_text_sink
        - output_encoding
      attack_payloads:
        - "<img src=x onerror=alert('DOM XSS')>"
      vulnerable_parameters:
        - fragment
      success_payload: "<img src=x onerror=alert('DOM XSS')>"
      success_criteria: Execute JavaScript through DOM manipulation.
      difficulty: advanced
      fix_starter_code: |
        const fragment = decodeURIComponent(location.hash.slice(1));
        const output = document.getElementById('fragment-output');
        output.innerHTML = fragment;
      hints:
        - This vulnerability exists in client-side JavaScript.
        - Try manipulating the URL fragment after #.
        - The page dynamically updates content based on the fragment.
        - No server-side filtering is involved.

  - name: XSS Cookie Theft
    description: Learn to steal cookies using XSS vulnerabilities.
    type: simulation
    order: 7
    simulation:
      engine: xss-cookie-theft
      type: cookie_theft
      scenario: session_hijacking
      target_url: /xss-lab/cookies
      vulnerable_code: |
        const message = request.query.message;
        const banner = document.getElementById('message-banner');
        banner.innerHTML = message;
      vulnerable_lines:
        - 3
      explain:
        question: How can XSS lead to cookie theft?
        options:
          - id: script_reads_cookie
            label: Executed script can read cookies that are accessible to JavaScript and expose session data.
          - id: cookies_are_sql
            label: Cookies are SQL queries.
          - id: images_store_cookies
            label: Image files automatically store passwords.
        answer: script_reads_cookie
      expected_patterns:
        - safe_text_sink
        - output_encoding
      attack_payloads:
        - "<script>alert(document.cookie)</script>"
      vulnerable_parameters:
        - message
      success_payload: "<script>alert(document.cookie)</script>"
      success_criteria: Display session cookie value.
      difficulty: intermediate
      fix_starter_code: |
        const message = request.query.message;
        const banner = document.getElementById('message-banner');
        banner.innerHTML = message;
      hints:
        - Use document.cookie to access session cookies.
        - Try displaying the cookie value in an alert.
        - In real attacks, cookies would be sent to an attacker's server.
        - This demonstrates the impact of XSS on session security.

  - name: XSS Prevention Techniques
    description: Learn about effective methods to prevent XSS vulnerabilities.
    type: theory
    order: 8
    heading: XSS Prevention Techniques
    content: |
      Preventing XSS requires a multi-layered approach combining input validation, output encoding, and security headers.

      ### Input Validation

      - Whitelist allowed characters and patterns
      - Reject or sanitize dangerous input
      - Validate on both client and server side

      ### Output Encoding

      - HTML encode user data before display
      - JavaScript encode for JS contexts
      - URL encode for URL contexts
      - CSS encode for style contexts

      ### Content Security Policy (CSP)

      ```http
      Content-Security-Policy: default-src 'self'; script-src 'self'; object-src 'none'
      ```

      ### Secure Coding Practices

      - Use template engines with auto-escaping
      - Avoid `innerHTML` for dynamic content
      - Set the `HttpOnly` flag on session cookies
      - Implement proper error handling
    mcq:
      question: Which HTTP header helps prevent XSS attacks by controlling resource loading?
      options:
        - A) X-Frame-Options
        - B) Content-Security-Policy
        - C) X-XSS-Protection
        - D) Strict-Transport-Security
      answer: B
---
