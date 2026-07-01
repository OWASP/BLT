---
layout: lab
title: Insecure Direct Object Reference
description: Learn how missing object-level authorization exposes other users' data.
difficulty: beginner
category: Web Security
estimated_time: 45

tasks:
  - name: Introduction to IDOR
    description: Learn why object IDs in URLs need authorization checks.
    type: theory
    order: 1
    heading: What is an Insecure Direct Object Reference?
    content: |
      Insecure Direct Object Reference (IDOR) happens when an application exposes an internal object identifier and trusts that identifier without checking whether the current user is allowed to access the object.

      A common example is a profile route like `/users/42`. If user 17 can change the URL to `/users/42` and read another user's private profile, the application has an object-level authorization bug.

      ### Why IDOR Happens

      IDOR usually appears when code checks that a user is logged in, but does not check whether the requested record belongs to that user.

      ```javascript
      app.get('/profiles/:userId', requireLogin, (request, response) => {
          const profile = db.getUserProfile(request.params.userId);
          response.json(profile);
      });
      ```

      The route has authentication, but it does not have authorization for the specific profile object.

      ### Secure Pattern

      Load the object, compare its owner with the authenticated user, and reject access when they do not match.
    mcq:
      question: What check is missing in a typical IDOR vulnerability?
      options:
        - A) Whether the requested object belongs to, or is allowed for, the authenticated user
        - B) Whether the URL uses lowercase letters
        - C) Whether the database table has an index
        - D) Whether the browser supports JavaScript
      answer: A

  - name: IDOR Profile Access
    description: Practice finding and fixing a profile endpoint that trusts a URL object ID.
    type: simulation
    order: 2
    simulation:
      engine: idor-profile
      type: object_level_authorization
      scenario: profile_lookup
      target_url: /profiles/:userId
      vulnerable_code: |
        app.get('/profiles/:userId', requireLogin, (request, response) => {
            const requestedUserId = request.params.userId;
            const profile = db.getUserProfile(requestedUserId);
            response.json(profile);
        });
      vulnerable_lines:
        - 4
      explain:
        question: Why can this endpoint leak another user's profile?
        options:
          - id: missing_object_authorization
            label: The route returns any requested profile ID without checking whether it belongs to the logged-in user.
          - id: weak_password_hash
            label: The application stores weak password hashes.
          - id: missing_rate_limit
            label: The endpoint does not limit how many requests a user can send.
        answer: missing_object_authorization
      expected_patterns:
        - object_level_authorization
        - ownership_check
      attack_payloads:
        - /profiles/42
      vulnerable_parameters:
        - userId
      success_payload: /profiles/42
      success_criteria: A logged-in user can change the profile ID in the URL and read another user's profile.
      fix_starter_code: |
        app.get('/profiles/:userId', requireLogin, (request, response) => {
            const requestedUserId = request.params.userId;
            const profile = db.getUserProfile(requestedUserId);
            response.json(profile);
        });
      hints:
        - Authentication only proves who made the request.
        - Authorization decides whether that user may access this specific profile.
        - Compare the profile owner with the authenticated user before returning data.
        - Return 403 Forbidden when the requested profile belongs to someone else.

  - name: IDOR in APIs and Downloads
    description: Learn where IDOR appears outside profile pages.
    type: theory
    order: 3
    heading: Common IDOR Locations
    content: |
      IDOR is not limited to profile pages. Any endpoint that accepts an object ID can become vulnerable if it skips object-level authorization.

      ### Common Places to Check

      - Invoice downloads such as `/invoices/1008.pdf`
      - API routes such as `/api/orders/42`
      - Account settings routes such as `/users/17/settings`
      - File attachments such as `/attachments/771`
      - Admin actions that accept `user_id`, `team_id`, or `project_id`

      ### Vulnerable Example

      ```javascript
      app.get('/invoices/:invoiceId', requireLogin, (request, response) => {
          const invoice = db.getInvoice(request.params.invoiceId);
          response.download(invoice.filePath);
      });
      ```

      This route checks that the user is logged in, but it does not check whether the invoice belongs to that user or their organization.
    mcq:
      question: Which route is most likely to need an object-level authorization check?
      options:
        - A) /assets/logo.png
        - B) /invoices/1008.pdf
        - C) /about
        - D) /styles/main.css
      answer: B

  - name: Object Authorization Patterns
    description: Compare ownership checks, role checks, and centralized authorization helpers.
    type: theory
    order: 4
    heading: Building Safer Authorization Checks
    content: |
      A good IDOR fix is more than comparing two IDs in one route. The goal is to make object authorization consistent across the application.

      ### Strong Patterns

      - Check ownership on the server for every object access.
      - Use role or permission checks when teams, projects, or organizations can share objects.
      - Query through the current user's scope when possible.
      - Keep authorization helpers centralized and reusable.

      ### Safer Query Pattern

      Instead of loading any invoice by ID, scope the lookup to the authenticated user:

      ```javascript
      const invoice = db.getInvoiceForUser(request.params.invoiceId, request.user.id);

      if (!invoice) {
          return response.status(404).json({ error: 'Not found' });
      }

      response.download(invoice.filePath);
      ```

      This avoids returning objects from outside the user's allowed scope.
    mcq:
      question: Why is querying through the current user's scope safer?
      options:
        - A) It prevents the database from using indexes
        - B) It makes unauthorized objects fail the lookup before they can be returned
        - C) It hides JavaScript from the browser
        - D) It removes the need for authentication
      answer: B

  - name: Preventing IDOR
    description: Review defensive patterns for object-level authorization.
    type: theory
    order: 5
    heading: How to Prevent IDOR
    content: |
      IDOR is prevented with consistent object-level authorization checks.

      ### Defenses

      - Check ownership before returning, updating, or deleting a record.
      - Prefer centralized authorization helpers so routes use the same rule.
      - Return `404` or `403` when the user cannot access the requested object.
      - Avoid assuming hidden UI controls or unpredictable IDs are sufficient protection.

      ### Example Fix

      ```javascript
      app.get('/profiles/:userId', requireLogin, (request, response) => {
          const profile = db.getUserProfile(request.params.userId);

          if (!profile || profile.userId !== request.user.id) {
              return response.status(403).json({ error: 'Forbidden' });
          }

          response.json(profile);
      });
      ```

      The URL still contains a direct object reference, but the server now verifies that the authenticated user is allowed to access the referenced object.
    mcq:
      question: Which defense best prevents IDOR?
      options:
        - A) Hiding profile links from the page
        - B) Checking object ownership or authorization on the server
        - C) Renaming the userId parameter
        - D) Adding more CSS to the profile page
      answer: B
---
