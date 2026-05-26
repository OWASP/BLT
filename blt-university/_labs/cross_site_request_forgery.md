---
layout: lab
title: Cross-Site Request Forgery
description: Learn CSRF attacks and defenses through focused security exercises.
difficulty: beginner
category: Web Security
estimated_time: 45

tasks:
  - name: Introduction to CSRF
    description: Learn the fundamentals of Cross-Site Request Forgery attacks and their impact.
    type: theory
    order: 1
    heading: What is Cross-Site Request Forgery (CSRF)?
    content: |
      Cross-Site Request Forgery (CSRF) is an attack that forces authenticated users to submit unintended requests to a web application. The attacker tricks the victim into executing unwanted actions on a web application where they are currently authenticated.

      ### How CSRF Works

      1. User logs into a legitimate website, such as online banking.
      2. User visits a malicious website while still logged in.
      3. Malicious site sends a request to the legitimate site using the user's session.
      4. The legitimate site processes the request as if the user intended it.

      ### Common CSRF Attack Vectors

      - **HTML Forms:** Auto-submitting forms with hidden fields
      - **Image Tags:** Using `img src` to trigger GET requests
      - **JavaScript:** AJAX requests from malicious sites
      - **Links:** Tricking users to click malicious links

      ### Example CSRF Attack

      ```html
      <!-- Malicious HTML page -->
      <form action="https://bank.com/transfer" method="POST" id="csrf-form">
          <input type="hidden" name="amount" value="1000">
          <input type="hidden" name="to_account" value="attacker_account">
      </form>
      <script>document.getElementById('csrf-form').submit();</script>
      ```

      ### Impact of CSRF

      - Unauthorized fund transfers
      - Account settings changes
      - Password modifications
      - Data deletion or modification
    mcq:
      question: What is required for a CSRF attack to be successful?
      options:
        - A) The victim must visit a malicious website
        - B) The victim must be authenticated to the target site
        - C) The target site must lack CSRF protection
        - D) All of the above
      answer: D

  - name: CSRF Protection Mechanisms
    description: Learn about different methods to prevent CSRF attacks.
    type: theory
    order: 2
    heading: CSRF Protection Mechanisms
    content: |
      There are several effective methods to prevent CSRF attacks. The key is to ensure that requests genuinely originate from the authenticated user.

      ### 1. CSRF Tokens

      The most common and effective protection method:

      - Generate a unique, unpredictable token for each session
      - Include the token in all state-changing requests
      - Verify the token on the server before processing requests

      ```html
      <form method="POST">
          <input type="hidden" name="csrf_token" value="abc123xyz789">
          <input type="text" name="email">
          <button type="submit">Update Email</button>
      </form>
      ```

      ### 2. SameSite Cookie Attribute

      Prevents cookies from being sent with cross-site requests:

      ```http
      Set-Cookie: sessionid=abc123; SameSite=Strict
      Set-Cookie: sessionid=abc123; SameSite=Lax
      ```

      ### 3. Origin and Referer Headers

      Verify that requests come from the expected origin:

      - Check the Origin header matches your domain
      - Validate the Referer header, though it is less reliable

      ### 4. Double Submit Cookie

      Store CSRF token in both a cookie and request parameter:

      - Set CSRF token as a cookie
      - Include the same token in a form or header
      - Verify both values match
    mcq:
      question: Which CSRF protection method is considered the most secure?
      options:
        - A) Checking Referer header only
        - B) Using SameSite=Lax cookies
        - C) CSRF tokens with proper validation
        - D) Origin header validation only
      answer: C

  - name: Basic CSRF Attack - Email Change
    description: Practice exploiting a CSRF vulnerability to change user email address.
    type: simulation
    order: 3
    simulation:
      type: basic_csrf
      scenario: email_change
      target_url: /profile/update
      vulnerable_parameters:
        - email
      success_payload: "<form action='/profile/update' method='POST'><input name='email' value='attacker@evil.com'></form>"
      success_criteria: HTML form that performs unauthorized email change.
      difficulty: beginner
      hints:
        - Create an HTML form that submits to the target URL.
        - The form should change the email to a value you control.
        - Use POST method for the form submission.
        - The target site does not validate CSRF tokens.

  - name: CSRF with Auto-Submit
    description: Create a CSRF attack that automatically submits when the page loads.
    type: simulation
    order: 4
    simulation:
      type: auto_submit_csrf
      scenario: fund_transfer
      target_url: /transfer/money
      vulnerable_parameters:
        - amount
        - to_account
      success_payload: "<form id='csrf' action='/transfer/money' method='POST'><input name='amount' value='1000'><input name='to_account' value='attacker'></form><script>document.getElementById('csrf').submit()</script>"
      success_criteria: Auto-submitting form that transfers funds without user interaction.
      difficulty: intermediate
      hints:
        - Create a form that submits automatically using JavaScript.
        - Include hidden input fields for amount and destination account.
        - Use `document.getElementById().submit()` to auto-submit.
        - The form should transfer money to your account.

  - name: Image-based CSRF Attack
    description: Exploit CSRF using image tags for GET-based vulnerable endpoints.
    type: simulation
    order: 5
    simulation:
      type: image_csrf
      scenario: account_deletion
      target_url: /account/delete
      vulnerable_parameters:
        - confirm
      success_payload: "<img src='/account/delete?confirm=yes' style='display:none'>"
      success_criteria: Hidden image that triggers account deletion via GET request.
      difficulty: beginner
      hints:
        - Use an img tag with the vulnerable URL as the src.
        - Include the required parameters in the URL query string.
        - Hide the image so the user does not see it.
        - The request happens when the image loads.

  - name: CSRF with AJAX
    description: Perform CSRF attacks using JavaScript and AJAX requests.
    type: simulation
    order: 6
    simulation:
      type: ajax_csrf
      scenario: password_change
      target_url: /account/password
      vulnerable_parameters:
        - new_password
      success_payload: "<script>fetch('/account/password', {method: 'POST', body: 'new_password=hacked123', headers: {'Content-Type': 'application/x-www-form-urlencoded'}})</script>"
      success_criteria: JavaScript code that changes user password via AJAX.
      difficulty: advanced
      hints:
        - Use JavaScript `fetch()` or `XMLHttpRequest`.
        - Send a POST request to the vulnerable endpoint.
        - Include the new password in the request body.
        - Set proper Content-Type header for form data.

  - name: CSRF Token Bypass Techniques
    description: Learn methods to bypass weak CSRF token implementations.
    type: theory
    order: 7
    heading: CSRF Token Bypass Techniques
    content: |
      Even when CSRF tokens are implemented, they may have weaknesses that can be exploited by attackers.

      ### Common Bypass Techniques

      #### 1. Missing Token Validation

      - Application accepts requests without CSRF tokens
      - Simply omit the token from the request
      - Server does not enforce token presence

      #### 2. Predictable Tokens

      - Tokens generated using weak algorithms
      - Sequential or timestamp-based tokens
      - Reused tokens across sessions

      #### 3. Token Leakage

      - Tokens exposed in URLs through GET parameters
      - Tokens in Referer headers
      - Tokens accessible via XSS

      #### 4. Subdomain Attacks

      - Weak domain validation
      - Accepting requests from any subdomain
      - Cookie scope issues

      ### Testing for CSRF Vulnerabilities

      1. Remove CSRF token and replay request.
      2. Change token value to invalid or empty.
      3. Use token from a different session.
      4. Check if token is validated on the server.
      5. Test with different HTTP methods.

      ### Example Bypass

      ```http
      # Original request with token
      POST /transfer HTTP/1.1
      csrf_token=abc123&amount=100&to=victim

      # Bypass attempt - remove token
      POST /transfer HTTP/1.1
      amount=100&to=attacker
      ```
    mcq:
      question: Which scenario makes CSRF tokens ineffective?
      options:
        - A) Tokens are generated using strong randomness
        - B) Server accepts requests without validating tokens
        - C) Tokens are properly tied to user sessions
        - D) Tokens are validated on every request
      answer: B
---

