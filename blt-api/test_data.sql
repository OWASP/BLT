-- Test data for local development

-- Make the seed idempotent for local reruns:
-- clear child tables first, then parent tables.
DELETE FROM user_bug_flags;
DELETE FROM user_bug_saves;
DELETE FROM user_bug_upvotes;
DELETE FROM user_follows;
DELETE FROM bug_team_members;
DELETE FROM bug_tags;
DELETE FROM bug_screenshots;
DELETE FROM bugs;
DELETE FROM domain_tags;
DELETE FROM domains;
DELETE FROM users;
DELETE FROM tags;

-- Reset AUTOINCREMENT counters for deterministic IDs in this seed file.
DELETE FROM sqlite_sequence
WHERE name IN (
    'user_bug_flags',
    'user_bug_saves',
    'user_bug_upvotes',
    'user_follows',
    'bug_team_members',
    'bug_tags',
    'bug_screenshots',
    'bugs',
    'domain_tags',
    'domains',
    'users',
    'tags'
);

-- Insert test tags
INSERT INTO tags (name) VALUES 
    ('security'),
    ('bug-bounty'),
    ('vulnerability'),
    ('web-app'),
    ('api');

-- Insert test users
-- Note: In production, passwords should be properly hashed (bcrypt, argon2, etc.)
-- These are placeholder hashed passwords for testing
INSERT INTO users (username, password, email, title, user_avatar, description, winnings, total_score, is_active) VALUES
    (
        'alice_hunter',
        'pbkdf2_sha256$260000$test_hash_alice',
        'alice@example.com',
        3,
        'https://avatars.example.com/alice.jpg',
        'Security researcher specializing in web application vulnerabilities. OSCP certified.',
        1250.50,
        450,
        1
    ),
    (
        'bob_security',
        'pbkdf2_sha256$260000$test_hash_bob',
        'bob@example.com',
        2,
        'https://avatars.example.com/bob.jpg',
        'Penetration tester and bug bounty hunter. Love finding SQLi vulnerabilities.',
        890.00,
        320,
        1
    ),
    (
        'charlie_dev',
        'pbkdf2_sha256$260000$test_hash_charlie',
        'charlie@example.com',
        1,
        'https://avatars.example.com/charlie.jpg',
        'Full-stack developer interested in application security.',
        450.75,
        180,
        1
    ),
    (
        'diana_admin',
        'pbkdf2_sha256$260000$test_hash_diana',
        'diana@example.com',
        4,
        'https://avatars.example.com/diana.jpg',
        'Security team lead at OWASP. Bug bounty program manager.',
        2100.00,
        650,
        1
    ),
    (
        'eve_newbie',
        'pbkdf2_sha256$260000$test_hash_eve',
        'eve@example.com',
        1,
        NULL,
        'New to bug bounties, learning the ropes!',
        50.00,
        25,
        1
    );

-- Insert test domains
INSERT INTO domains (name, url, email, is_active, has_security_txt, user) VALUES
    ('OWASP BLT', 'https://blt.owasp.org', 'support@owasp.org', 1, 1, 4),
    ('Example Corp', 'https://example.com', 'security@example.com', 1, 0, 1),
    ('Test Domain', 'https://test.example.org', 'test@example.org', 1, 1, 2);

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
    reporter_ip_address, cve_id, cve_score, domain, user, closed_by
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
        1,
        1,
        NULL
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
        2,
        2,
        4
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
        3,
        3,
        NULL
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
        1,
        4,
        NULL
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
        2,
        1,
        NULL
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

-- Insert bug team members (users collaborating on bugs)
INSERT INTO bug_team_members (bug_id, user_id) VALUES
    (1, 2), -- alice_hunter's XSS bug -> bob_security helping
    (1, 3), -- alice_hunter's XSS bug -> charlie_dev helping
    (2, 1), -- bob_security's SQL bug -> alice_hunter helping
    (4, 1), -- diana_admin's rate limit bug -> alice_hunter helping
    (4, 2); -- diana_admin's rate limit bug -> bob_security helping

