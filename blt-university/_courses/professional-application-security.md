---
layout: course
title: Professional Application Security
category: Secure Coding
level: Intermediate
track: professional
duration: 6 weeks
instructor: Dr. Sarah Chen
featured: false
prerequisites: Basic programming experience and familiarity with HTTP requests
description: Strengthen secure development skills through the Identify, Explain, Fix workflow across common web application vulnerabilities.
labs:
  - sql_injection
  - cross_site_scripting_xss
  - insecure_direct_object_reference
  - broken_authentication
  - command_injection
  - server_side_request_forgery

syllabus:
  - title: Input and Output Safety
    description: Learn how untrusted input reaches interpreters and browser output contexts.
    topics:
      - SQL injection and parameterized queries
      - Cross-site scripting and output encoding
      - Safe validation boundaries
  - title: Identity and Access Control
    description: Practice checking who is making a request and what that user is allowed to access.
    topics:
      - Authentication failures
      - Object-level authorization
      - Request forgery protections
  - title: Server-Side Attack Surfaces
    description: Review controls for features that interact with operating systems, files, and internal services.
    topics:
      - Command injection
      - File upload validation
      - Server-side request forgery
---

This course is for developers, contributors, and security practitioners who are comfortable reading application code. Work through the linked labs in order and focus on why a defensive change works, not on matching one exact implementation.
