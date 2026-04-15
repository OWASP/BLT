UPDATE mentors SET referred_by = 'mdkaifansari04'
WHERE lower(github_username) = 'rinkitadhana' AND (referred_by IS NULL OR referred_by = '');

UPDATE mentors SET referred_by = 'mdkaifansari04'
WHERE lower(github_username) = 'rajgupta36' AND (referred_by IS NULL OR referred_by = '');

UPDATE mentors SET referred_by = 'arnavkirti'
WHERE lower(github_username) = 'shriyashsoni' AND (referred_by IS NULL OR referred_by = '');

UPDATE mentors SET referred_by = 'arnavkirti'
WHERE lower(github_username) = 'mohammedfaiyaz29' AND (referred_by IS NULL OR referred_by = '');

UPDATE mentors SET referred_by = 'pritz395'
WHERE lower(github_username) = 'vaswani2003' AND (referred_by IS NULL OR referred_by = '');

UPDATE mentors SET referred_by = 'pritz395'
WHERE lower(github_username) = 'kittenbytes' AND (referred_by IS NULL OR referred_by = '');

UPDATE mentors SET referred_by = 'e-esakman'
WHERE lower(github_username) = 'captain-t2004' AND (referred_by IS NULL OR referred_by = '');

UPDATE mentors SET referred_by = 's3dfx-cyber'
WHERE lower(github_username) = 'kunal1522' AND (referred_by IS NULL OR referred_by = '');

UPDATE mentors SET referred_by = 'rudra-rps'
WHERE lower(github_username) = 'rudrabhaskar9439' AND (referred_by IS NULL OR referred_by = '');

UPDATE mentors SET referred_by = 'rudra-rps'
WHERE lower(github_username) = 'dev-sanidhya' AND (referred_by IS NULL OR referred_by = '');

UPDATE mentors SET referred_by = 'sidd190'
WHERE lower(github_username) = 'vedantanand17' AND (referred_by IS NULL OR referred_by = '');

UPDATE mentors SET referred_by = 'vinamra'
WHERE lower(github_username) = 'preetham' AND (referred_by IS NULL OR referred_by = '');

UPDATE mentors SET referred_by = 'raj'
WHERE lower(github_username) = 'mdkaifansari04' AND (referred_by IS NULL OR referred_by = '');

UPDATE mentors SET referred_by = 'shirshjain'
WHERE lower(github_username) = 'ananya' AND (referred_by IS NULL OR referred_by = '');

UPDATE mentors SET referred_by = 'kunal1522'
WHERE lower(github_username) = 'saviodsouza' AND (referred_by IS NULL OR referred_by = '');

UPDATE mentors SET referred_by = 'manikandanchandran'
WHERE lower(github_username) = 'mohammedaashik' AND (referred_by IS NULL OR referred_by = '');

UPDATE mentors SET referred_by = 'manikandanchandran'
WHERE lower(github_username) = 'jayant' AND (referred_by IS NULL OR referred_by = '');

UPDATE mentors SET referred_by = 'rehan'
WHERE lower(github_username) = 'shazzahrazaidi' AND (referred_by IS NULL OR referred_by = '');

UPDATE mentors SET referred_by = 'rishab87'
WHERE lower(github_username) = 'sidd190' AND (referred_by IS NULL OR referred_by = '');

UPDATE mentors SET referred_by = 'jisan'
WHERE lower(github_username) = 'rosai' AND (referred_by IS NULL OR referred_by = '');

UPDATE mentors SET referred_by = 'aadityasharma'
WHERE lower(github_username) = 'shubhangpathak' AND (referred_by IS NULL OR referred_by = '');

UPDATE mentors SET referred_by = 'akshaybehl'
WHERE lower(github_username) = 'sakshee' AND (referred_by IS NULL OR referred_by = '');

-- arnavkirti referred_by intentionally omitted: shriyashsoni → arnavkirti is recorded below,
-- so arnavkirti → shriyashsoni would be a circular reference.

UPDATE mentors SET referred_by = 'kunal1522'
WHERE lower(github_username) = 'shivanandu' AND (referred_by IS NULL OR referred_by = '');

