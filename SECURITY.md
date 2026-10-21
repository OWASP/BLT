# Security Policy

This policy covers every project in the OWASP BLT monorepo (the `blt-*` folders and the rest of
[git.owaspblt.org/BLT](https://git.owaspblt.org/BLT)) and the sites deployed from it under `owaspblt.org`.
Some project folders also have their own `SECURITY.md` describing that project's security design; for
**reporting** a vulnerability, follow this page.

## Report a vulnerability privately

Open a private security advisory on the forge:

1. Sign in to [git.owaspblt.org](https://git.owaspblt.org).
2. Go to the **Security** tab of the BLT repository and choose **Report a vulnerability**:
   <https://git.owaspblt.org/BLT/security/advisories/new>
3. Name the affected project folder (for example `blt-api`) or site (for example `next.owaspblt.org`).

The advisory stays private until a maintainer publishes it.

**Never** report a vulnerability in a public issue, pull request, discussion, Slack channel or AI chat.

If you can't use the forge, email **[support@owaspblt.org](mailto:support@owaspblt.org)** with "Security" in
the subject, and we'll open a private advisory for you. Send only a short description first; we'll arrange
a private channel for the details.

## What to include

- The affected project, URL, endpoint or file, and the version or commit.
- Steps to reproduce, or a proof of concept.
- The impact as you understand it, and an honest severity estimate.
- Whether you want to be credited, and under what name.

Reports found with AI tools are welcome. Confirm the finding is real and remove anything the tool made up
before you send it; see the security section of the [AI Policy](https://git.owaspblt.org/BLT/blob/AI_POLICY.md).
Don't paste unpublished vulnerability details into third-party AI services.

## What to expect

- We aim to respond within 7 days. Maintainers are volunteers, so a reply can take longer.
- For a valid report we agree a fix and disclosure timeline with you, typically up to 90 days.
- We fix the issue, deploy the affected project, and may publish the advisory once users are protected.
- We credit you in the advisory if you want; you can also stay anonymous.

Please don't exploit the issue beyond what is needed to show it, don't access or change other people's
data, don't run load or denial-of-service tests against live sites, and don't disclose the issue publicly
until it is fixed or the agreed timeline has passed.

## Bounties

BLT does not currently pay bounties for vulnerabilities in its own projects.

## Supported versions

Every BLT project deploys continuously from the `main` branch. Only the current `main` and the live sites
are supported; fixes are not backported.

## Reporting vulnerabilities in other organizations

To send an encrypted vulnerability report to *another* organization's security team, use
[BLT-Zero](https://zero.owaspblt.org): the report is encrypted in your browser and delivered to the
organization's inbox. See [blt-zero](https://git.owaspblt.org/BLT/tree/blt-zero).
