# Lab Template

Use this template when creating a new lab in `_labs/`. Save the file with a clear lowercase slug, such as `_labs/idor_basics.md`.

```yaml
---
layout: lab
title: Your Lab Title
description: One sentence describing what learners will practice.
difficulty: beginner
category: Web Security
estimated_time: 45

# Optional proposal metadata. Add these when known.
# owasp_category: A01
# track: both
# tags:
#   - access-control
#   - idor
# learning_objectives:
#   - Identify attacker-controlled object identifiers.
# success_criteria:
#   - Complete each theory and simulation task.
# attack_payloads:
#   - /api/users/2

tasks:
  - name: Introduction
    description: Learn the concept behind this vulnerability.
    type: theory
    order: 1
    heading: What learners need to know
    content: |
      Explain the vulnerability and its impact in Markdown.

      Include safe examples and defensive guidance.
    mcq:
      question: What is the safest answer?
      options:
        - A) Unsafe pattern
        - B) Secure pattern
        - C) Unrelated pattern
        - D) Another unrelated pattern
      answer: B

  - name: Vulnerable Scenario
    description: Practice identifying, explaining, and fixing the issue.
    type: simulation
    order: 2
    simulation:
      engine: idor-basic
      type: insecure_direct_object_reference
      scenario: user_profile
      target_url: /api/users/2
      vulnerable_code: |
        app.get('/api/users/:id', requireLogin, (req, res) => {
          const user = findUserById(req.params.id);
          res.json(user);
        });
      vulnerable_lines:
        - 2
      explain:
        question: Why can this endpoint expose another user's data?
        options:
          - id: missing_owner_check
            label: The route trusts the requested user id without checking ownership or authorization.
          - id: weak_password
            label: The password is too short.
          - id: missing_tls
            label: The request is not using TLS.
        answer: missing_owner_check
      expected_patterns:
        - authorization_check
        - object_ownership_check
      forbidden_patterns:
        - trust_client_id
      attack_payloads:
        - /api/users/2
      vulnerable_parameters:
        - id
      success_payload: /api/users/2
      success_criteria: Access another user's profile by changing the id parameter.
      difficulty: beginner
      fix_starter_code: |
        app.get('/api/users/:id', requireLogin, (req, res) => {
          const user = findUserById(req.params.id);
          res.json(user);
        });
      hints:
        - Look for a user-controlled identifier.
        - Check whether the current user is authorized to access the object.
        - Fetch records through the authenticated user's allowed scope.
---

Write optional long-form lab notes here if the lab needs extra Markdown content outside the task list.
```

## Required Frontmatter

- `layout`: must be `lab`
- `title`: lab title
- `description`: short lab summary
- `difficulty`: `beginner`, `intermediate`, or `advanced`
- `category`: category label used by the labs page
- `estimated_time`: estimated minutes, minimum `1`
- `tasks`: one or more task objects

## Current Task Types

- `theory`: lesson content, usually with an embedded `mcq`
- `mcq`: reserved for future standalone quiz tasks
- `simulation`: interactive identify, explain, and fix exercise