INSERT INTO contributor_referrals (org, month_key, referrer_login, referred_login, repo, issue_number, created_at)
VALUES ('OWASP-BLT', '2026-04', lower('vinamra'), lower('preetham'), 'BLT-Pool', 0, 1744329600)
ON CONFLICT (org, month_key, referrer_login, referred_login) DO NOTHING;

INSERT INTO contributor_referrals (org, month_key, referrer_login, referred_login, repo, issue_number, created_at)
VALUES ('OWASP-BLT', '2026-04', lower('carla'), lower('preetham'), 'BLT-Pool', 0, 1744329600)
ON CONFLICT (org, month_key, referrer_login, referred_login) DO NOTHING;

INSERT INTO contributor_referrals (org, month_key, referrer_login, referred_login, repo, issue_number, created_at)
VALUES ('OWASP-BLT', '2026-04', lower('raj'), lower('mdkaifansari04'), 'BLT-Pool', 0, 1744329600)
ON CONFLICT (org, month_key, referrer_login, referred_login) DO NOTHING;

INSERT INTO contributor_referrals (org, month_key, referrer_login, referred_login, repo, issue_number, created_at)
VALUES ('OWASP-BLT', '2026-04', lower('rinkitadhana'), lower('mdkaifansari04'), 'BLT-Pool', 0, 1744329600)
ON CONFLICT (org, month_key, referrer_login, referred_login) DO NOTHING;

INSERT INTO contributor_referrals (org, month_key, referrer_login, referred_login, repo, issue_number, created_at)
VALUES ('OWASP-BLT', '2026-04', lower('shirshjain'), lower('ananya'), 'BLT-Pool', 0, 1744329600)
ON CONFLICT (org, month_key, referrer_login, referred_login) DO NOTHING;

INSERT INTO contributor_referrals (org, month_key, referrer_login, referred_login, repo, issue_number, created_at)
VALUES ('OWASP-BLT', '2026-04', lower('ankitsinghsisodya'), lower('ananya'), 'BLT-Pool', 0, 1744329600)
ON CONFLICT (org, month_key, referrer_login, referred_login) DO NOTHING;

INSERT INTO contributor_referrals (org, month_key, referrer_login, referred_login, repo, issue_number, created_at)
VALUES ('OWASP-BLT', '2026-04', lower('kunal1522'), lower('saviodsouza'), 'BLT-Pool', 0, 1744329600)
ON CONFLICT (org, month_key, referrer_login, referred_login) DO NOTHING;

INSERT INTO contributor_referrals (org, month_key, referrer_login, referred_login, repo, issue_number, created_at)
VALUES ('OWASP-BLT', '2026-04', lower('chigorin'), lower('saviodsouza'), 'BLT-Pool', 0, 1744329600)
ON CONFLICT (org, month_key, referrer_login, referred_login) DO NOTHING;

INSERT INTO contributor_referrals (org, month_key, referrer_login, referred_login, repo, issue_number, created_at)
VALUES ('OWASP-BLT', '2026-04', lower('manikandanchandran'), lower('mohammedaashik'), 'BLT-Pool', 0, 1744329600)
ON CONFLICT (org, month_key, referrer_login, referred_login) DO NOTHING;

INSERT INTO contributor_referrals (org, month_key, referrer_login, referred_login, repo, issue_number, created_at)
VALUES ('OWASP-BLT', '2026-04', lower('manikandanchandran'), lower('jayant'), 'BLT-Pool', 0, 1744329600)
ON CONFLICT (org, month_key, referrer_login, referred_login) DO NOTHING;

INSERT INTO contributor_referrals (org, month_key, referrer_login, referred_login, repo, issue_number, created_at)
VALUES ('OWASP-BLT', '2026-04', lower('bishaldas'), lower('jayant'), 'BLT-Pool', 0, 1744329600)
ON CONFLICT (org, month_key, referrer_login, referred_login) DO NOTHING;

INSERT INTO contributor_referrals (org, month_key, referrer_login, referred_login, repo, issue_number, created_at)
VALUES ('OWASP-BLT', '2026-04', lower('rehan'), lower('shazzahrazaidi'), 'BLT-Pool', 0, 1744329600)
ON CONFLICT (org, month_key, referrer_login, referred_login) DO NOTHING;

