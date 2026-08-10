(function () {
    window.BltLabs = window.BltLabs || {};
    const BltLabs = window.BltLabs;

    function parseJavaScript(code) {
        if (!window.acorn?.parse) {
            return null;
        }

        try {
            return window.acorn.parse(String(code || ''), {
                ecmaVersion: 'latest',
                sourceType: 'script',
                allowReturnOutsideFunction: true,
                allowAwaitOutsideFunction: true
            });
        } catch (_error) {
            return null;
        }
    }

    function walk(node, visit) {
        if (!node || typeof node !== 'object') {
            return;
        }
        visit(node);
        Object.values(node).forEach((value) => {
            if (Array.isArray(value)) {
                value.forEach((child) => walk(child, visit));
            } else if (value?.type) {
                walk(value, visit);
            }
        });
    }

    function memberName(node) {
        if (node?.type !== 'MemberExpression') {
            return null;
        }
        const object = node.object?.type === 'Identifier' ? node.object.name : memberName(node.object);
        const property = node.computed
            ? (node.property?.value ?? null)
            : node.property?.name;
        return object && property ? `${object}.${property}` : null;
    }

    function declarations(ast) {
        const values = new Map();
        walk(ast, (node) => {
            if (node.type === 'VariableDeclarator' && node.id?.type === 'Identifier' && node.init) {
                values.set(node.id.name, node.init);
            }
        });
        return values;
    }

    function resolve(node, values, seen = new Set()) {
        if (node?.type !== 'Identifier' || seen.has(node.name) || !values.has(node.name)) {
            return node;
        }
        seen.add(node.name);
        return resolve(values.get(node.name), values, seen);
    }

    function staticText(node, values) {
        const resolved = resolve(node, values);
        if (resolved?.type === 'Literal' && typeof resolved.value === 'string') {
            return resolved.value;
        }
        if (resolved?.type === 'TemplateLiteral' && resolved.expressions.length === 0) {
            return resolved.quasis.map((part) => part.value.cooked || '').join('');
        }
        return null;
    }

    function isDynamicSql(node, values) {
        const resolved = resolve(node, values);
        if (!resolved) {
            return false;
        }
        if (resolved.type === 'BinaryExpression' && resolved.operator === '+') {
            return true;
        }
        return resolved.type === 'TemplateLiteral' && resolved.expressions.length > 0;
    }

    function calls(ast) {
        const items = [];
        walk(ast, (node) => {
            if (node.type === 'CallExpression' || node.type === 'NewExpression') {
                items.push(node);
            }
        });
        return items;
    }

    function isDatabaseCall(call) {
        const name = memberName(call.callee) || '';
        return /\b(?:db\.)?(query|execute|prepare)$/.test(name);
    }

    function hasPlaceholder(text) {
        return /(\?|:\w+|\$\d+)/.test(text || '');
    }

    function hasBindingCall(call) {
        const name = memberName(call.callee) || '';
        return /\.(setString|setInt|bindValue|bindParam)$/.test(name);
    }

    function callName(call) {
        return memberName(call?.callee) || call?.callee?.name || '';
    }

    function propertyName(node) {
        return node?.key?.name || node?.key?.value || '';
    }

    function hasName(node, pattern) {
        let found = false;
        walk(node, (child) => {
            if (child.type === 'Identifier' && pattern.test(child.name)) {
                found = true;
            }
            if (child.type === 'Literal' && typeof child.value === 'string' &&
                pattern.test(child.value)) {
                found = true;
            }
        });
        return found;
    }

    function astFor(code) {
        const ast = parseJavaScript(code);
        return ast ? { ast, allCalls: calls(ast) } : null;
    }

    function analyzeXssFix(code) {
        const parsed = astFor(code);
        if (!parsed) {
            return null;
        }

        let unsafe = false;
        let safe = false;
        let encoded = false;
        walk(parsed.ast, (node) => {
            if (node.type === 'AssignmentExpression') {
                const property = memberName(node.left)?.split('.').pop();
                unsafe ||= ['innerHTML', 'outerHTML'].includes(property);
                safe ||= ['textContent', 'innerText'].includes(property);
            }
        });
        parsed.allCalls.forEach((call) => {
            const name = callName(call);
            unsafe ||= /(?:insertAdjacentHTML|document\.write)$/.test(name);
            safe ||= /(?:createTextNode)$/.test(name);
            encoded ||= /(?:escapeHTML|encodeHTML|sanitize)$/.test(name);
        });
        return { plausible: unsafe || safe || encoded, unsafe, safe, encoded };
    }

    function analyzeCsrfFix(code) {
        const parsed = astFor(code);
        if (!parsed) {
            return null;
        }

        const validationCalls = parsed.allCalls.filter((call) => {
            return /(?:validate|verify|check|compare).*csrf|csrf.*(?:validate|verify|check|compare)/i
                .test(callName(call));
        });
        const stateCalls = parsed.allCalls.filter((call) => {
            return /(?:update|delete|transfer|change|reset|create|save)/i.test(callName(call));
        });
        let sameSite = false;
        walk(parsed.ast, (node) => {
            if (node.type === 'Property' && /sameSite/i.test(propertyName(node)) &&
                /^(strict|lax)$/i.test(String(node.value?.value || ''))) {
                sameSite = true;
            }
        });

        const firstValidation = Math.min(...validationCalls.map((call) => call.start));
        const firstStateChange = Math.min(...stateCalls.map((call) => call.start));
        return {
            includesToken: hasName(parsed.ast, /csrf[_-]?token/i),
            validates: validationCalls.length > 0,
            beforeStateChange: validationCalls.length > 0 &&
                (stateCalls.length === 0 || firstValidation < firstStateChange),
            sameSite
        };
    }

    function analyzeIdorFix(code) {
        const parsed = astFor(code);
        if (!parsed) {
            return null;
        }

        const responseCalls = parsed.allCalls.filter((call) => {
            return /(?:res|response)\.(?:json|send|render)$/.test(callName(call));
        });
        const ownershipChecks = [];
        walk(parsed.ast, (node) => {
            if (node.type === 'IfStatement' &&
                hasName(node.test, /owner|userId|authorize|access/i)) {
                ownershipChecks.push(node);
            }
        });
        const responseStart = Math.min(...responseCalls.map((call) => call.start));
        const checkBeforeResponse = ownershipChecks.some((node) => {
            return responseCalls.length === 0 || node.start < responseStart;
        });
        const rejected = ownershipChecks.some((node) => {
            return hasName(node.consequent, /Forbidden|Unauthorized/) ||
                parsed.allCalls.some((call) => {
                    return call.start >= node.consequent.start && call.end <= node.consequent.end &&
                        /status$/.test(callName(call)) &&
                        call.arguments.some((arg) => arg.value === 401 || arg.value === 403);
                });
        });
        return {
            userIdentity: hasName(parsed.ast, /^(req|request|currentUser|authenticatedUser)$/) &&
                /\.(?:user|session)\.(?:id|userId)\b/.test(String(code)),
            checkBeforeResponse,
            rejected
        };
    }

    function analyzeRedirectFix(code) {
        const parsed = astFor(code);
        if (!parsed) {
            return null;
        }

        const redirectCalls = parsed.allCalls.filter((call) => {
            return /(?:res|response)\.redirect$|^redirect$/.test(callName(call));
        });
        return {
            plausible: redirectCalls.length > 0,
            allowlist: hasName(parsed.ast, /allowed|allowlist|whitelist/i),
            parsedUrl: parsed.allCalls.some((call) => callName(call) === 'URL'),
            dangerousBlocked: hasName(parsed.ast, /javascript:|data:|protocol|hostname|origin|pathname|isSafeRedirect/i),
            rawInput: redirectCalls.some((call) => {
                return /^(req|request)\.(query|body|params)\./
                    .test(memberName(call.arguments[0]) || '');
            })
        };
    }

    function analyzeCommandFix(code) {
        const parsed = astFor(code);
        if (!parsed) {
            return null;
        }

        const values = declarations(parsed.ast);
        const commandCalls = parsed.allCalls.filter((call) => {
            return /(?:exec|execSync|system|popen|shell_exec|passthru|spawn|execFile)$/
                .test(callName(call));
        });
        let shellDisabled = false;
        walk(parsed.ast, (node) => {
            if (node.type === 'Property' && propertyName(node) === 'shell' &&
                node.value?.value === false) {
                shellDisabled = true;
            }
        });
        return {
            plausible: commandCalls.length > 0,
            dynamicShell: commandCalls.some((call) => isDynamicSql(call.arguments[0], values)),
            safeApi: commandCalls.some((call) => {
                return /(?:spawn|execFile)$/.test(callName(call)) &&
                    resolve(call.arguments[1], values)?.type === 'ArrayExpression';
            }),
            validated: parsed.allCalls.some((call) => /(?:isIP|match|test|includes)$/.test(callName(call))) ||
                hasName(parsed.ast, /allowlist|allowedCommands|commandMap/i),
            shellDisabled
        };
    }

    function analyzeUploadFix(code) {
        const parsed = astFor(code);
        if (!parsed) {
            return null;
        }

        return {
            fileType: hasName(parsed.ast, /allowedExtensions|allowedMimeTypes|allowedTypes|mime|magic|extension/i),
            content: parsed.allCalls.some((call) => /(?:fileTypeFromBuffer|detectMime|scan)/i.test(callName(call))) ||
                hasName(parsed.ast, /magic|signature|virus|malware/i),
            safeStore: hasName(parsed.ast, /privateUploads|storagePath|randomUUID|uuid|basename|normalize/i),
            traversal: hasName(parsed.ast, /basename|normalize|safeJoin|traversal/) ||
                hasName(parsed.ast, /\.\./)
        };
    }

    function analyzeSensitiveDataFix(code) {
        const parsed = astFor(code);
        if (!parsed) {
            return null;
        }

        const names = (pattern) => hasName(parsed.ast, pattern);
        const hasLogging = parsed.allCalls.some((call) => /(?:logger|console)\./.test(callName(call)));
        return {
            plausible: names(/password|secret|token|key|error|log|env|vault|kms|hash|encrypt|auth|redact|sanitize|mask/i),
            removesOutput: names(/redact|sanitize|mask|safeError/i),
            secretManager: names(/secretManager|vault|kms|env|getSecret|secretsManager/i),
            protectedStorage: names(/encrypt|hash|bcrypt|argon2|scrypt|private|deny|auth|authorization/i),
            safeLogging: !hasLogging || names(/redact|mask|sanitize/i)
        };
    }

    function analyzeSsrfFix(code) {
        const parsed = astFor(code);
        if (!parsed) {
            return null;
        }

        const fetchCalls = parsed.allCalls.filter((call) => /(?:fetch|request|get|axios)$/.test(callName(call)));
        let redirectsDisabled = false;
        walk(parsed.ast, (node) => {
            const redirectSetting = /maxRedirects|followRedirects|redirect/.test(propertyName(node));
            const disabled = node.value?.value === 0 || node.value?.value === false ||
                node.value?.value === 'manual';
            if (node.type === 'Property' && redirectSetting && disabled) {
                redirectsDisabled = true;
            }
        });
        return {
            plausible: fetchCalls.length > 0 || parsed.allCalls.some((call) => callName(call) === 'URL'),
            outboundValidated: hasName(parsed.ast, /allowedHosts|allowlist|whitelist/i) &&
                parsed.allCalls.some((call) => callName(call) === 'URL'),
            blocksInternal: hasName(parsed.ast, /169\.254\.169\.254|127\.0\.0\.1|localhost|privateIp|internalIp|isPrivate/i),
            redirectsDisabled,
            rawFetch: fetchCalls.some((call) => {
                return /^(req|request)\.(query|body|params)\./
                    .test(memberName(call.arguments[0]) || '');
            })
        };
    }

    function analyzeAuthFix(code) {
        const parsed = astFor(code);
        if (!parsed) {
            return null;
        }

        const names = (pattern) => hasName(parsed.ast, pattern);
        return {
            credentials: names(/forcePasswordChange|passwordPolicy|bcrypt|argon2|mfa|multiFactor|default.*disabled/i),
            sessions: names(/regenerate|rotateSession|httpOnly|secure|sameSite/i),
            tokens: names(/jwt|validateSignature|algorithms|expiresIn|singleUse|random/i),
            limits: names(/rateLimit|lockout|throttle|attempts|progressiveDelay|singleUse|expires/i)
        };
    }

    function analyzeSqliFix(code, config = {}) {
        const ast = parseJavaScript(code);
        if (!ast) {
            return null;
        }

        const values = declarations(ast);
        const allCalls = calls(ast);
        const databaseCalls = allCalls.filter(isDatabaseCall);
        const queryCalls = databaseCalls.filter((call) => /\b(query|execute)$/.test(memberName(call.callee) || ''));
        const texts = databaseCalls.map((call) => staticText(call.arguments[0], values));
        const sqlCalls = databaseCalls.filter((call, index) => /\b(select|insert|update|delete)\b/i.test(texts[index] || '') || isDynamicSql(call.arguments[0], values));
        const requiredInputs = Array.isArray(config.vulnerable_parameters) && config.vulnerable_parameters.length
            ? config.vulnerable_parameters
            : ['username', 'password'];
        const sourceText = String(code || '').replace(/[_-]/g, '').toLowerCase();
        const hasExpectedInputs = requiredInputs.every((name) => sourceText.includes(String(name).replace(/[_-]/g, '').toLowerCase()));
        const parameterized = databaseCalls.some((call, index) => hasPlaceholder(texts[index]));
        const separatelyBound = queryCalls.some((call) => call.arguments.length >= 2 && resolve(call.arguments[1], values)?.type === 'ArrayExpression') || allCalls.some(hasBindingCall);
        const dynamicSql = sqlCalls.some((call) => isDynamicSql(call.arguments[0], values));

        return {
            plausible: databaseCalls.length > 0 && sqlCalls.length > 0 && hasExpectedInputs,
            noConcatenation: !dynamicSql,
            parameterized,
            separatelyBound,
            bypassBlocked: parameterized && separatelyBound && !dynamicSql
        };
    }

    Object.assign(BltLabs, {
        analyzeAuthFix,
        analyzeCommandFix,
        analyzeCsrfFix,
        analyzeIdorFix,
        analyzeRedirectFix,
        analyzeSensitiveDataFix,
        analyzeSqliFix,
        analyzeSsrfFix,
        analyzeUploadFix,
        analyzeXssFix,
        parseJavaScript
    });
}());
