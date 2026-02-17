-- Test data for local development

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
