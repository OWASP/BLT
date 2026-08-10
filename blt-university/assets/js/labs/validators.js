(function () {
    window.BltLabs = window.BltLabs || {};
    const BltLabs = window.BltLabs;
    const {
        analyzeAuthFix,
        analyzeCommandFix,
        analyzeCsrfFix,
        analyzeIdorFix,
        analyzeRedirectFix,
        analyzeSensitiveDataFix,
        analyzeSqliFix,
        analyzeSsrfFix,
        analyzeUploadFix,
        analyzeXssFix
    } = BltLabs;


    // Identify and explain step validation.
    function normalizeLines(lines = []) {
        return lines.map(Number).filter(Number.isFinite).sort((a, b) => a - b);
    }

    function validateLineSelection(selectedLines, expectedLines) {
        const selected = normalizeLines(selectedLines);
        const expected = normalizeLines(expectedLines);

        return selected.length === expected.length && selected.every((line, index) => line === expected[index]);
    }

    function validateExplainAnswer(selectedAnswer, expectedAnswer) {
        const selected = String(selectedAnswer ?? '').trim();
        const expected = String(expectedAnswer ?? '').trim();

        return Boolean(selected) && Boolean(expected) && selected === expected;
    }

    // SQL injection validation helpers.
    function hasParameterizedQuery(code) {
        return /(\?|:\w+|\$\d+)/.test(code) && /\b(execute|query|prepare|preparedstatement)\b/i.test(code);
    }

    function hasSeparateParameterBinding(code) {
        return /\[[^\]]+\]/i.test(code) ||
            /\.(setString|setInt|bindValue|bindParam)\s*\(/i.test(code);
    }

    function splitJavaScriptStatements(code) {
        const statements = [];
        let current = '';
        let quote = null;
        let escaped = false;

        String(code || '').split('').forEach(character => {
            current += character;

            if (escaped) {
                escaped = false;
                return;
            }

            if (character === '\\') {
                escaped = true;
                return;
            }

            if (quote) {
                if (character === quote) {
                    quote = null;
                }
                return;
            }

            if (character === '\'' || character === '"' || character === '`') {
                quote = character;
                return;
            }

            if (character === ';') {
                statements.push(current);
                current = '';
            }
        });

        if (current.trim()) {
            statements.push(current);
        }

        return statements;
    }

    function hasUnquotedPlus(statement) {
        let quote = null;
        let escaped = false;

        return String(statement || '').split('').some(character => {
            if (escaped) {
                escaped = false;
                return false;
            }

            if (character === '\\') {
                escaped = true;
                return false;
            }

            if (quote) {
                if (character === quote) {
                    quote = null;
                }
                return false;
            }

            if (character === '\'' || character === '"' || character === '`') {
                quote = character;
                return false;
            }

            return character === '+';
        });
    }

    function escapeRegex(value) {
        return String(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    function hasSqlConcatenation(code) {
        const statements = splitJavaScriptStatements(code);
        const sqlVariables = new Set();

        statements.forEach(statement => {
            if (!/\b(select|insert|update|delete)\b/i.test(statement)) {
                return;
            }

            const assignment = statement.match(/\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=/);
            if (assignment) {
                sqlVariables.add(assignment[1]);
            }
        });

        return statements.some(statement => {
            const containsSqlVerb = /\b(select|insert|update|delete)\b/i.test(statement);
            const referencesSqlVariable = [...sqlVariables].some(name => new RegExp(`\\b${escapeRegex(name)}\\b`).test(statement));
            const usesDynamicInput = hasUnquotedPlus(statement) || /\$\{[^}]+}/.test(statement);

            return (containsSqlVerb || referencesSqlVariable) && usesDynamicInput;
        });
    }

    function loginBypassStillWorks(code, payloads = []) {
        if (!hasSqlConcatenation(code)) {
            return false;
        }

        return payloads.some(payload => /or\s+['"]?1['"]?\s*=\s*['"]?1/i.test(payload));
    }

    function hasSqlQuery(code) {
        return /\bselect\b[\s\S]*\bfrom\b[\s\S]*\bwhere\b/i.test(code);
    }

    function hasDbExecution(code) {
        return /\bdb\s*\.\s*(query|execute|prepare)\s*\(/i.test(code) ||
            /\b(preparedstatement|prepare)\b/i.test(code);
    }

    function toCamelCase(value) {
        return String(value).replace(/[_-]([a-z])/gi, (_match, character) => character.toUpperCase());
    }

    function inputNamePattern(inputName) {
        const variants = [
            inputName,
            toCamelCase(inputName),
            String(inputName).replace(/[_-]/g, '')
        ].filter(Boolean);
        return new RegExp(`\\b(?:${variants.map(escapeRegex).join('|')})\\b`, 'i');
    }

    function hasRequiredSqlInputs(code, config = {}) {
        const requiredInputs = Array.isArray(config.vulnerable_parameters) && config.vulnerable_parameters.length
            ? config.vulnerable_parameters
            : ['username', 'password'];

        return requiredInputs.every(inputName => inputNamePattern(inputName).test(code));
    }

    function isPlausibleSqliFix(code, config = {}) {
        return hasSqlQuery(code) && hasDbExecution(code) && hasRequiredSqlInputs(code, config);
    }

    function validateSqliFix(code, config = {}) {
        const astResult = analyzeSqliFix?.(code, config);
        const plausibleFix = astResult?.plausible ?? isPlausibleSqliFix(code, config);
        const noConcatenation = plausibleFix &&
            (astResult?.noConcatenation ?? !hasSqlConcatenation(code));
        const parameterized = plausibleFix &&
            (astResult?.parameterized ?? hasParameterizedQuery(code));
        const separateBinding = plausibleFix &&
            (astResult?.separatelyBound ?? hasSeparateParameterBinding(code));
        const bypassBlocked = plausibleFix && (astResult?.bypassBlocked ?? (
            parameterized && separateBinding && !loginBypassStillWorks(code, config.attack_payloads || [])
        ));

        const checks = [
            {
                label: 'A SQL query using the expected input is present',
                passed: plausibleFix
            },
            {
                label: 'User input is not concatenated into the SQL string',
                passed: noConcatenation
            },
            {
                label: 'Parameterized query or prepared statement detected',
                passed: parameterized
            },
            {
                label: 'User values are passed separately from the SQL string',
                passed: separateBinding
            },
            {
                label: 'Login bypass payload no longer changes query behavior',
                passed: bypassBlocked
            }
        ];

        return {
            passed: checks.every(check => check.passed),
            checks
        };
    }

    // XSS validation helpers.
    function usesUnsafeHtmlSink(code) {
        return /\.(innerHTML|outerHTML)\s*=|insertAdjacentHTML\s*\(|document\.write\s*\(/i.test(code);
    }

    function usesSafeTextSink(code) {
        return /\.(textContent|innerText)\s*=|createTextNode\s*\(/i.test(code);
    }

    function encodesHtml(code) {
        return /escapeHTML|encodeHTML|sanitize|DOMPurify|replace\s*\(\s*\/\[&<>"'\]/i.test(code) ||
            (/replace\s*\([^)]*&/i.test(code) && /replace\s*\([^)]*</i.test(code));
    }

    function xssPayloadStillExecutes(code, payloads = []) {
        const hasExecutablePayload = payloads.some(payload => /<script|onerror|onload|javascript:/i.test(payload));
        return hasExecutablePayload && usesUnsafeHtmlSink(code) && !encodesHtml(code);
    }

    function validateXssFix(code, config = {}) {
        const astResult = analyzeXssFix?.(code);
        const plausibleFix = astResult?.plausible ??
            (usesUnsafeHtmlSink(code) || usesSafeTextSink(code) || encodesHtml(code));
        const unsafeSink = astResult?.unsafe ?? usesUnsafeHtmlSink(code);
        const safeSink = astResult?.safe ?? usesSafeTextSink(code);
        const encoded = astResult?.encoded ?? encodesHtml(code);
        const executablePayload = (config.attack_payloads || []).some((payload) => {
            return /<script|onerror|onload|javascript:/i.test(payload);
        });

        const checks = [
            {
                label: 'Untrusted input is not written with innerHTML or document.write',
                passed: plausibleFix && (!unsafeSink || encoded)
            },
            {
                label: 'Output uses a safe text sink or explicit HTML encoding',
                passed: plausibleFix && (safeSink || encoded)
            },
            {
                label: 'Script payload is rendered as text instead of executing',
                passed: plausibleFix && (!executablePayload || safeSink || encoded)
            }
        ];

        return {
            passed: checks.every(check => check.passed),
            checks
        };
    }

    // CSRF validation helpers.
    // Shared by the presence check and the ordering check below so the two can never drift
    // apart. Carries no /g flag, so reusing one object across .test() and .search() is safe.
    const CSRF_VALIDATION_PATTERN = /(validate|verify|check|compare)[\s\S]{0,40}csrf[_-]?token|csrf[_-]?token[\s\S]{0,40}(validate|verify|check|compare)/i;

    function includesCsrfToken(code) {
        return /csrf[_-]?token/i.test(code);
    }

    function validatesCsrfToken(code) {
        return CSRF_VALIDATION_PATTERN.test(code);
    }

    function verifiesCsrfBeforeStateChange(code) {
        const validationIndex = code.search(CSRF_VALIDATION_PATTERN);
        const stateChangeIndex = code.search(/\b(update|delete|transfer|change|reset|create|save)[A-Za-z0-9_$]*\s*\(|\.\s*(perform|run|apply|execute)?(Update|Delete|Transfer|Change|Reset|Create|Save)[A-Za-z0-9_$]*\s*\(/i);

        // Deliberately lenient: with no recognizable state-changing call to order against,
        // token presence alone passes rather than failing a learner for a naming style the
        // pattern above does not cover.
        if (stateChangeIndex === -1) {
            return validationIndex !== -1;
        }

        return validationIndex !== -1 && validationIndex < stateChangeIndex;
    }

    function usesSameSiteCookie(code) {
        return /SameSite\s*=\s*(Strict|Lax)/i.test(code) ||
            /sameSite\s*:\s*['"]?(strict|lax)['"]?/i.test(code);
    }

    function validateCsrfFix(code) {
        const astResult = analyzeCsrfFix?.(code);
        const plausibleFix = astResult ?
            (astResult.includesToken || astResult.validates || astResult.sameSite) : true;
        const checks = [
            {
                label: 'State-changing form includes a CSRF token',
                passed: plausibleFix && includesCsrfToken(code)
            },
            {
                label: 'Server verifies the submitted CSRF token before updating data',
                passed: plausibleFix && validatesCsrfToken(code)
            },
            {
                label: 'CSRF token is verified before any state-changing action',
                passed: plausibleFix && verifiesCsrfBeforeStateChange(code)
            },
            {
                label: 'Session cookie is hardened with SameSite protection',
                passed: plausibleFix && usesSameSiteCookie(code)
            }
        ];

        return {
            passed: checks.every(check => check.passed),
            checks
        };
    }

    // IDOR validation helpers.
    function usesAuthenticatedIdentity(code) {
        return /\b(req|request)\.(user|session)\.(id|userId)\b/i.test(code) ||
            /\b(currentUser|authenticatedUser)\.(id|userId)\b/i.test(code);
    }

    function findFirstIndex(code, patterns) {
        return patterns.reduce((firstIndex, pattern) => {
            const index = code.search(pattern);
            if (index === -1) {
                return firstIndex;
            }

            return firstIndex === -1 ? index : Math.min(firstIndex, index);
        }, -1);
    }

    function dataResponseIndex(code) {
        return code.search(/\b(res|response)\.(json|send|render)\s*\(\s*(profile|record|resource|account)\b/i);
    }

    function authorizationCheckIndex(code) {
        return findFirstIndex(code, [
            /(profile|record|resource|account)\.(userId|ownerId|id)\s*[!=]==?\s*(req|request)\.(user|session)\.(id|userId)/i,
            /(req|request)\.(user|session)\.(id|userId)\s*[!=]==?\s*(profile|record|resource|account)\.(userId|ownerId|id)/i,
            /\b(if\s*\([^)]*\b(authorize|isAuthorized|canAccess|canView|requireOwner|requireOwnership)\s*\(|requireOwner|requireOwnership)\b/i
        ]);
    }

    function checksResourceOwnershipBeforeReturn(code) {
        const checkIndex = authorizationCheckIndex(code);
        const responseIndex = dataResponseIndex(code);

        // The responseIndex === -1 branch accepts submissions that never return the resource
        // inline: ordering cannot be judged when there is nothing to order against, so an
        // ownership check anywhere is enough.
        return checkIndex !== -1 && (responseIndex === -1 || checkIndex < responseIndex);
    }

    function rejectsUnauthorizedAccessBeforeReturn(code) {
        const rejectionIndex = findFirstIndex(code, [
            /if\s*\([^)]*(profile|record|resource|account|authorize|isAuthorized|canAccess|canView|requireOwner|requireOwnership)[^)]*\)\s*\{?[\s\S]{0,220}\b(return\s+)?(res|response)\.status\s*\(\s*(401|403)\s*\)/i,
            /if\s*\([^)]*(profile|record|resource|account|authorize|isAuthorized|canAccess|canView|requireOwner|requireOwnership)[^)]*\)\s*\{?[\s\S]{0,220}\bthrow\s+new\s+(Forbidden|Unauthorized|Auth)/i
        ]);
        const responseIndex = dataResponseIndex(code);

        // Same leniency as above: a submission that never returns the resource inline passes
        // on the presence of a rejection path alone.
        return rejectionIndex !== -1 && (responseIndex === -1 || rejectionIndex < responseIndex);
    }

    function returnsResourceBeforeAuthorization(code) {
        const responseIndex = dataResponseIndex(code);
        if (responseIndex === -1) {
            return false;
        }

        const checkIndex = authorizationCheckIndex(code);
        return checkIndex === -1 || responseIndex < checkIndex;
    }

    function validateIdorFix(code) {
        const astResult = analyzeIdorFix?.(code);
        const plausibleFix = astResult ?
            (astResult.userIdentity || astResult.checkBeforeResponse || astResult.rejected) : true;
        const checks = [
            {
                label: 'Authenticated user identity is used for the access decision',
                passed: plausibleFix && usesAuthenticatedIdentity(code)
            },
            {
                label: 'Resource ownership or authorization is checked before returning data',
                passed: plausibleFix && checksResourceOwnershipBeforeReturn(code) && !returnsResourceBeforeAuthorization(code)
            },
            {
                label: 'Unauthorized object access is rejected',
                passed: plausibleFix && rejectsUnauthorizedAccessBeforeReturn(code)
            }
        ];

        return {
            passed: checks.every(check => check.passed),
            checks
        };
    }

    // Open redirect validation helpers. usesAllowlist is also reused by the SSRF group below.
    function usesAllowlist(code) {
        return /\ballowed(?:Hosts|Domains|Paths|Redirects|Origins)?\b|allowlist|whitelist/i.test(code);
    }

    function validatesUrl(code) {
        return /new\s+URL\s*\(|urlparse\s*\(|parseUrl\s*\(|URL\.canParse|startsWith\s*\(\s*['"]\//i.test(code);
    }

    function blocksDangerousRedirects(code) {
        return /javascript:|data:|\/\/|protocol|hostname|origin|pathname|isSafeRedirect/i.test(code);
    }

    function redirectsRawUserInput(code) {
        return /redirect\s*\(\s*(req|request)\.(query|body|params)\.[A-Za-z_$][\w$]*\s*\)/i.test(code);
    }

    function isPlausibleRedirectFix(code) {
        return /\b(res|response)\.redirect\s*\(|\bredirect\s*\(/i.test(code);
    }

    function validateRedirectFix(code) {
        const astResult = analyzeRedirectFix?.(code);
        const plausibleFix = isPlausibleRedirectFix(code) &&
            (astResult?.plausible ?? true);

        const checks = [
            {
                label: 'Redirect target is checked against an allowlist or internal path list',
                passed: plausibleFix && usesAllowlist(code)
            },
            {
                label: 'Redirect URL is parsed or normalized before use',
                passed: plausibleFix && validatesUrl(code)
            },
            {
                label: 'Dangerous external schemes or protocol-relative URLs are blocked',
                passed: plausibleFix && blocksDangerousRedirects(code)
            },
            {
                label: 'Raw user-controlled redirect values are not passed directly to redirect',
                passed: plausibleFix && !redirectsRawUserInput(code)
            }
        ];

        return {
            passed: checks.every(check => check.passed),
            checks
        };
    }

    // Command injection validation helpers.
    function invokesShellWithUserInput(code) {
        return /\b(exec|execSync|system|popen|shell_exec|passthru)\s*\([^)]*(req|request|input|ip|host|cmd|target)[^)]*\)/i.test(code) ||
            /\b(spawn|execFile)\s*\([^)]*\+\s*(req|request|input|ip|host|cmd|target)/i.test(code);
    }

    function usesSafeCommandApi(code) {
        return /\b(execFile|spawn)\s*\([^,]+,\s*\[[^\]]+\]/i.test(code) ||
            /subprocess\.run\s*\([^)]*shell\s*=\s*False/i.test(code);
    }

    function validatesCommandInput(code) {
        return /net\.isIP|ipaddr|isValidIp|allowedCommands|commandMap|allowlist|allowed|match\s*\(|test\s*\(/i.test(code);
    }

    function blocksShellMetacharacters(code) {
        return /\bshell\s*:\s*false|shell\s*=\s*False/i.test(code) ||
            /\/\[[^\]]*[;&|`$<>][^\]]*\]\/\s*\.\s*(test|exec)\s*\(\s*(input|ip|host|cmd|target|req|request)/i.test(code) ||
            /\b(reject|block|deny|throw)[\s\S]{0,80}\b(shell\s*)?metacharacter/i.test(code);
    }

    function isPlausibleCommandFix(code) {
        return /\b(execFile|spawn|subprocess\.run|exec|execSync|system|popen|shell_exec|passthru)\s*\(/i.test(code);
    }

    function validateCommandFix(code) {
        const astResult = analyzeCommandFix?.(code);
        const plausibleFix = isPlausibleCommandFix(code) &&
            (astResult?.plausible ?? true);

        const checks = [
            {
                label: 'User input is not concatenated into a shell command',
                passed: plausibleFix && !invokesShellWithUserInput(code)
            },
            {
                label: 'Safe command APIs pass arguments separately',
                passed: plausibleFix && usesSafeCommandApi(code)
            },
            {
                label: 'Input is validated against an allowlist or strict pattern',
                passed: plausibleFix && validatesCommandInput(code)
            },
            {
                label: 'Shell metacharacters are blocked or the shell is disabled',
                passed: plausibleFix && blocksShellMetacharacters(code)
            }
        ];

        return {
            passed: checks.every(check => check.passed),
            checks
        };
    }

    // File upload validation helpers.
    function restrictsFileType(code) {
        return /allowed(?:Extensions|MimeTypes|Types)|\.includes\s*\(|mime|magic|file-type|extension/i.test(code);
    }

    function checksFileContent(code) {
        return /magic|signature|fileTypeFromBuffer|detectMime|scan|virus|malware/i.test(code);
    }

    function storesSafely(code) {
        return /outside.*web.?root|privateUploads|storagePath|randomUUID|uuid|basename|path\.join|normalize/i.test(code);
    }

    function preventsTraversal(code) {
        return /\.\.|path\.normalize|basename|safeJoin|startsWith\s*\(|reject.*traversal/i.test(code);
    }

    function validateUploadFix(code) {
        const astResult = analyzeUploadFix?.(code);
        const plausibleFix = astResult ?
            (astResult.fileType || astResult.content || astResult.safeStore || astResult.traversal) : true;
        const checks = [
            {
                label: 'Uploaded files are restricted to allowed types',
                passed: plausibleFix && restrictsFileType(code)
            },
            {
                label: 'File content or magic bytes are verified',
                passed: plausibleFix && checksFileContent(code)
            },
            {
                label: 'Files are renamed or stored outside the web root',
                passed: plausibleFix && storesSafely(code)
            },
            {
                label: 'Path traversal through filenames is prevented',
                passed: plausibleFix && preventsTraversal(code)
            }
        ];

        return {
            passed: checks.every(check => check.passed),
            checks
        };
    }

    // Sensitive data exposure validation helpers.
    function removesSensitiveOutput(code) {
        return /redact|sanitize|mask|safeError|generic.*error|delete\s+.*(password|secret|token|key)/i.test(code);
    }

    function usesSecretManager(code) {
        return /secretManager|vault|kms|process\.env|env\.|getSecret|secretsManager/i.test(code);
    }

    function protectsSensitiveStorage(code) {
        return /encrypt|hash|bcrypt|argon2|scrypt|private|deny|auth|authorization/i.test(code);
    }

    function avoidsSecretLogging(code) {
        // Inverted default on purpose: redaction is only required of submissions that log at
        // all, so code with no logging has nothing to leak and passes trivially.
        return /logger|console|log/i.test(code) ? /redact|mask|sanitize/i.test(code) : true;
    }

    function isPlausibleSensitiveDataFix(code) {
        return /(password|secret|token|key|error|log|logger|console|env|vault|kms|hash|encrypt|auth|redact|sanitize|mask)/i.test(code);
    }

    function validateSensitiveDataFix(code) {
        const astResult = analyzeSensitiveDataFix?.(code);
        const plausibleFix = isPlausibleSensitiveDataFix(code) &&
            (astResult?.plausible ?? true);

        const checks = [
            {
                label: 'Secrets and sensitive fields are removed or redacted from output',
                passed: plausibleFix && removesSensitiveOutput(code)
            },
            {
                label: 'Secrets are loaded from managed configuration instead of public files',
                passed: plausibleFix && usesSecretManager(code)
            },
            {
                label: 'Sensitive data is encrypted, hashed, or access-controlled',
                passed: plausibleFix && protectsSensitiveStorage(code)
            },
            {
                label: 'Logs and errors avoid exposing raw secrets',
                passed: plausibleFix && avoidsSecretLogging(code)
            }
        ];

        return {
            passed: checks.every(check => check.passed),
            checks
        };
    }

    // SSRF validation helpers.
    function validatesOutboundUrl(code) {
        return /new\s+URL\s*\(|urlparse\s*\(|parseUrl\s*\(/i.test(code) && usesAllowlist(code);
    }

    function blocksInternalNetworks(code) {
        return /169\.254\.169\.254|127\.0\.0\.1|localhost|10\.0\.0\.0|172\.16|192\.168|privateIp|internalIp|isPrivate/i.test(code);
    }

    function restrictsRedirectFollowing(code) {
        return /maxRedirects\s*:\s*0|followRedirects\s*:\s*false|redirect\s*:\s*['"]manual|disable.*redirect/i.test(code);
    }

    function avoidsArbitraryServerFetch(code) {
        return !/\b(fetch|request|get)\s*\(\s*(req|request)\.(query|body|params)\.[A-Za-z_$][\w$]*/i.test(code);
    }

    function isPlausibleSsrfFix(code) {
        return /\b(fetch|request|get|axios)\s*\(|new\s+URL\s*\(|urlparse\s*\(|parseUrl\s*\(/i.test(code);
    }

    function validateSsrfFix(code) {
        const astResult = analyzeSsrfFix?.(code);
        const plausibleFix = isPlausibleSsrfFix(code) &&
            (astResult?.plausible ?? true);

        const checks = [
            {
                label: 'Outbound URLs are parsed and checked against trusted hosts',
                passed: plausibleFix && validatesOutboundUrl(code)
            },
            {
                label: 'Internal, loopback, and metadata IP ranges are blocked',
                passed: plausibleFix && blocksInternalNetworks(code)
            },
            {
                label: 'Redirect following is disabled or restricted',
                passed: plausibleFix && restrictsRedirectFollowing(code)
            },
            {
                label: 'The server does not fetch arbitrary user-controlled URLs',
                passed: plausibleFix && avoidsArbitraryServerFetch(code)
            }
        ];

        return {
            passed: checks.every(check => check.passed),
            checks
        };
    }

    // Broken authentication validation helpers.
    function strengthensCredentials(code) {
        return /forcePasswordChange|passwordPolicy|bcrypt|argon2|mfa|multiFactor|default.*disabled/i.test(code);
    }

    function protectsSessions(code) {
        return /regenerate|rotateSession|session\.regenerate|httpOnly|secure\s*:\s*true|sameSite/i.test(code);
    }

    function validatesTokens(code) {
        return /jwt\.verify|validateSignature|algorithms|reject.*none|expiresIn|singleUse|crypto\.random/i.test(code);
    }

    function limitsAuthAbuse(code) {
        return /rateLimit|lockout|throttle|attempts|progressiveDelay|singleUse|expires/i.test(code);
    }

    function validateAuthFix(code) {
        const astResult = analyzeAuthFix?.(code);
        const plausibleFix = astResult ?
            (astResult.credentials || astResult.sessions || astResult.tokens || astResult.limits) : true;
        const checks = [
            {
                label: 'Credentials or reset secrets are strengthened',
                passed: plausibleFix && strengthensCredentials(code)
            },
            {
                label: 'Sessions are rotated or cookies are hardened',
                passed: plausibleFix && protectsSessions(code)
            },
            {
                label: 'JWTs or reset tokens are validated safely',
                passed: plausibleFix && validatesTokens(code)
            },
            {
                label: 'Authentication abuse is limited with rate limits, expiry, or lockouts',
                passed: plausibleFix && limitsAuthAbuse(code)
            }
        ];

        return {
            passed: checks.every(check => check.passed),
            checks
        };
    }

    Object.assign(BltLabs, {
        validateAuthFix,
        validateCommandFix,
        validateCsrfFix,
        validateExplainAnswer,
        validateIdorFix,
        validateLineSelection,
        validateRedirectFix,
        validateSensitiveDataFix,
        validateSqliFix,
        validateSsrfFix,
        validateUploadFix,
        validateXssFix
    });
}());
