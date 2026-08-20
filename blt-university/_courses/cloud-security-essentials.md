---
layout: course
title: Cloud Security Essentials
category: Cloud Security
level: Advanced
duration: About 2 hours
instructor: OWASP BLT Community
featured: true
next_course: crypto-for-devs
prerequisites: Familiarity with cloud accounts, roles, and storage services
description: Trace identity, public exposure, and audit evidence through an approachable cloud incident scenario.
outcomes:
  - Trace effective permissions across identities, functions, and storage.
  - Investigate exposure using policy, configuration, and audit evidence.
  - Contain a cloud incident while preserving the evidence needed to learn from it.
  - Design guardrails that prevent unsafe defaults from returning.
lessons:
  - id: permissions-form-a-path
    title: Permissions form a path
    intro: Cloud risk often comes from several individually reasonable permissions that become dangerous when combined.
    body: |
      Review what an identity can read, what it can change, and which other role it can assume. A service account that cannot access data directly may still be able to update a function that runs as a stronger role.

      Least privilege is not just a shorter action list. It also limits resources, conditions, session duration, and who may delegate the identity.
    example:
      title: Look beyond the first statement
      language: Policy
      code: |
        Allow: update function code
        Resource: billing-exporter

        billing-exporter runs as: finance-read-role
      note: The effective path includes the permissions of the runtime role, not only the caller's policy.
    challenge:
      id: trace-runtime-role
      type: artifact
      title: Follow the permission path
      prompt: The deploy bot cannot read invoices directly. Enter the role that gains the read permission when the function runs.
      answer: finance-read-role
      success: Correct. The function's runtime role completes the permission path.
      artifact:
        title: Identity trace
        language: Policy trace
        code: |
          deploy-bot
            └─ can update: billing-exporter
                 └─ runs as: finance-read-role
                      └─ can read: invoice-archive
  - id: public-is-a-state
    title: Public is a state, not a label
    intro: A private resource can become reachable through a policy, signed URL, proxy, snapshot, or copied object.
    body: |
      Check the complete access path. Storage settings may say private while a content-delivery rule still allows anonymous reads. A database may reject public traffic while a snapshot is shared with another account.

      When exposure is confirmed, preserve the relevant audit details while blocking the exposed path. Record configuration and access history before making broader cleanup changes so you can still determine what happened.
    observation: This is the part people usually overlook. Fixing the visible setting can erase context without answering who accessed the resource.
    challenge:
      id: inspect-assumed-role
      type: inspect
      title: Inspect the evidence panel
      prompt: The visible panel looks empty. Inspect its HTML and find the value of the data-evidence attribute. That is the role used by the mock export job.
      clue: backup-read-role
      answer: backup-read-role
      success: You found the role in the underlying evidence instead of trusting the empty summary.
  - id: contain-without-going-blind
    title: Contain without going blind
    intro: Fast containment matters, but deleting the affected resource can remove the evidence needed to understand the incident.
    body: |
      Disable the narrowest risky path first. Revoke a key, block a public policy, or detach a role while preserving logs, configuration history, and relevant snapshots.

      Then trace the identity backward and the data forward. Ask how the credential was issued, what it accessed, and whether a replacement credential inherited the same weakness.
    example:
      title: A useful containment order
      language: Checklist
      code: |
        1. Block the exposed path
        2. Preserve logs and configuration history
        3. Rotate affected credentials
        4. Trace access and data movement
        5. Fix the policy pattern that allowed it
      note: Rotation without policy repair often recreates the same incident with a new key.
    challenge:
      id: containment-order
      type: sequence
      title: Build the first-response order
      prompt: The export role was exposed ten minutes ago. Put these four actions in the order that contains the path and preserves useful evidence.
      answer: block|preserve|rotate|trace
      success: The path is contained first, the evidence survives, and the investigation can continue safely.
      options:
        - id: trace
          label: Trace access and data movement.
        - id: rotate
          label: Rotate the affected credential.
        - id: block
          label: Block the exposed access path.
        - id: preserve
          label: Preserve logs and configuration history.
  - id: follow-credential-lineage
    title: Follow credential lineage
    intro: Rotating a key helps only when you know which workload used it and whether an older copy still works.
    body: |
      Inventory the issuer, workload, last use, and replacement for every long-lived credential. A key with no clear owner is not harmless. It is a path nobody is watching.

      During an incident, compare issue and use times. A credential used after its replacement became active may reveal a forgotten deployment or copied secret. Treat the audit trail like a small forensics puzzle: establish the rotation boundary, isolate the event that crosses it, then name the workload that still needs attention.
    challenge:
      id: stale-credential
      type: artifact
      title: Identify the stale credential
      prompt: The replacement became active at 09:20. Which credential was used afterward, and by which workload? Enter the finding as credential/workload.
      answer: key-201/unknown-workload
      success: Challenge completed. key-201 was still accepted by unknown-workload after key-305 became active. Trace and contain that workload.
      artifact:
        title: Rotation incident · audit trail
        language: Audit log
        code: |
          09:12  key-201  export-job       read invoice-archive
          09:20  key-305  rotation         replacement active
          09:27  key-201  unknown-workload read invoice-archive
          09:31  key-305  export-job       read invoice-archive
  - id: make-the-safe-state-default
    title: Make the safe state the default
    intro: The best incident fix also makes the same mistake harder to repeat.
    body: |
      Prefer organization-level controls for risks that should never be optional. Block public storage by default, require short-lived workload identities, and alert on policy changes that widen access.

      A dashboard warning is useful, but it still depends on someone noticing it. A preventive control stops the unsafe state before it becomes an incident.
    challenge:
      id: preventive-guardrail
      type: choice
      title: Choose the preventive control
      prompt: Teams keep accidentally publishing storage buckets. Which control prevents the mistake instead of only reporting it?
      answer: deny-public
      success: Correct. An organization-level deny makes private storage the enforced default.
      options:
        - id: weekly-report
          label: Email a weekly list of public buckets to each team.
        - id: deny-public
          label: Apply an organization-level policy that denies public bucket access.
        - id: naming-rule
          label: Require public buckets to include public in their name.
---

Cloud incidents rarely fit inside one service. This course follows an approachable scenario across identity, storage exposure, and audit evidence without requiring access to a real cloud account.

The exercises use a mock identity trace and an embedded page clue. They reinforce checking the underlying evidence instead of trusting a summary label.