INSERT INTO contributor_referrals (org, month_key, referrer_login, referred_login, repo, issue_number, created_at)
VALUES ('OWASP-BLT', '2026-04', lower('rishab87'), lower('sidd190'), 'BLT-Pool', 0, 1744329600)
ON CONFLICT (org, month_key, referrer_login, referred_login) DO NOTHING;
-- vedantanand17 → sidd190 removed: mentors.referred_by for sidd190 is 'rishab87', not vedantanand17 (avoids double-credit)

INSERT INTO contributor_referrals (org, month_key, referrer_login, referred_login, repo, issue_number, created_at)
VALUES ('OWASP-BLT', '2026-04', lower('jisan'), lower('rosai'), 'BLT-Pool', 0, 1744329600)
ON CONFLICT (org, month_key, referrer_login, referred_login) DO NOTHING;

INSERT INTO contributor_referrals (org, month_key, referrer_login, referred_login, repo, issue_number, created_at)
VALUES ('OWASP-BLT', '2026-04', lower('shivam'), lower('rosai'), 'BLT-Pool', 0, 1744329600)
ON CONFLICT (org, month_key, referrer_login, referred_login) DO NOTHING;

INSERT INTO contributor_referrals (org, month_key, referrer_login, referred_login, repo, issue_number, created_at)
VALUES ('OWASP-BLT', '2026-04', lower('aadityasharma'), lower('shubhangpathak'), 'BLT-Pool', 0, 1744329600)
ON CONFLICT (org, month_key, referrer_login, referred_login) DO NOTHING;

INSERT INTO contributor_referrals (org, month_key, referrer_login, referred_login, repo, issue_number, created_at)
VALUES ('OWASP-BLT', '2026-04', lower('akshaybehl'), lower('sakshee'), 'BLT-Pool', 0, 1744329600)
ON CONFLICT (org, month_key, referrer_login, referred_login) DO NOTHING;

INSERT INTO contributor_referrals (org, month_key, referrer_login, referred_login, repo, issue_number, created_at)
VALUES ('OWASP-BLT', '2026-04', lower('arpitchaudhary'), lower('sakshee'), 'BLT-Pool', 0, 1744329600)
ON CONFLICT (org, month_key, referrer_login, referred_login) DO NOTHING;

INSERT INTO contributor_referrals (org, month_key, referrer_login, referred_login, repo, issue_number, created_at)
VALUES ('OWASP-BLT', '2026-04', lower('vedantanand17'), lower('sakshee'), 'BLT-Pool', 0, 1744329600)
ON CONFLICT (org, month_key, referrer_login, referred_login) DO NOTHING;

INSERT INTO contributor_referrals (org, month_key, referrer_login, referred_login, repo, issue_number, created_at)
VALUES ('OWASP-BLT', '2026-04', lower('sakshamgupta'), lower('sakshee'), 'BLT-Pool', 0, 1744329600)
ON CONFLICT (org, month_key, referrer_login, referred_login) DO NOTHING;

INSERT INTO contributor_referrals (org, month_key, referrer_login, referred_login, repo, issue_number, created_at)
VALUES ('OWASP-BLT', '2026-04', lower('shriyashsoni'), lower('arnavkirti'), 'BLT-Pool', 0, 1744329600)
ON CONFLICT (org, month_key, referrer_login, referred_login) DO NOTHING;

INSERT INTO contributor_referrals (org, month_key, referrer_login, referred_login, repo, issue_number, created_at)
VALUES ('OWASP-BLT', '2026-04', lower('mohammedfaiyaz29'), lower('arnavkirti'), 'BLT-Pool', 0, 1744329600)
ON CONFLICT (org, month_key, referrer_login, referred_login) DO NOTHING;

INSERT INTO contributor_referrals (org, month_key, referrer_login, referred_login, repo, issue_number, created_at)
VALUES ('OWASP-BLT', '2026-04', lower('mariyan-zarev'), lower('arnavkirti'), 'BLT-Pool', 0, 1744329600)
ON CONFLICT (org, month_key, referrer_login, referred_login) DO NOTHING;

