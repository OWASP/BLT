---
layout: lab
title: File Upload Vulnerabilities
description: Explore critical file upload security flaws that allow attackers to upload malicious files and execute
  code on servers. Learn to bypass extension filters, MIME type validation, and path traversal restrictions.
difficulty: intermediate
category: Web Security
estimated_time: 50
tasks:
- name: Introduction to File Upload Vulnerabilities
  description: Learn why unrestricted file uploads are dangerous and common attack patterns.
  type: theory
  order: 1
  heading: Introduction to File Upload Vulnerabilities
  content: |
    <h2>What are File Upload Vulnerabilities?</h2>
    <p>File Upload Vulnerabilities occur when an application accepts files from users without proper validation, allowing attackers to upload malicious files (web shells), bypass access controls, or overwrite sensitive files.</p>

    <h3>Common risks</h3>
    <ul>
        <li>Remote code execution (uploading web shells)</li>
        <li>Content-based attacks (malicious scripts disguised as images)</li>
        <li>Path traversal (writing files outside allowed directories)</li>
        <li>Denial of Service (large or numerous uploads)</li>
    </ul>

    <h3>Typical vulnerable code</h3>
    <pre><code>
    // Poor example: saving uploaded file with original filename without validation
    filename = request.FILES['file'].name
    open("/var/www/uploads/" + filename, "wb").write(request.FILES['file'].read())
    </code></pre>
  mcq:
    question: Which of the following is the best practice to reduce file upload risk?
    options:
    - A) Allow any file extension but scan contents on demand
    - B) Validate file type, restrict extensions, and store outside the web root
    - C) Save files using user-controlled filenames
    - D) Serve uploaded files directly from the application server
    answer: B
- name: File Type & Content Validation
  description: Understand checks for MIME type, extension and magic bytes, and why each matters.
  type: theory
  order: 2
  heading: File Type & Content Validation
  content: |
    <h2>File Validation Techniques</h2>
    <ul>
        <li><strong>Extension checks:</strong> Useful but can be bypassed by renaming files.</li>
        <li><strong>MIME type checks:</strong> Based on headers; can be spoofed.</li>
        <li><strong>Magic byte inspection:</strong> Checking file signatures is stronger.</li>
        <li><strong>Content scanning:</strong> Anti-virus / malware scanning as an additional layer.</li>
    </ul>

    <h3>Best practices</h3>
    <ul>
        <li>Whitelist allowed file types and verify magic bytes</li>
        <li>Store uploads outside the web root and serve via authenticated proxy</li>
        <li>Rename files to server-generated tokens (avoid original filenames)</li>
        <li>Limit file size and enforce quotas</li>
    </ul>
  mcq:
    question: Why is checking only file extension insufficient?
    options:
    - A) Extensions are always correct
    - B) Attackers can rename files to bypass extension checks
    - C) Extensions validate magic bytes
    - D) Extensions prevent XSS
    answer: B
- name: 'Simulation: Upload a Web Shell (Safe Lab)'
  description: Simulate uploading a malicious web shell file and demonstrating execution (lab safely simulates execution
    output).
  type: simulation
  order: 3
  simulation:
    type: upload_shell
    scenario: web_shell_upload
    engine: upload-shell
    target_url: /upload
    vulnerable_code: |
      app.post('/upload', upload.single('file'), (req, res) => {
        const filename = req.file.originalname;
        fs.writeFileSync('/var/www/uploads/' + filename, req.file.buffer);
        res.send(`/uploads/${filename}`);
      });
    vulnerable_lines:
    - 3
    - 4
    explain:
      question: Why can this upload become executable?
      options:
      - id: executable_upload
        label: The app trusts the original filename and stores attacker content under a web-served path.
      - id: small_file
        label: The uploaded file is too small.
      answer: executable_upload
    expected_patterns:
    - allowed_file_types
    - magic_byte_validation
    - outside_web_root_storage
    fix_starter_code: |
      app.post('/upload', upload.single('file'), (req, res) => {
        const filename = req.file.originalname;
        fs.writeFileSync('/var/www/uploads/' + filename, req.file.buffer);
        res.send(`/uploads/${filename}`);
      });
    vulnerable_parameters:
    - file
    success_payload: upload a file named shell.php containing '<?php echo shell_exec($_GET["cmd"]); ?>'
    success_criteria: Lab marks it as executable and returns simulated command output
    hints:
    - Try a .php file with a simple payload
    - Try double extensions like image.php.jpg
    - The lab simulates execution (no real system commands run)
    difficulty: intermediate
