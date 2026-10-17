---
layout: course
title: Introduction to Web Application Security
category: Web Security
level: Beginner
track: professional
duration: 2 to 3 hours
instructor: OWASP BLT Community
featured: true
next_course: advanced-pentesting
image: /assets/images/courses/web-security.svg
prerequisites: Basic familiarity with web pages, forms, and HTTP requests
description: Learn where web applications lose trust, then practice each idea in the existing hands-on security labs.
outcomes:
  - Recognize where user-controlled input crosses an interpreter boundary.
  - Explain how authentication, authorization, and session state differ.
  - Use the existing practice labs to investigate common web security failures.
lessons:
  - id: input-crosses-a-boundary
    title: Input crosses a boundary
    intro: User input becomes dangerous when an interpreter mistakes data for instructions.
    body: |
      A search term, form field, or URL parameter starts as data. Trouble begins when an application joins that value directly into SQL, HTML, or another executable context.

      The defensive question is simple: where will this value be interpreted next? Parameterized queries protect database structure. Context-aware output encoding prevents a browser from treating text as markup or script.
    example:
      title: Data should stay data
      language: JavaScript
      code: |
        // Risky: input changes the query structure
        db.query("SELECT * FROM users WHERE id = " + userId);

        // Safer: the driver binds input as a value
        db.query("SELECT * FROM users WHERE id = ?", [userId]);
      note: Validation is useful, but it does not replace the safe API for the destination interpreter.
    labs:
      - sql_injection
      - cross_site_scripting_xss
  - id: identity-is-not-permission
    title: Identity is not permission
    intro: Knowing who sent a request is different from checking whether that person may access the object.
    body: |
      Authentication establishes identity. Authorization decides what that identity can do. Applications often check the first and assume the second.

      Every object lookup needs a server-side permission check. Hiding an identifier in the interface or changing it to a UUID does not enforce access control.
    example:
      title: Check ownership with the lookup
      language: HTTP
      code: |
        GET /api/invoices/842
        Cookie: session=user-17

        Required check: invoice 842 belongs to user 17
      note: If the permission check happens only in the browser, a direct request can bypass it.
    labs:
      - broken_authentication
      - insecure_direct_object_reference
  - id: the-browser-carries-authority
    title: The browser carries authority
    intro: Cookies, redirects, and automatic requests can move trust somewhere the user did not intend.
    body: |
      A browser automatically attaches cookies to matching requests. Without an anti-forgery control, another page may cause an authenticated action on the learner's behalf.

      Redirect destinations also need boundaries. If any external URL is accepted, a trusted domain can become the first step in a phishing path.
    observation: The browser doing something automatically does not mean the user approved it.
    labs:
      - cross_site_request_forgery
      - open_redirect
  - id: server-features-reach-further
    title: Server features reach further than expected
    intro: Commands and outbound requests can expose the operating system or internal network behind an ordinary feature.
    body: |
      Features such as diagnostics, image importers, and webhook testers often call powerful server-side APIs. If untrusted input controls a command string or destination URL, the feature may reach resources the user could never access directly.

      Prefer structured process APIs, strict destination allowlists, and network controls that limit what the application can reach.
    labs:
      - command_injection
      - server_side_request_forgery
  - id: files-and-secrets-outlive-requests
    title: Files and secrets outlive the request
    intro: Uploaded files and exposed data remain risky after the original request has finished.
    body: |
      File names, extensions, and browser-provided content types are claims, not proof. Store uploads outside executable paths, generate server-side names, and validate the content you actually expect.

      Secrets can also escape through logs, error messages, backups, and frontend bundles. Before shipping a response, ask whether every returned field belongs in the learner's browser.
    observation: The safest secret in a frontend bundle is the one that was never placed there.
    labs:
      - file_upload_vulnerabilities
      - sensitive_data_exposure
---

Web security becomes less mysterious when you follow trust from a request to the system that interprets it. This course introduces five trust boundaries and connects each one to existing BLT University labs.

The lessons are intentionally short. Learn the reason behind a vulnerability, practice it safely, then return to the course to continue the path.