INSERT INTO contributor_referrals (org, month_key, referrer_login, referred_login, repo, issue_number, created_at)
VALUES ('OWASP-BLT', '2026-04', lower('tanishtyagi'), lower('arnavkirti'), 'BLT-Pool', 0, 1744329600)
ON CONFLICT (org, month_key, referrer_login, referred_login) DO NOTHING;

INSERT INTO contributor_referrals (org, month_key, referrer_login, referred_login, repo, issue_number, created_at)
VALUES ('OWASP-BLT', '2026-04', lower('ankitshankar'), lower('arnavkirti'), 'BLT-Pool', 0, 1744329600)
ON CONFLICT (org, month_key, referrer_login, referred_login) DO NOTHING;

INSERT INTO contributor_referrals (org, month_key, referrer_login, referred_login, repo, issue_number, created_at)
VALUES ('OWASP-BLT', '2026-04', lower('kunal1522'), lower('shivanandu'), 'BLT-Pool', 0, 1744329600)
ON CONFLICT (org, month_key, referrer_login, referred_login) DO NOTHING;

INSERT INTO contributor_referrals (org, month_key, referrer_login, referred_login, repo, issue_number, created_at)
VALUES ('OWASP-BLT', '2026-04', lower('aryanjain'), lower('shivanandu'), 'BLT-Pool', 0, 1744329600)
ON CONFLICT (org, month_key, referrer_login, referred_login) DO NOTHING;

UPDATE mentors SET referred_by = 'sakshamgupta'
WHERE lower(github_username) = 'swaparupmukherjee' AND (referred_by IS NULL OR referred_by = '');

INSERT INTO contributor_referrals (org, month_key, referrer_login, referred_login, repo, issue_number, created_at)
VALUES ('OWASP-BLT', '2026-04', lower('sakshamgupta'), lower('swaparupmukherjee'), 'BLT-Pool', 0, 1744329600)
ON CONFLICT (org, month_key, referrer_login, referred_login) DO NOTHING;

INSERT INTO contributor_referrals (org, month_key, referrer_login, referred_login, repo, issue_number, created_at)
VALUES ('OWASP-BLT', '2026-04', lower('sarafarajnasardi'), lower('swaparupmukherjee'), 'BLT-Pool', 0, 1744329600)
ON CONFLICT (org, month_key, referrer_login, referred_login) DO NOTHING;

UPDATE mentors SET referred_by = 'gauravarora'
WHERE lower(github_username) = 'devislodhwal' AND (referred_by IS NULL OR referred_by = '');

INSERT INTO contributor_referrals (org, month_key, referrer_login, referred_login, repo, issue_number, created_at)
VALUES ('OWASP-BLT', '2026-04', lower('gauravarora'), lower('devislodhwal'), 'BLT-Pool', 0, 1744329600)
ON CONFLICT (org, month_key, referrer_login, referred_login) DO NOTHING;

UPDATE mentors SET referred_by = 'sahildhillon'
WHERE lower(github_username) = 'amoghsunil' AND (referred_by IS NULL OR referred_by = '');

INSERT INTO contributor_referrals (org, month_key, referrer_login, referred_login, repo, issue_number, created_at)
VALUES ('OWASP-BLT', '2026-04', lower('sahildhillon'), lower('amoghsunil'), 'BLT-Pool', 0, 1744329600)
ON CONFLICT (org, month_key, referrer_login, referred_login) DO NOTHING;

UPDATE mentors SET referred_by = 'rudra9439'
WHERE lower(github_username) = 'rudrapratapsingh' AND (referred_by IS NULL OR referred_by = '');

INSERT INTO contributor_referrals (org, month_key, referrer_login, referred_login, repo, issue_number, created_at)
VALUES ('OWASP-BLT', '2026-04', lower('rudra9439'), lower('rudrapratapsingh'), 'BLT-Pool', 0, 1744329600)
ON CONFLICT (org, month_key, referrer_login, referred_login) DO NOTHING;

INSERT INTO contributor_referrals (org, month_key, referrer_login, referred_login, repo, issue_number, created_at)
VALUES ('OWASP-BLT', '2026-04', lower('sanidhyashishodia'), lower('rudrapratapsingh'), 'BLT-Pool', 0, 1744329600)
ON CONFLICT (org, month_key, referrer_login, referred_login) DO NOTHING;
