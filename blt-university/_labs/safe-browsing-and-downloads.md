---
layout: lab
title: Safe Browsing and Downloads
description: Practice safer decisions around websites, browser permissions, downloads, updates, and public networks.
difficulty: beginner
category: Cyber Hygiene
track: hygiene
estimated_time: 45
tags:
  - safe browsing
  - downloads
  - device security
learning_objectives:
  - Evaluate a website before sharing information.
  - Limit unnecessary browser and application permissions.
  - Choose safer update and download practices.
success_criteria:
  - Distinguish HTTPS transport from proof that a site is trustworthy.
  - Choose official sources and least-privilege permissions.

tasks:
  - name: Check the Website
    description: Learn what HTTPS can tell you and what it cannot.
    type: theory
    order: 1
    heading: A lock icon is not a trust certificate
    content: |
      HTTPS encrypts the connection between your browser and the website. It helps prevent people on the network from reading or changing traffic, but it does not prove that the website is honest. A phishing site can also use HTTPS.

      Check the full domain, avoid lookalike spellings, and use a known bookmark for sensitive services. Never rely on a lock icon alone before entering a password or payment details.
    mcq:
      question: A site shows HTTPS and a lock icon. What does that actually tell you?
      options:
        - A) The website is operated by the company it claims to represent.
        - B) The website is free from malware.
        - C) The connection is encrypted between your browser and that domain.
        - D) The page cannot collect personal information.
      answer: C

  - name: Review Permissions and Downloads
    description: Choose the least access an application or website needs to perform its task.
    type: theory
    order: 2
    heading: Grant only the access you can explain
    content: |
      A website that wants access to your camera, microphone, location, or notifications should explain why it needs that access. Deny requests that do not match the task and remove permissions that are no longer needed.

      Download software from the official publisher or a trusted app store. Avoid “urgent update” pop-ups and unsolicited attachments. Check the publisher, file name, and expected source before opening anything.
    mcq:
      question: A simple website asks for microphone access but gives no reason. What is the safer choice?
      options:
        - A) Allow it because the browser will block misuse.
        - B) Deny it and continue only if the site still provides the expected function.
        - C) Allow it, then leave the tab open overnight.
        - D) Download a browser extension to grant broader access.
      answer: B

  - name: Update and Connect Carefully
    description: Reduce exposure by keeping devices updated and treating public networks as untrusted.
    type: theory
    order: 3
    heading: Reduce the opportunities attackers get
    content: |
      Install security updates from the device or software vendor and restart when required. Updates fix known weaknesses that attackers may already understand.

      Public Wi-Fi can be monitored or impersonated. Avoid sensitive activity on an unknown network when possible, use your device's cellular connection or a trusted VPN when appropriate, and never ignore certificate or browser security warnings.
    mcq:
      question: You need to use public Wi-Fi. Which habit meaningfully lowers the risk?
      options:
        - A) Ignore certificate warnings if the network is free.
        - B) Use the same password on the network and your email account.
        - C) Avoid sensitive activity and use a trusted connection when possible.
        - D) Turn off all device updates until you return home.
      answer: C

  - name: Evaluate an Update Prompt
    description: Distinguish an official update path from a suspicious browser pop-up.
    type: theory
    order: 4
    heading: Start updates from the software, not the warning
    content: |
      A pop-up that says your device is infected or that you must install a codec immediately is not proof that an update is needed. Close the tab without clicking its buttons. Open the device settings or the software's official update screen and check there instead.

      Do not install extensions, remote-access tools, or “cleaners” because a web page demands them. If a warning keeps appearing, ask your organisation's support team or use the vendor's official help page.
    mcq:
      question: A browser pop-up insists that an update is urgent. Where should you check first?
      options:
        - A) Click the recommended download because the page knows the device state.
        - B) Close the page and check for updates from the device or application's official settings.
        - C) Disable the browser's security warnings and try again.
        - D) Install the file, then scan it after it runs.
      answer: B

  - name: Choose the Safer Path
    description: Apply safe browsing decisions to a website, download, and network scenario.
    type: theory
    order: 5
    heading: Stop when the source or request cannot be verified
    content: |
      Before entering sensitive information or opening a download, ask three questions: Do I recognise the full domain? Did I start this request? Can I verify the source through an official channel?

      If the answer to any question is no, stop and find a safer path. Use a bookmark or manually typed address, obtain software from the vendor, deny unnecessary permissions, and postpone sensitive activity until you have a trusted connection.
    mcq:
      question: On public Wi-Fi, a site asks you to install an extension before it will show your account. What should you do?
      options:
        - A) Install it because the site uses HTTPS.
        - B) Accept the extension and remove it after signing in.
        - C) Leave the page, use the official bookmarked service on a trusted connection, and avoid the extension.
        - D) Enter a temporary password to see whether the page is legitimate.
      answer: C

  - name: Investigate a Suspicious Download
    description: Decide how to respond when a download, permission request, and network warning appear together.
    type: theory
    order: 6
    heading: Do not let several warnings become one rushed decision
    content: |
      While using airport Wi-Fi, a website displays a fake “browser out of date” banner. It downloads an installer, requests administrator access, and asks you to disable security protection. The page uses HTTPS, but you reached it through an advertisement rather than a known bookmark.

      Do not run the installer or disable protections. Close the page, delete the download without opening it, disconnect from the untrusted network if possible, and check for updates from the browser's own settings. If the file ran or requested credentials, tell support and follow the device's malware-response process.
    mcq:
      question: An airport Wi-Fi page pushes an installer and asks you to disable security protection. What is the safest complete response?
      options:
        - A) Run the installer as administrator because the browser says the update is urgent.
        - B) Disable protection temporarily, inspect the installer, and re-enable protection afterward.
        - C) Close the page, do not run the file, use the official update path on a trusted connection, and report any exposure.
        - D) Upload the installer to a public scanner from the same airport network.
      answer: C
---