-- Insert user follows (who follows whom)
INSERT INTO user_follows (follower_id, following_id) VALUES
    (5, 1), -- eve_newbie follows alice_hunter
    (5, 2), -- eve_newbie follows bob_security
    (5, 4), -- eve_newbie follows diana_admin
    (3, 1), -- charlie_dev follows alice_hunter
    (3, 4), -- charlie_dev follows diana_admin
    (2, 1), -- bob_security follows alice_hunter
    (1, 4), -- alice_hunter follows diana_admin
    (2, 4); -- bob_security follows diana_admin

-- Insert user bug upvotes
INSERT INTO user_bug_upvotes (user_id, bug_id) VALUES
    (1, 2), -- alice upvoted bob's SQL bug
    (1, 4), -- alice upvoted diana's rate limit bug
    (2, 1), -- bob upvoted alice's XSS bug
    (2, 4), -- bob upvoted diana's rate limit bug
    (3, 1), -- charlie upvoted alice's XSS bug
    (3, 2), -- charlie upvoted bob's SQL bug
    (4, 1), -- diana upvoted alice's XSS bug
    (4, 2), -- diana upvoted bob's SQL bug
    (4, 3), -- diana upvoted charlie's file upload bug
    (5, 1), -- eve upvoted alice's XSS bug
    (5, 2); -- eve upvoted bob's SQL bug

-- Insert user bug saves (bookmarks)
INSERT INTO user_bug_saves (user_id, bug_id) VALUES
    (1, 2), -- alice saved bob's SQL bug
    (1, 3), -- alice saved charlie's file upload bug
    (2, 1), -- bob saved alice's XSS bug
    (3, 1), -- charlie saved alice's XSS bug
    (3, 2), -- charlie saved bob's SQL bug
    (5, 1), -- eve saved alice's XSS bug
    (5, 2), -- eve saved bob's SQL bug
    (5, 4); -- eve saved diana's rate limit bug

-- Insert user bug flags (reported issues)
INSERT INTO user_bug_flags (user_id, bug_id, flag_reason) VALUES
    (3, 5, 'Duplicate of another bug report'),
    (4, 3, 'Needs more details and proof of concept');

-- Display inserted data
SELECT 'Users:' as info;
SELECT id, username, email, total_score, winnings, is_active FROM users;

SELECT 'Domains:' as info;
SELECT d.id, d.name, d.url, u.username as submitted_by FROM domains d
LEFT JOIN users u ON d.user = u.id;

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
    d.name as domain_name,
    u.username as reported_by,
    cu.username as closed_by
FROM bugs b
LEFT JOIN domains d ON b.domain = d.id
LEFT JOIN users u ON b.user = u.id
LEFT JOIN users cu ON b.closed_by = cu.id
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

SELECT 'Bug Team Members:' as info;
SELECT 
    b.id as bug_id,
    substr(b.description, 1, 40) as bug,
    u.username as team_member
FROM bug_team_members btm
JOIN bugs b ON btm.bug_id = b.id
JOIN users u ON btm.user_id = u.id
ORDER BY b.id;

SELECT 'User Follows (Social Graph):' as info;
SELECT 
    u1.username as follower,
    u2.username as following
FROM user_follows uf
JOIN users u1 ON uf.follower_id = u1.id
JOIN users u2 ON uf.following_id = u2.id
ORDER BY u1.username, u2.username;

SELECT 'User Bug Upvotes:' as info;
SELECT 
    u.username,
    substr(b.description, 1, 40) as bug_upvoted
FROM user_bug_upvotes ubu
JOIN users u ON ubu.user_id = u.id
JOIN bugs b ON ubu.bug_id = b.id
ORDER BY u.username;

SELECT 'User Bug Saves (Bookmarks):' as info;
SELECT 
    u.username,
    substr(b.description, 1, 40) as bug_saved
FROM user_bug_saves ubs
JOIN users u ON ubs.user_id = u.id
JOIN bugs b ON ubs.bug_id = b.id
ORDER BY u.username;

SELECT 'User Bug Flags:' as info;
SELECT 
    u.username,
    substr(b.description, 1, 40) as bug_flagged,
    ubf.flag_reason
FROM user_bug_flags ubf
JOIN users u ON ubf.user_id = u.id
JOIN bugs b ON ubf.bug_id = b.id
ORDER BY u.username;
