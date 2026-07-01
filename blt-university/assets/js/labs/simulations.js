(function () {
    window.BltLabs = window.BltLabs || {};
    const BltLabs = window.BltLabs;
    const {
        renderCodeFixSimulation,
        validateAuthFix,
        validateCommandFix,
        validateCsrfFix,
        validateIdorFix,
        validateRedirectFix,
        validateSensitiveDataFix,
        validateSqliFix,
        validateSsrfFix,
        validateUploadFix,
        validateXssFix
    } = BltLabs;

    function renderSqliLoginSimulation(container, config, context) {
        renderCodeFixSimulation(container, config, context, {
            engine: 'sqli-login',
            title: 'SQL Injection Login Bypass',
            validateFix: validateSqliFix,
            fixGuidance: [
                {
                    title: 'Separate SQL from data',
                    body: 'Keep the SQL statement static and put untrusted values in a separate parameter list.',
                    code: "const query = 'SELECT * FROM users WHERE username = ? AND password = ?';\ndb.execute(query, [username, password]);"
                },
                {
                    title: 'Placeholder styles vary',
                    body: 'Many drivers use ? placeholders. PostgreSQL often uses $1, $2. Both are safe when values are bound separately.',
                    code: "db.query('SELECT * FROM users WHERE username = $1', [username]);"
                },
                {
                    title: 'What to avoid',
                    body: "String concatenation lets payloads like ' OR '1'='1 change the query structure.",
                    code: "query = \"... username = '\" + username + \"'\";"
                }
            ],
            messages: {
                identifyPrompt: 'Select the line where user input is joined into the SQL query.',
                identifyError: 'Not quite. Select the line where user input is joined into the SQL query.',
                explainError: 'Choose the answer that explains how the payload changes SQL logic.',
                fixPrompt: 'Rewrite the query using placeholders and pass user values separately.',
                fixGoal: 'Protect the login query from SQL injection.',
                fixError: 'The fix is close, but the validator still sees SQL injection risk.',
                complete: 'You identified the vulnerable line, explained the risk, and fixed the query.'
            }
        });
    }

    function renderSqliVariantSimulation(container, config, context, engine, title, messages) {
        renderCodeFixSimulation(container, config, context, {
            engine,
            title,
            validateFix: validateSqliFix,
            fixGuidance: [
                {
                    title: 'Keep the query shape fixed',
                    body: 'Build one static SQL statement and place every user-controlled value in a parameter list.',
                    code: "const query = 'SELECT id, name, price, description FROM products WHERE name LIKE ?';\ndb.execute(query, [`%${search}%`]);"
                },
                {
                    title: 'Bind inference inputs too',
                    body: 'Blind and time-based checks still need placeholders. The database should receive values, not SQL fragments.',
                    code: "db.query('SELECT id FROM profiles WHERE user_id = $1', [userId]);"
                },
                {
                    title: 'What to avoid',
                    body: 'Never concatenate search terms, IDs, ORDER BY values, or timing probes directly into SQL.',
                    code: "query = '... WHERE id = ' + userId;"
                }
            ],
            messages
        });
    }

    function renderSqliUnionSimulation(container, config, context) {
        renderSqliVariantSimulation(container, config, context, 'sqli-union', 'Union SQL Injection Defense', {
            identifyPrompt: 'Select the line where the search term is concatenated into a query that returns table columns.',
            identifyError: 'Not quite. Select the line where the search term changes the SELECT query.',
            explainError: 'Choose the answer that explains why UNION can append rows from another table.',
            fixPrompt: 'Parameterize the search term so UNION payloads are treated as data.',
            fixGoal: 'Stop UNION payloads from changing the product search query.',
            fixError: 'The fix still needs a static query, placeholders, and separate bound values.',
            complete: 'You identified the UNION injection point, explained the column-matching risk, and fixed the query.'
        });
    }

    function renderSqliBlindSimulation(container, config, context) {
        renderSqliVariantSimulation(container, config, context, 'sqli-blind', 'Blind SQL Injection Defense', {
            identifyPrompt: 'Select the line where the user ID can change a Boolean condition in SQL.',
            identifyError: 'Not quite. Select the query line that lets input alter SQL logic.',
            explainError: 'Choose the answer that explains how response differences leak data.',
            fixPrompt: 'Bind the user ID as a parameter so Boolean probes cannot alter the WHERE clause.',
            fixGoal: 'Stop Boolean probes from changing profile lookup behavior.',
            fixError: 'The fix still needs a parameterized query with the user ID bound separately.',
            complete: 'You identified the blind injection point, explained the inference channel, and fixed the lookup.'
        });
    }

    function renderSqliTimeSimulation(container, config, context) {
        renderSqliVariantSimulation(container, config, context, 'sqli-time', 'Time-Based SQL Injection Defense', {
            identifyPrompt: 'Select the line where the article ID can inject a time-delay expression.',
            identifyError: 'Not quite. Select the query line where user input reaches SQL.',
            explainError: 'Choose the answer that explains how response time becomes a data signal.',
            fixPrompt: 'Bind the article ID as a parameter so SLEEP payloads stay inert data.',
            fixGoal: 'Stop timing payloads from changing article lookup behavior.',
            fixError: 'The fix still needs a static query, placeholder, and separate parameter binding.',
            complete: 'You identified the timing injection point, explained the delay signal, and fixed the query.'
        });
    }

    function renderReflectedXssSimulation(container, config, context) {
        renderCodeFixSimulation(container, config, context, {
            engine: 'xss-reflected',
            title: 'Reflected XSS Comment System',
            validateFix: validateXssFix,
            fixGuidance: [
                {
                    title: 'Prefer text sinks',
                    body: 'If the content should be text, use textContent so the browser does not parse tags or event handlers.',
                    code: 'preview.textContent = comment;'
                },
                {
                    title: 'Encode before HTML contexts',
                    body: 'If you must render into HTML, encode <, >, &, quotes, and apostrophes before insertion.',
                    code: 'preview.innerHTML = escapeHTML(comment);'
                },
                {
                    title: 'What to avoid',
                    body: 'innerHTML with raw user input turns payloads into executable markup.',
                    code: 'preview.innerHTML = comment;'
                }
            ],
            messages: {
                identifyPrompt: 'Select the line that renders untrusted input as HTML.',
                identifyError: 'Not quite. Look for the line that writes user input into the page as HTML.',
                explainError: 'Choose the answer that explains why the script can execute in another user browser.',
                fixPrompt: 'Render the comment as text or encode HTML before displaying it.',
                fixGoal: 'Render untrusted comments without executing attacker-controlled markup.',
                fixError: 'The fix still allows untrusted HTML to reach an executable sink.',
                complete: 'You identified the unsafe HTML sink, explained the XSS risk, and rendered input safely.'
            }
        });
    }

    function renderXssVariantSimulation(container, config, context, engine, title, messages) {
        renderCodeFixSimulation(container, config, context, {
            engine,
            title,
            validateFix: validateXssFix,
            fixGuidance: [
                {
                    title: 'Prefer safe text sinks',
                    body: 'Use textContent or createTextNode when user content should be displayed as text.',
                    code: 'profileBio.textContent = bio;'
                },
                {
                    title: 'Encode before HTML contexts',
                    body: 'If markup is required, encode dangerous characters or use a trusted sanitizer.',
                    code: 'result.innerHTML = escapeHTML(searchTerm);'
                },
                {
                    title: 'What to avoid',
                    body: 'Filters that only block a few strings are bypassable. Do not write raw input into HTML.',
                    code: 'output.innerHTML = userInput;'
                }
            ],
            messages
        });
    }

    function renderStoredXssSimulation(container, config, context) {
        renderXssVariantSimulation(container, config, context, 'xss-stored', 'Stored XSS Profile Defense', {
            identifyPrompt: 'Select the line that renders stored profile data as executable HTML.',
            identifyError: 'Not quite. Select the line that writes the stored bio into the page as HTML.',
            explainError: 'Choose the answer that explains why every profile viewer is affected.',
            fixPrompt: 'Render stored profile content as text or sanitize it before display.',
            fixGoal: 'Prevent stored profile data from executing script for future viewers.',
            fixError: 'The fix still allows untrusted stored HTML to reach an executable sink.',
            complete: 'You identified stored XSS, explained persistence, and rendered profile content safely.'
        });
    }

    function renderXssFilterBypassSimulation(container, config, context) {
        renderXssVariantSimulation(container, config, context, 'xss-filter-bypass', 'XSS Filter Bypass Defense', {
            identifyPrompt: 'Select the line where filtered input is still inserted as HTML.',
            identifyError: 'Not quite. Select the line where the filtered search term reaches an HTML sink.',
            explainError: 'Choose the answer that explains why blocklists miss alternate payloads.',
            fixPrompt: 'Replace blocklist filtering with safe output encoding or a text sink.',
            fixGoal: 'Prevent bypass payloads from executing through the search result.',
            fixError: 'The fix still relies on unsafe HTML rendering or insufficient encoding.',
            complete: 'You identified the bypassable sink, explained blocklist weakness, and fixed rendering.'
        });
    }

    function renderDomXssSimulation(container, config, context) {
        renderXssVariantSimulation(container, config, context, 'xss-dom', 'DOM XSS Defense', {
            identifyPrompt: 'Select the client-side line that writes URL fragment data into HTML.',
            identifyError: 'Not quite. Select the DOM assignment that parses attacker-controlled markup.',
            explainError: 'Choose the answer that explains why this happens entirely in the browser.',
            fixPrompt: 'Treat fragment data as text or sanitize it before updating the DOM.',
            fixGoal: 'Stop URL fragment content from becoming executable DOM.',
            fixError: 'The fix still allows fragment data to reach an unsafe HTML sink.',
            complete: 'You identified DOM XSS, explained the client-side data flow, and fixed the sink.'
        });
    }

    function renderXssCookieTheftSimulation(container, config, context) {
        renderXssVariantSimulation(container, config, context, 'xss-cookie-theft', 'XSS Cookie Theft Defense', {
            identifyPrompt: 'Select the line that renders user messages as executable HTML.',
            identifyError: 'Not quite. Select the message rendering line that allows script execution.',
            explainError: 'Choose the answer that explains how script execution exposes browser data.',
            fixPrompt: 'Render messages safely and avoid exposing sensitive cookies to JavaScript.',
            fixGoal: 'Prevent message payloads from executing and reading cookie data.',
            fixError: 'The fix still allows untrusted HTML into the page.',
            complete: 'You identified the cookie-theft path, explained the impact, and fixed rendering.'
        });
    }

    function renderCsrfFormSimulation(container, config, context) {
        renderCodeFixSimulation(container, config, context, {
            engine: 'csrf-form',
            title: 'CSRF Email Change Defense',
            validateFix: validateCsrfFix,
            fixGuidance: [
                {
                    title: 'Add request intent',
                    body: 'State-changing forms should include a per-session CSRF token that attackers cannot guess.',
                    code: '<input type="hidden" name="csrf_token" value="{{ csrfToken }}">'
                },
                {
                    title: 'Verify on the server',
                    body: 'The server must compare the submitted token with the session token before changing data.',
                    code: 'verifyCsrfToken(req.body.csrf_token, req.session.csrf_token);'
                },
                {
                    title: 'Harden cookies',
                    body: 'SameSite cookies reduce automatic cross-site cookie sending and complement token validation.',
                    code: "session({ cookie: { sameSite: 'Lax' } })"
                }
            ],
            messages: {
                identifyPrompt: 'Select the line that updates state without verifying request intent.',
                identifyError: 'Not quite. Select the state-changing line that runs without CSRF validation.',
                explainError: 'Choose the answer that explains why an attacker can force this request.',
                fixPrompt: 'Add a CSRF token to the form, verify it server-side, and harden the session cookie.',
                fixGoal: 'Protect this endpoint from CSRF.',
                fixError: 'The fix still needs token presence, server-side validation, and cookie hardening.',
                complete: 'You identified the missing request-intent check and added CSRF defenses.'
            }
        });
    }

    function renderCsrfVariantSimulation(container, config, context, engine, title, messages) {
        renderCodeFixSimulation(container, config, context, {
            engine,
            title,
            validateFix: validateCsrfFix,
            fixGuidance: [
                {
                    title: 'Require request intent',
                    body: 'State-changing requests should include an unpredictable CSRF token tied to the user session.',
                    code: '<input type="hidden" name="csrf_token" value="{{ csrfToken }}">'
                },
                {
                    title: 'Verify before action',
                    body: 'Reject the request before changing data if the submitted token does not match the session.',
                    code: 'verifyCsrfToken(req.body.csrf_token, req.session.csrf_token);'
                },
                {
                    title: 'Harden cookies',
                    body: 'SameSite cookies reduce automatic cross-site cookie sending and complement token validation.',
                    code: "session({ cookie: { sameSite: 'Lax' } })"
                }
            ],
            messages
        });
    }

    function renderCsrfAutoSubmitSimulation(container, config, context) {
        renderCsrfVariantSimulation(container, config, context, 'csrf-auto-submit', 'Auto-Submit CSRF Defense', {
            identifyPrompt: 'Select the state-changing transfer line that runs without CSRF validation.',
            identifyError: 'Not quite. Select the line that transfers funds before verifying request intent.',
            explainError: 'Choose the answer that explains why auto-submit can trigger the request.',
            fixPrompt: 'Require and verify a CSRF token before transferring money, then harden cookies.',
            fixGoal: 'Protect the transfer endpoint from auto-submitted cross-site forms.',
            fixError: 'The fix still needs token presence, server validation, and SameSite cookie protection.',
            complete: 'You identified the auto-submit CSRF path and added request-intent defenses.'
        });
    }

    function renderCsrfImageSimulation(container, config, context) {
        renderCsrfVariantSimulation(container, config, context, 'csrf-image', 'Image CSRF Defense', {
            identifyPrompt: 'Select the GET route that deletes an account based only on a query string.',
            identifyError: 'Not quite. Select the destructive route that an image load can trigger.',
            explainError: 'Choose the answer that explains why GET endpoints should not change state.',
            fixPrompt: 'Move deletion behind a POST flow with CSRF validation and hardened cookies.',
            fixGoal: 'Prevent image loads from triggering account deletion.',
            fixError: 'The fix still needs token presence, server validation, and SameSite cookie protection.',
            complete: 'You identified the image-triggered CSRF path and protected the destructive action.'
        });
    }

    function renderCsrfAjaxSimulation(container, config, context) {
        renderCsrfVariantSimulation(container, config, context, 'csrf-ajax', 'AJAX CSRF Defense', {
            identifyPrompt: 'Select the password change line that trusts the request without token validation.',
            identifyError: 'Not quite. Select the line that changes the password before CSRF validation.',
            explainError: 'Choose the answer that explains why AJAX still needs request-intent checks.',
            fixPrompt: 'Validate a CSRF token from the request body or header before changing the password.',
            fixGoal: 'Protect the password endpoint from cross-site JavaScript requests.',
            fixError: 'The fix still needs token presence, server validation, and SameSite cookie protection.',
            complete: 'You identified the AJAX CSRF path and added token-based defenses.'
        });
    }

    function renderIdorProfileSimulation(container, config, context) {
        renderCodeFixSimulation(container, config, context, {
            engine: 'idor-profile',
            title: 'IDOR Profile Access Defense',
            validateFix: validateIdorFix,
            fixGuidance: [
                {
                    title: 'Do not trust object IDs alone',
                    body: 'Route parameters identify the requested object, not whether the current user is allowed to read it.',
                    code: 'const profile = db.getUserProfile(request.params.userId);'
                },
                {
                    title: 'Compare owner to session user',
                    body: 'Load the resource, then verify that its owner matches the authenticated user before returning it.',
                    code: "if (!profile || profile.userId !== request.user.id) {\n  return response.status(403).json({ error: 'Forbidden' });\n}"
                },
                {
                    title: 'Centralize authorization',
                    body: 'A helper such as canAccessProfile(user, profile) keeps the ownership rule consistent across routes.',
                    code: 'if (!canAccessProfile(request.user, profile)) return response.status(403).end();'
                }
            ],
            messages: {
                identifyPrompt: 'Select the line that returns a profile based only on a user-controlled object ID.',
                identifyError: 'Not quite. Select the line where the requested profile is returned without an ownership check.',
                explainError: 'Choose the answer that explains why changing the URL can expose another user profile.',
                fixPrompt: 'Verify that the authenticated user owns or is allowed to access the requested profile before returning it.',
                fixGoal: 'Prevent users from reading profiles that belong to someone else.',
                fixError: 'The fix still needs authenticated identity, an ownership/authorization check, and a rejection path.',
                complete: 'You identified the missing object-level authorization check and protected the profile route.'
            }
        });
    }

    function messageSet(config, fallbackTitle, fallbackMessages = {}) {
        return {
            title: config.title || fallbackTitle,
            identifyPrompt: config.identify_prompt || fallbackMessages.identifyPrompt || 'Select the vulnerable line where untrusted input creates the security risk.',
            identifyError: config.identify_error || fallbackMessages.identifyError || 'Not quite. Select the line where untrusted input reaches the risky operation.',
            explainError: config.explain_error || fallbackMessages.explainError || 'Choose the answer that best explains the vulnerability.',
            fixPrompt: config.fix_prompt || fallbackMessages.fixPrompt || 'Rewrite the code to use the secure pattern described in the objective.',
            fixGoal: config.fix_goal || fallbackMessages.fixGoal || config.success_criteria || 'Fix the vulnerable implementation.',
            fixError: config.fix_error || fallbackMessages.fixError || 'The fix is close, but one or more required defensive checks are still missing.',
            complete: config.complete_message || fallbackMessages.complete || 'You identified the issue, explained the risk, and implemented the fix.'
        };
    }

    function genericGuidance(config, defaults = []) {
        if (Array.isArray(config.fix_guidance) && config.fix_guidance.length) {
            return config.fix_guidance;
        }

        return defaults;
    }

    function renderFamilySimulation(container, config, context, options) {
        renderCodeFixSimulation(container, config, context, {
            engine: config.engine || context.engine || options.engine,
            title: config.title || options.title,
            validateFix: options.validateFix,
            fixGuidance: genericGuidance(config, options.fixGuidance),
            messages: messageSet(config, options.title, options.messages),
            language: options.language || 'JS'
        });
    }

    function renderOpenRedirectSimulation(container, config, context) {
        renderFamilySimulation(container, config, context, {
            title: 'Open Redirect Defense',
            validateFix: validateRedirectFix,
            fixGuidance: [
                {
                    title: 'Prefer internal paths',
                    body: 'Map return destinations to known internal routes instead of accepting arbitrary URLs.',
                    code: "const allowedPaths = ['/dashboard', '/settings'];"
                },
                {
                    title: 'Parse before redirecting',
                    body: 'Normalize URLs and compare host, protocol, and path before sending the redirect.',
                    code: "const parsed = new URL(next, 'https://app.example');"
                },
                {
                    title: 'Block dangerous schemes',
                    body: 'Reject protocol-relative URLs and schemes such as javascript: or data:.',
                    code: "if (next.startsWith('//') || /^javascript:/i.test(next)) reject();"
                }
            ],
            messages: {
                identifyPrompt: 'Select the line that redirects to a user-controlled destination.',
                identifyError: 'Not quite. Select the line that passes raw redirect input into the redirect response.',
                fixPrompt: 'Allow only trusted internal paths or allowlisted destinations before redirecting.',
                fixGoal: 'Prevent attacker-controlled redirect destinations.',
                complete: 'You identified the open redirect, explained the phishing risk, and restricted redirect destinations.'
            }
        });
    }

    function renderCommandInjectionSimulation(container, config, context) {
        renderFamilySimulation(container, config, context, {
            title: 'Command Injection Defense',
            validateFix: validateCommandFix,
            fixGuidance: [
                {
                    title: 'Avoid the shell',
                    body: 'Use APIs that pass executable and arguments separately instead of building a command string.',
                    code: "spawn('ping', ['-c', '1', ip], { shell: false });"
                },
                {
                    title: 'Validate strictly',
                    body: 'Allow only expected IPs, hostnames, or named actions before invoking any system tool.',
                    code: 'if (!net.isIP(ip)) throw new Error("Invalid IP");'
                },
                {
                    title: 'No metacharacters',
                    body: 'Reject shell separators and substitutions such as ;, |, &, $, and backticks.',
                    code: "if (/[;&|`$<>]/.test(input)) reject();"
                }
            ],
            messages: {
                identifyPrompt: 'Select the line where user input is inserted into an operating-system command.',
                identifyError: 'Not quite. Select the command execution line that includes user-controlled input.',
                fixPrompt: 'Use a safe command API with separate arguments, strict input validation, and no shell metacharacters.',
                fixGoal: 'Prevent user input from changing the executed operating-system command.',
                complete: 'You identified command injection, explained the shell risk, and replaced it with a safe command pattern.'
            }
        });
    }

    function renderFileUploadSimulation(container, config, context) {
        renderFamilySimulation(container, config, context, {
            title: 'File Upload Defense',
            validateFix: validateUploadFix,
            fixGuidance: [
                {
                    title: 'Allowlist file types',
                    body: 'Check extension, MIME type, and magic bytes against a small allowed set.',
                    code: "const allowedExtensions = ['.jpg', '.png', '.pdf'];"
                },
                {
                    title: 'Rename and isolate',
                    body: 'Generate server-side filenames and store uploads outside the web root.',
                    code: 'const safeName = `${crypto.randomUUID()}.jpg`;'
                },
                {
                    title: 'Block traversal',
                    body: 'Never trust original filenames or path parameters when writing uploaded files.',
                    code: 'const name = path.basename(upload.originalname);'
                }
            ],
            messages: {
                identifyPrompt: 'Select the line where uploaded file data or filenames are trusted unsafely.',
                identifyError: 'Not quite. Select the file handling line that trusts user-controlled upload data.',
                fixPrompt: 'Restrict file types, verify content, store safely, and prevent path traversal.',
                fixGoal: 'Prevent malicious uploads from executing or escaping the upload directory.',
                complete: 'You identified the upload flaw, explained the risk, and added layered upload defenses.'
            }
        });
    }

    function renderSensitiveDataSimulation(container, config, context) {
        renderFamilySimulation(container, config, context, {
            title: 'Sensitive Data Exposure Defense',
            validateFix: validateSensitiveDataFix,
            fixGuidance: [
                {
                    title: 'Redact output',
                    body: 'Return generic errors and remove secrets before sending responses or logs.',
                    code: 'logger.error(redact(error));'
                },
                {
                    title: 'Use managed secrets',
                    body: 'Load credentials from environment or a secrets manager instead of public files.',
                    code: 'const dbPassword = secretManager.getSecret("DB_PASSWORD");'
                },
                {
                    title: 'Protect storage',
                    body: 'Encrypt sensitive exports, hash passwords, and require authorization for private files.',
                    code: 'const hash = await argon2.hash(password);'
                }
            ],
            messages: {
                identifyPrompt: 'Select the line that exposes a secret, credential, or sensitive file.',
                identifyError: 'Not quite. Select the line that leaks sensitive data to a response, log, or public file.',
                fixPrompt: 'Redact secrets, use managed configuration, and protect sensitive storage or responses.',
                fixGoal: 'Prevent secrets and sensitive data from being exposed.',
                complete: 'You identified the sensitive data leak, explained the impact, and added protective controls.'
            }
        });
    }

    function renderSsrfSimulation(container, config, context) {
        renderFamilySimulation(container, config, context, {
            title: 'SSRF Defense',
            validateFix: validateSsrfFix,
            fixGuidance: [
                {
                    title: 'Allow trusted hosts',
                    body: 'Parse the URL and allow only expected protocols and hostnames.',
                    code: "const allowedHosts = ['images.example.com'];"
                },
                {
                    title: 'Block internal ranges',
                    body: 'Reject loopback, private networks, and cloud metadata IP addresses.',
                    code: "if (host === '169.254.169.254' || isPrivateIp(host)) reject();"
                },
                {
                    title: 'Control redirects',
                    body: 'Disable automatic redirects or re-validate every redirect hop.',
                    code: 'fetch(url, { redirect: "manual" });'
                }
            ],
            messages: {
                identifyPrompt: 'Select the line where the server fetches a user-controlled URL.',
                identifyError: 'Not quite. Select the server-side request line that uses attacker-controlled input.',
                fixPrompt: 'Allow only trusted outbound destinations, block internal networks, and restrict redirects.',
                fixGoal: 'Prevent the server from requesting internal or attacker-chosen resources.',
                complete: 'You identified SSRF, explained the server-side request risk, and restricted outbound fetches.'
            }
        });
    }

    function renderBrokenAuthSimulation(container, config, context) {
        renderFamilySimulation(container, config, context, {
            title: 'Broken Authentication Defense',
            validateFix: validateAuthFix,
            fixGuidance: [
                {
                    title: 'Strengthen credentials',
                    body: 'Remove defaults, hash passwords, enforce policy, and require MFA where appropriate.',
                    code: 'await argon2.hash(password);'
                },
                {
                    title: 'Protect sessions',
                    body: 'Rotate sessions after login and use secure, HttpOnly, SameSite cookies.',
                    code: 'req.session.regenerate(() => createSession(user));'
                },
                {
                    title: 'Limit abuse',
                    body: 'Validate tokens, expire reset links, and rate-limit repeated attempts.',
                    code: 'rateLimit({ windowMs: 15 * 60 * 1000, max: 5 });'
                }
            ],
            messages: {
                identifyPrompt: 'Select the line where authentication state, credentials, or tokens are handled unsafely.',
                identifyError: 'Not quite. Select the authentication line that creates the weakness.',
                fixPrompt: 'Harden credentials, sessions, tokens, and repeated authentication attempts.',
                fixGoal: 'Prevent account takeover through authentication weaknesses.',
                complete: 'You identified the authentication flaw, explained the takeover risk, and added authentication defenses.'
            }
        });
    }


    const SimulationRegistry = {
        'sqli-login': renderSqliLoginSimulation,
        'sqli-union': renderSqliUnionSimulation,
        'sqli-blind': renderSqliBlindSimulation,
        'sqli-time': renderSqliTimeSimulation,
        'xss-reflected': renderReflectedXssSimulation,
        'xss-stored': renderStoredXssSimulation,
        'xss-filter-bypass': renderXssFilterBypassSimulation,
        'xss-dom': renderDomXssSimulation,
        'xss-cookie-theft': renderXssCookieTheftSimulation,
        'csrf-form': renderCsrfFormSimulation,
        'csrf-auto-submit': renderCsrfAutoSubmitSimulation,
        'csrf-image': renderCsrfImageSimulation,
        'csrf-ajax': renderCsrfAjaxSimulation,
        'idor-profile': renderIdorProfileSimulation,
        'redirect-basic': renderOpenRedirectSimulation,
        'redirect-phishing': renderOpenRedirectSimulation,
        'redirect-chain': renderOpenRedirectSimulation,
        'command-basic': renderCommandInjectionSimulation,
        'command-pipe': renderCommandInjectionSimulation,
        'command-blind': renderCommandInjectionSimulation,
        'command-filter-bypass': renderCommandInjectionSimulation,
        'upload-shell': renderFileUploadSimulation,
        'upload-mimetype': renderFileUploadSimulation,
        'upload-path-traversal': renderFileUploadSimulation,
        'upload-double-extension': renderFileUploadSimulation,
        'sensitive-error': renderSensitiveDataSimulation,
        'sensitive-file': renderSensitiveDataSimulation,
        'sensitive-asset': renderSensitiveDataSimulation,
        'sensitive-storage': renderSensitiveDataSimulation,
        'sensitive-remediation': renderSensitiveDataSimulation,
        'ssrf-basic': renderSsrfSimulation,
        'ssrf-redirect': renderSsrfSimulation,
        'ssrf-bypass': renderSsrfSimulation,
        'ssrf-webhook': renderSsrfSimulation,
        'auth-default-creds': renderBrokenAuthSimulation,
        'auth-session-fixation': renderBrokenAuthSimulation,
        'auth-jwt-none': renderBrokenAuthSimulation,
        'auth-reset-token': renderBrokenAuthSimulation,
        'auth-rate-limit': renderBrokenAuthSimulation
    };

    Object.assign(BltLabs, {
        SimulationRegistry
    });
}());
