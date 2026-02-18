-- Test data for local development

-- Make the seed idempotent for local reruns:
-- clear child tables first, then parent tables.
DELETE FROM bug_team_members;
DELETE FROM bug_tags;
DELETE FROM bug_screenshots;
DELETE FROM bugs;
DELETE FROM domain_tags;
DELETE FROM domains;
DELETE FROM tags;

-- Reset AUTOINCREMENT counters for deterministic IDs in this seed file.
DELETE FROM sqlite_sequence
WHERE name IN (
    'bug_team_members',
    'bug_tags',
    'bug_screenshots',
    'bugs',
    'domain_tags',
    'domains',
    'tags'
);

-- Insert test tags
INSERT INTO tags (name) VALUES 
    ('security'),
    ('bug-bounty'),
    ('vulnerability'),
    ('web-app'),
    ('api');

-- Insert test domains
INSERT INTO domains (name, url, email, is_active, has_security_txt) VALUES
    ('OWASP BLT', 'https://blt.owasp.org', 'support@owasp.org', 1, 1),
    ('Example Corp', 'https://example.com', 'security@example.com', 1, 0),
    ('Test Domain', 'https://test.example.org', 'test@example.org', 1, 1);

-- Link tags to domains
INSERT INTO domain_tags (domain_id, tag_id) VALUES
    (1, 1), -- OWASP BLT -> security
    (1, 2), -- OWASP BLT -> bug-bounty
    (1, 3), -- OWASP BLT -> vulnerability
    (2, 1), -- Example Corp -> security
    (2, 4), -- Example Corp -> web-app
    (3, 1), -- Test Domain -> security
    (3, 5); -- Test Domain -> api

-- Insert test bugs
INSERT INTO bugs (
    url, description, markdown_description, label, views, verified, score, 
    status, user_agent, screenshot, github_url, is_hidden, rewarded, 
    reporter_ip_address, cve_id, cve_score, domain
) VALUES
    (
        'https://blt.owasp.org/login',
        'XSS vulnerability found in login form',
        '## XSS Vulnerability\n\nFound a reflected XSS in the login form when entering malicious input in the username field.\n\n### Steps to Reproduce:\n1. Navigate to login page\n2. Enter `<script>alert(1)</script>` in username\n3. Submit form',
        1,
        125,
        1,
        85,
        'open',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'https://cdn.example.com/screenshots/bug1.png',
        'https://github.com/OWASP-BLT/BLT/issues/123',
        0,
        50,
        '192.168.1.100',
        'CVE-2024-1234',
        '7.5',
        1
    ),
    (
        'https://example.com/api/users',
        'SQL Injection in user search endpoint',
        '## SQL Injection\n\nThe `/api/users` endpoint is vulnerable to SQL injection via the `search` parameter.\n\n### Proof of Concept:\n```\nGET /api/users?search=admin'' OR 1=1--\n```',
        2,
        89,
        1,
        95,
        'closed',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
        'https://cdn.example.com/screenshots/bug2.png',
        NULL,
        0,
        100,
        '10.0.0.50',
        'CVE-2024-5678',
        '9.8',
        2
    ),
    (
        'https://test.example.org/upload',
        'Unrestricted file upload allows malicious files',
        '## File Upload Vulnerability\n\nThe upload functionality does not properly validate file types, allowing upload of executable files.',
        3,
        45,
        0,
        70,
        'open',
        'Mozilla/5.0 (X11; Linux x86_64)',
        NULL,
        NULL,
        0,
        0,
        '172.16.0.25',
        NULL,
        NULL,
        3
    ),
    (
        'https://blt.owasp.org/api/v1',
        'Missing rate limiting on API endpoints',
        '## Rate Limiting Issue\n\nAPI endpoints lack rate limiting, allowing potential abuse and DoS attacks.',
        4,
        200,
        1,
        60,
        'open',
        'curl/7.68.0',
        NULL,
        'https://github.com/OWASP-BLT/BLT/issues/456',
        0,
        25,
        '203.0.113.10',
        NULL,
        NULL,
        1
    ),
    (
        'https://example.com/forgot-password',
        'Weak password reset mechanism',
        '## Weak Password Reset\n\nPassword reset tokens are predictable and have no expiration.',
        5,
        67,
        0,
        55,
        'reviewing',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)',
        'https://cdn.example.com/screenshots/bug5.png',
        NULL,
        0,
        0,
        '198.51.100.42',
        NULL,
        NULL,
        2
    );

-- Insert bug screenshots
INSERT INTO bug_screenshots (image, bug) VALUES
    ('https://cdn.example.com/screenshots/xss-poc-1.png', 1),
    ('https://cdn.example.com/screenshots/xss-poc-2.png', 1),
    ('https://cdn.example.com/screenshots/sqli-proof.png', 2),
    ('https://cdn.example.com/screenshots/sqli-database.png', 2),
    ('https://cdn.example.com/screenshots/upload-shell.png', 3),
    ('https://cdn.example.com/screenshots/password-reset.png', 5);

-- Link tags to bugs
INSERT INTO bug_tags (bug_id, tag_id) VALUES
    (1, 1), -- XSS -> security
    (1, 3), -- XSS -> vulnerability
    (1, 4), -- XSS -> web-app
    (2, 1), -- SQL Injection -> security
    (2, 3), -- SQL Injection -> vulnerability
    (2, 5), -- SQL Injection -> api
    (3, 1), -- File Upload -> security
    (3, 3), -- File Upload -> vulnerability
    (3, 4), -- File Upload -> web-app
    (4, 1), -- Rate Limiting -> security
    (4, 5), -- Rate Limiting -> api
    (5, 1), -- Password Reset -> security
    (5, 4); -- Password Reset -> web-app

-- Display inserted data
SELECT 'Domains:' as info;
SELECT * FROM domains;

SELECT 'Tags:' as info;
SELECT * FROM tags;

SELECT 'Domain Tags:' as info;
SELECT 
    d.name as domain_name,
    t.name as tag_name
FROM domain_tags dt
JOIN domains d ON dt.domain_id = d.id
JOIN tags t ON dt.tag_id = t.id
ORDER BY d.name, t.name;

SELECT 'Bugs:' as info;
SELECT 
    b.id,
    b.url,
    substr(b.description, 1, 50) as description,
    b.status,
    b.score,
    b.verified,
    d.name as domain_name
FROM bugs b
LEFT JOIN domains d ON b.domain = d.id
ORDER BY b.created DESC;

SELECT 'Bug Screenshots:' as info;
SELECT 
    s.id,
    s.image,
    b.description as bug_description
FROM bug_screenshots s
JOIN bugs b ON s.bug = b.id
ORDER BY s.created DESC;

SELECT 'Bug Tags:' as info;
SELECT 
    b.id as bug_id,
    substr(b.description, 1, 40) as bug,
    t.name as tag_name
FROM bug_tags bt
JOIN bugs b ON bt.bug_id = b.id
JOIN tags t ON bt.tag_id = t.id
ORDER BY b.id, t.name;