- name: 'Simulation: Content-Type Bypass'
  description: Bypass naive MIME-type checks by uploading a malicious payload disguised as an image.
  type: simulation
  order: 4
  simulation:
    type: upload_mimetype_bypass
    scenario: mimetype_bypass
    engine: upload-mimetype
    target_url: /avatar
    vulnerable_code: |
      app.post('/avatar', upload.single('file'), (req, res) => {
        if (req.file.mimetype.startsWith('image/')) {
          fs.writeFileSync('/var/www/uploads/' + req.file.originalname, req.file.buffer);
        }
        res.send('uploaded');
      });
    vulnerable_lines:
    - 2
    - 3
    explain:
      question: Why is trusting only the MIME header weak?
      options:
      - id: spoofed_mime
        label: Attackers can spoof Content-Type while the file content remains malicious.
      - id: large_image
        label: Images are always too large to store.
      answer: spoofed_mime
    expected_patterns:
    - extension_allowlist
    - magic_byte_validation
    - malware_scanning
    fix_starter_code: |
      app.post('/avatar', upload.single('file'), (req, res) => {
        if (req.file.mimetype.startsWith('image/')) {
          fs.writeFileSync('/var/www/uploads/' + req.file.originalname, req.file.buffer);
        }
        res.send('uploaded');
      });
    vulnerable_parameters:
    - file
    success_payload: Upload file with .jpg extension but with embedded script content
    success_criteria: Lab detects disguised malicious content
    hints:
    - Add PHP inside a .jpg
    - Try payload in EXIF or metadata (simulated)
    difficulty: intermediate
- name: 'Simulation: Path Traversal via Filename'
  description: Exploit improper file path handling to write outside upload directory.
  type: simulation
  order: 5
  simulation:
    type: upload_path_traversal
    scenario: path_traversal
    engine: upload-path-traversal
    target_url: /upload?path=
    vulnerable_code: |
      app.post('/upload', upload.single('file'), (req, res) => {
        const destination = path.join('/srv/uploads', req.query.path, req.file.originalname);
        fs.writeFileSync(destination, req.file.buffer);
        res.send('saved');
      });
    vulnerable_lines:
    - 2
    - 3
    explain:
      question: Why can this write outside the upload directory?
      options:
      - id: traversal_path
        label: User-controlled path segments can include ../ and escape the intended directory.
      - id: missing_thumbnail
        label: The file does not have a thumbnail.
      answer: traversal_path
    expected_patterns:
    - path_normalization
    - traversal_blocking
    - safe_storage_root
    fix_starter_code: |
      app.post('/upload', upload.single('file'), (req, res) => {
        const destination = path.join('/srv/uploads', req.query.path, req.file.originalname);
        fs.writeFileSync(destination, req.file.buffer);
        res.send('saved');
      });
    vulnerable_parameters:
    - file
    - path
    success_payload: Use '../../secrets.txt' to simulate writing outside upload directory
    success_criteria: Lab reveals simulated secret contents
    hints:
    - Try ../ sequences
    - Use URL-encoded traversal
    difficulty: advanced
- name: Secure File Upload Practices
  description: Learn secure practices for file upload systems.
  type: theory
  order: 6
  heading: Secure File Upload Practices
  content: |
    <h2>Secure File Upload Best Practices</h2>
    <ul>
        <li>Whitelist extensions + verify magic bytes</li>
        <li>Store uploads outside web root</li>
        <li>Generate server-side filenames</li>
        <li>Use auth-protected file serving</li>
        <li>Limit upload size</li>
    </ul>
  mcq:
    question: Which is NOT a recommended secure upload practice?
    options:
    - A) Store uploads outside webroot
    - B) Validate magic bytes
    - C) Use user-controlled filenames directly
    - D) Use server-generated filenames
    answer: C
- name: File Upload Challenge - Restricted Extensions
  description: Server blocks .php and .jsp — find a bypass.
  type: simulation
  order: 7
  simulation:
    type: upload_restricted_ext_bypass
    scenario: double_extension
    engine: upload-double-extension
    target_url: /upload
    vulnerable_code: |
      app.post('/upload', upload.single('file'), (req, res) => {
        if (!req.file.originalname.endsWith('.php')) {
          fs.writeFileSync('/var/www/uploads/' + req.file.originalname, req.file.buffer);
        }
        res.send('uploaded');
      });
    vulnerable_lines:
    - 2
    - 3
    explain:
      question: Why can double extensions bypass this check?
      options:
      - id: blocklist_bypass
        label: Blocking one suffix misses alternate names and server parsing behavior such as shell.php.jpg.
      - id: no_filename
        label: Uploaded files do not have filenames.
      answer: blocklist_bypass
    expected_patterns:
    - extension_allowlist
    - magic_byte_validation
    - server_generated_filename
    fix_starter_code: |
      app.post('/upload', upload.single('file'), (req, res) => {
        if (!req.file.originalname.endsWith('.php')) {
          fs.writeFileSync('/var/www/uploads/' + req.file.originalname, req.file.buffer);
        }
        res.send('uploaded');
      });
    vulnerable_parameters:
    - file
    success_payload: shell.php.jpg
    success_criteria: Lab simulates execution output from double-extension file
    hints:
    - Try double extensions
    - Try tricky filenames / mixed casing
    difficulty: advanced
---
