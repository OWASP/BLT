#!/usr/bin/env node

/**
 * Test script to verify data display functionality
 * This tests both API endpoints and HTML structure
 */

const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

// ANSI color codes for output
const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
};

let testsPassed = 0;
let testsFailed = 0;

function log(message, color = colors.reset) {
  console.log(`${color}${message}${colors.reset}`);
}

function testResult(testName, passed, message = '') {
  if (passed) {
    testsPassed++;
    log(`✓ ${testName}`, colors.green);
    if (message) log(`  ${message}`, colors.blue);
  } else {
    testsFailed++;
    log(`✗ ${testName}`, colors.red);
    if (message) log(`  ${message}`, colors.red);
  }
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function getSetCookieHeader(response) {
  if (response?.headers?.getSetCookie) {
    return response.headers.getSetCookie().join('\n');
  }
  return response?.headers?.get('set-cookie') || '';
}

async function waitForEndpoint(url, timeoutMs = 25000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const resp = await fetch(url, { redirect: 'manual' });
      if (resp && resp.status) {
        return true;
      }
    } catch (_) {
      // keep waiting for wrangler dev to become ready
    }
    await sleep(500);
  }
  return false;
}

async function startRuntimeServer() {
  const port = 8788;
  const baseUrl = `http://127.0.0.1:${port}`;
  const cmd = process.platform === 'win32' ? 'npx.cmd' : 'npx';
  const args = ['wrangler', 'dev', '--local', '--ip', '127.0.0.1', '--port', String(port), '--log-level', 'error'];

  const child = spawn(cmd, args, {
    cwd: __dirname,
    env: { ...process.env, BROWSER: 'none' },
    stdio: ['ignore', 'pipe', 'pipe'],
  });

  let output = '';
  child.stdout.on('data', (chunk) => {
    output += chunk.toString();
  });
  child.stderr.on('data', (chunk) => {
    output += chunk.toString();
  });

  const ready = await waitForEndpoint(`${baseUrl}/api/auth/user`);
  if (!ready) {
    child.kill('SIGTERM');
    throw new Error(`wrangler dev did not become ready within timeout. Output:\n${output}`);
  }

  return { child, baseUrl };
}

async function stopRuntimeServer(runtime) {
  if (!runtime || !runtime.child || runtime.child.killed) return;
  runtime.child.kill('SIGTERM');
  await sleep(800);
  if (!runtime.child.killed) {
    runtime.child.kill('SIGKILL');
  }
}

// Test 1: Verify HTML file exists and contains required elements
function testHTMLStructure() {
  log('\n=== Testing HTML Structure ===\n', colors.blue);

  const htmlPath = path.join(__dirname, 'public', 'index.html');

  try {
    const htmlContent = fs.readFileSync(htmlPath, 'utf8');

    // Test HTML file exists
    testResult('HTML file exists', true, 'public/index.html found');

    // Test for essential elements that display data
    const requiredElements = [
      { pattern: /id=["']prListContainer["']/, name: 'PR list container element' },
      { pattern: /id=["']repoList["']/, name: 'Repository list element' },
      { pattern: /fetch\(['"`]\/api\/prs/, name: 'API fetch for PRs' },
      { pattern: /fetch\(['"`]\/api\/repos/, name: 'API fetch for repos' },
      { pattern: /fetch\(['"`]\/api\/authors/, name: 'API fetch for authors' },
      { pattern: /fetch\(['"`]\/api\/auth\/user/, name: 'API fetch for auth user state' },
      { pattern: /id=["']authControlsDesktop["']/, name: 'Desktop auth controls container' },
      { pattern: /id=["']authControlsMobile["']/, name: 'Mobile auth controls container' },
      { pattern: /<table/, name: 'Table element for data display' },
    ];

    requiredElements.forEach(({ pattern, name }) => {
      const found = pattern.test(htmlContent);
      testResult(name, found, found ? 'Found in HTML' : 'Missing from HTML');
    });

    // Test for PR data fields that should be displayed
    const dataFields = [
      { pattern: /pr_number|PR\s*#|Pull\s*Request/i, name: 'PR number display' },
      { pattern: /\b(pr[_-]?)?title\b|data-title|"title"\s*:/i, name: 'PR title display' },
      { pattern: /\b(author|creator)[_-]?(login|name)?\b|data-author|"author[_-]?login"\s*:/i, name: 'Author/creator display' },
      { pattern: /\b(checks?|ci)[_-]?(passed|failed|status)?\b|data-checks|"checks_"/i, name: 'Checks/CI status display' },
      { pattern: /\b(review|approval)[_-]?(status|state)?\b|data-review|"review_status"\s*:/i, name: 'Review status display' },
    ];

    dataFields.forEach(({ pattern, name }) => {
      const found = pattern.test(htmlContent);
      testResult(name, found, found ? 'Display logic found' : 'Display logic not found');
    });

    // Test for pagination elements
    testResult(
      'Pagination support',
      /pagination|page|next|previous/i.test(htmlContent),
      'Pagination-related code found'
    );

    // Test for sorting capability
    testResult(
      'Sorting functionality',
      /sort|order/i.test(htmlContent),
      'Sorting-related code found'
    );

  } catch (error) {
    testResult('HTML file readable', false, error.message);
  }
}

// Test 2: Verify Python source files exist and contain required handlers
function testPythonHandlers() {
  log('\n=== Testing Python API Handlers ===\n', colors.blue);

  const handlersPath = path.join(__dirname, 'src', 'handlers.py');

  try {
    const handlersContent = fs.readFileSync(handlersPath, 'utf8');

    testResult('handlers.py exists', true, 'src/handlers.py found');

    // Test for essential API handlers
    const requiredHandlers = [
      { pattern: /def\s+handle_list_prs/, name: 'handle_list_prs function' },
      { pattern: /def\s+handle_list_repos/, name: 'handle_list_repos function' },
      { pattern: /def\s+handle_list_authors/, name: 'handle_list_authors function' },
      { pattern: /def\s+handle_add_pr/, name: 'handle_add_pr function' },
      { pattern: /def\s+handle_refresh_pr/, name: 'handle_refresh_pr function' },
      { pattern: /resolve_github_token/, name: 'centralized token resolver usage' },
    ];

    requiredHandlers.forEach(({ pattern, name }) => {
      const found = pattern.test(handlersContent);
      testResult(name, found, found ? 'Handler implemented' : 'Handler missing');
    });

    // Test for JSON response formatting
    testResult(
      'JSON response formatting',
      /json\.dumps/.test(handlersContent),
      'JSON serialization found'
    );

    // Test for pagination logic
    testResult(
      'Pagination implementation',
      /\b(pagination|page|per_page|offset|limit)\b/i.test(handlersContent),
      'Pagination logic found'
    );

    // Test for dynamic column validation (no whitelist)
    testResult(
      'Dynamic column validation (no whitelist)',
      /def\s+is_valid_column_name/.test(handlersContent) && !/allowed_columns\s*=\s*\{/.test(handlersContent),
      'Column validation function exists and whitelist removed'
    );

    // Test for issues_count SQL expression
    testResult(
      'issues_count computed field support',
      (/ISSUES_COUNT_SQL_EXPR/.test(handlersContent) && /'issues_count':\s*ISSUES_COUNT_SQL_EXPR/.test(handlersContent)) ||
      /'issues_count':\s*'\(.*json_array_length\(blockers\).*json_array_length\(warnings\).*\)'/.test(handlersContent),
      'issues_count SQL expression found (as constant or inline)'
    );

    // Test for "ready" column mapping
    testResult(
      '"ready" column mapping to merge_ready',
      /'ready':\s*'merge_ready'/.test(handlersContent),
      '"ready" maps to merge_ready database column'
    );

  } catch (error) {
    testResult('handlers.py readable', false, error.message);
  }
}

// Test 3: Verify database migrations support required data fields
function testDatabaseSchema() {
  log('\n=== Testing Database Migrations ===\n', colors.blue);

  const migrationsPath = path.join(__dirname, 'migrations');

  try {
    // Check if migrations folder exists
    if (!fs.existsSync(migrationsPath)) {
      testResult('migrations folder exists', false, 'migrations folder not found');
      return;
    }

    testResult('migrations folder exists', true, 'migrations folder found');

    // Get all migration files
    const migrationFiles = fs.readdirSync(migrationsPath)
      .filter(f => f.endsWith('.sql'))
      .sort();

    testResult('migration files exist', migrationFiles.length > 0,
      migrationFiles.length > 0 ? `Found ${migrationFiles.length} migration file(s)` : 'No migration files found');

    if (migrationFiles.length === 0) return;

    // Read all migrations to check for required fields
    const allMigrations = migrationFiles
      .map(f => fs.readFileSync(path.join(migrationsPath, f), 'utf8'))
      .join('\n');

    // Test for essential PR data fields
    const requiredFields = [
      { pattern: /pr_number/, name: 'pr_number field' },
      { pattern: /title/, name: 'title field' },
      { pattern: /author_login/, name: 'author_login field' },
      { pattern: /repo_owner/, name: 'repo_owner field' },
      { pattern: /repo_name/, name: 'repo_name field' },
      { pattern: /checks_passed/, name: 'checks_passed field' },
      { pattern: /checks_failed/, name: 'checks_failed field' },
      { pattern: /mergeable_state/, name: 'mergeable_state field' },
      { pattern: /review_status/, name: 'review_status field' },
    ];

    requiredFields.forEach(({ pattern, name }) => {
      const found = pattern.test(allMigrations);
      testResult(name, found, found ? 'Field defined in migrations' : 'Field missing from migrations');
    });

    // Test for prs table
    testResult(
      'PRs table definition',
      /CREATE\s+TABLE.*prs/i.test(allMigrations),
      'PRs table defined'
    );

  } catch (error) {
    testResult('migrations readable', false, error.message);
  }
}

// Test 4: Verify wrangler configuration
function testWranglerConfig() {
  log('\n=== Testing Wrangler Configuration ===\n', colors.blue);

  const wranglerPath = path.join(__dirname, 'wrangler.toml');

  try {
    const wranglerContent = fs.readFileSync(wranglerPath, 'utf8');

    testResult('wrangler.toml exists', true, 'wrangler.toml found');

    // Test for essential configuration
    const requiredConfig = [
      { pattern: /main\s*=.*index\.py/, name: 'Python entry point configured' },
      { pattern: /d1_databases/, name: 'D1 database binding configured' },
      { pattern: /^\[assets\]/m, name: 'Static assets configured' },
      { pattern: /directory\s*=.*public/, name: 'Public directory configured' },
      { pattern: /python_workers/, name: 'Python workers compatibility flag' },
    ];

    requiredConfig.forEach(({ pattern, name }) => {
      const found = pattern.test(wranglerContent);
      testResult(name, found, found ? 'Configuration present' : 'Configuration missing');
    });

  } catch (error) {
    testResult('wrangler.toml readable', false, error.message);
  }
}

// Test 5: Verify package.json has required scripts
function testPackageJson() {
  log('\n=== Testing Package Configuration ===\n', colors.blue);

  const packagePath = path.join(__dirname, 'package.json');

  try {
    const packageContent = JSON.parse(fs.readFileSync(packagePath, 'utf8'));

    testResult('package.json exists', true, 'package.json found');

    // Test for essential scripts
    const requiredScripts = ['dev', 'deploy'];

    requiredScripts.forEach(script => {
      const exists = packageContent.scripts && packageContent.scripts[script];
      testResult(
        `npm script: ${script}`,
        exists,
        exists ? `Script defined: ${packageContent.scripts[script]}` : 'Script missing'
      );
    });

    // Test for wrangler dependency
    testResult(
      'wrangler dependency',
      packageContent.devDependencies && packageContent.devDependencies.wrangler,
      packageContent.devDependencies?.wrangler || 'Dependency missing'
    );

  } catch (error) {
    testResult('package.json readable/parseable', false, error.message);
  }
}

// Test 6: Verify API endpoint routing in index.py
function testAPIRouting() {
  log('\n=== Testing API Routing ===\n', colors.blue);

  const indexPath = path.join(__dirname, 'src', 'index.py');

  try {
    const indexContent = fs.readFileSync(indexPath, 'utf8');

    testResult('index.py exists', true, 'src/index.py found');

    // Test for essential API routes
    const requiredRoutes = [
      { pattern: /\/api\/prs/, name: '/api/prs endpoint' },
      { pattern: /\/api\/repos/, name: '/api/repos endpoint' },
      { pattern: /\/api\/authors/, name: '/api/authors endpoint' },
      { pattern: /\/api\/refresh/, name: '/api/refresh endpoint' },
      { pattern: /\/api\/status/, name: '/api/status endpoint' },
    ];

    requiredRoutes.forEach(({ pattern, name }) => {
      const found = pattern.test(indexContent);
      testResult(name, found, found ? 'Route configured' : 'Route missing');
    });

    const authRoutes = [
      { pattern: /\/api\/auth\/login/, name: '/api/auth/login endpoint' },
      { pattern: /\/api\/auth\/callback/, name: '/api/auth/callback endpoint' },
      { pattern: /\/api\/auth\/user/, name: '/api/auth/user endpoint' },
      { pattern: /\/api\/auth\/logout/, name: '/api/auth/logout endpoint' },
    ];
    authRoutes.forEach(({ pattern, name }) => {
      const found = pattern.test(indexContent);
      testResult(name, found, found ? 'Auth route configured' : 'Auth route missing');
    });

    // Test for CORS headers (important for data display)
    testResult(
      'CORS headers configuration',
      /Access-Control-Allow-Origin/.test(indexContent),
      'CORS configured for API access'
    );

    // Test for static asset serving
    testResult(
      'Static asset serving',
      /(env\.ASSETS|ASSETS\s*=|['"`]\/assets\/|hasattr.*ASSETS)/i.test(indexContent),
      'Asset serving configured'
    );

  } catch (error) {
    testResult('index.py readable', false, error.message);
  }
}

// Test 7: Verify OAuth authentication implementation and security controls
function testAuthenticationImplementation() {
  log('\n=== Testing Authentication Implementation ===\n', colors.blue);

  const authPath = path.join(__dirname, 'src', 'auth.py');
  const authHandlersPath = path.join(__dirname, 'src', 'auth_handlers.py');
  const handlersPath = path.join(__dirname, 'src', 'handlers.py');
  const swPath = path.join(__dirname, 'public', 'sw.js');
  const htmlPath = path.join(__dirname, 'public', 'index.html');

  try {
    const authContent = fs.readFileSync(authPath, 'utf8');
    const authHandlersContent = fs.readFileSync(authHandlersPath, 'utf8');
    const handlersContent = fs.readFileSync(handlersPath, 'utf8');
    const swContent = fs.readFileSync(swPath, 'utf8');
    const htmlContent = fs.readFileSync(htmlPath, 'utf8');

    testResult('auth.py exists', true, 'src/auth.py found');
    testResult('auth_handlers.py exists', true, 'src/auth_handlers.py found');

    // Cookie/session security expectations
    testResult(
      'OAuth session/state cookie constants defined',
      /SESSION_COOKIE_NAME\s*=\s*['"]blt_oauth_session['"]/.test(authContent) &&
      /STATE_COOKIE_NAME\s*=\s*['"]blt_oauth_state['"]/.test(authContent),
      'Cookie names are defined'
    );
    testResult(
      'Session and state TTL constants configured',
      /SESSION_MAX_AGE\s*=\s*60\s*\*\s*60\s*\*\s*24\s*\*\s*30/.test(authContent) &&
      /STATE_MAX_AGE\s*=\s*60\s*\*\s*10/.test(authContent),
      '30d session and 10m state TTL are configured'
    );
    testResult(
      'Cookie security flags enforced',
      /SameSite=\{same_site\}/.test(authContent) &&
      /parts\.append\('Secure'\)/.test(authContent) &&
      /parts\.append\('HttpOnly'\)/.test(authContent),
      'SameSite, Secure, and HttpOnly are set'
    );

    // Encryption expectations
    testResult(
      'OAuth session encryption uses AES-GCM',
      /'AES-GCM'/.test(authContent) &&
      /async\s+def\s+encrypt_session/.test(authContent) &&
      /async\s+def\s+decrypt_session/.test(authContent),
      'AES-GCM encrypt/decrypt helpers found'
    );
    testResult(
      'Encryption key validation enforced',
      /ENCRYPTION_KEY is required/.test(authContent) &&
      /must decode to exactly 32 bytes/.test(authContent),
      'ENCRYPTION_KEY validation found'
    );

    // Token resolution and precedence expectations
    const idxUser = authContent.indexOf("'token_source': 'user_oauth'");
    const idxHeader = authContent.indexOf("'token_source': 'header_token'");
    const idxShared = authContent.indexOf("'token_source': 'shared_token'");
    const idxUnauth = authContent.indexOf("'token_source': 'unauthenticated'");

    testResult(
      'Token sources are explicitly defined',
      idxUser >= 0 && idxHeader >= 0 && idxShared >= 0 && idxUnauth >= 0,
      'user_oauth/header_token/shared_token/unauthenticated present'
    );
    testResult(
      'Token resolution precedence is correct',
      idxUser < idxHeader && idxHeader < idxShared && idxShared < idxUnauth,
      'Precedence: user_oauth -> header_token -> shared_token -> unauthenticated'
    );

    // OAuth flow expectations
    testResult(
      'OAuth login handler sets state and redirects to GitHub authorize',
      /async\s+def\s+handle_auth_login/.test(authHandlersContent) &&
      /generate_oauth_state/.test(authHandlersContent) &&
      /build_state_cookie/.test(authHandlersContent) &&
      /github\.com\/login\/oauth\/authorize/.test(authHandlersContent),
      'Login flow wiring found'
    );

    const idxStateValidation = authHandlersContent.indexOf('validate_oauth_state');
    const idxTokenExchange = authHandlersContent.indexOf('_exchange_code_for_token');
    testResult(
      'OAuth callback validates state before token exchange',
      idxStateValidation >= 0 && idxTokenExchange >= 0 && idxStateValidation < idxTokenExchange,
      'State validation appears before code exchange in callback flow'
    );

    testResult(
      'OAuth callback performs server-side code exchange and user fetch',
      /login\/oauth\/access_token/.test(authHandlersContent) &&
      /https:\/\/api\.github\.com\/user/.test(authHandlersContent),
      'Token exchange and user profile fetch found'
    );

    testResult(
      'OAuth callback persists encrypted session cookie',
      /encrypt_session/.test(authHandlersContent) &&
      /build_session_cookie/.test(authHandlersContent),
      'Encrypted session cookie write found'
    );

    testResult(
      'Auth user/logout handlers implemented',
      /async\s+def\s+handle_auth_user/.test(authHandlersContent) &&
      /async\s+def\s+handle_auth_logout/.test(authHandlersContent) &&
      /clear_session_cookie/.test(authHandlersContent) &&
      /clear_state_cookie/.test(authHandlersContent),
      'Auth user and logout handlers found'
    );

    // Handler integration expectations
    const functionsRequiringTokenResolution = [
      'handle_add_pr',
      'handle_refresh_pr',
      'handle_batch_refresh_prs',
      'handle_pr_timeline',
      'handle_pr_review_analysis',
      'handle_pr_readiness',
      'handle_rate_limit',
    ];
    const getAsyncFunctionBlock = (content, fnName) => {
      const escaped = fnName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const re = new RegExp(`async\\s+def\\s+${escaped}\\([\\s\\S]*?(?=\\nasync\\s+def\\s+|\\n$)`, 'm');
      const match = content.match(re);
      return match ? match[0] : '';
    };
    const missingResolverFns = functionsRequiringTokenResolution.filter((fnName) => {
      const fnBlock = getAsyncFunctionBlock(handlersContent, fnName);
      return !fnBlock || !/resolve_github_token/.test(fnBlock);
    });
    testResult(
      'Token resolver is used in all auth-sensitive handlers',
      missingResolverFns.length === 0,
      missingResolverFns.length === 0
        ? 'All targeted handlers call resolve_github_token'
        : `Missing in: ${missingResolverFns.join(', ')}`
    );

    testResult(
      'Legacy direct header token reads removed from handlers',
      !/request\.headers\.get\('x-github-token'\)/.test(handlersContent),
      'No direct x-github-token reads in handlers.py'
    );

    // Frontend and caching expectations
    testResult(
      'Frontend auth UX uses OAuth endpoints',
      /fetch\(['"`]\/api\/auth\/user/.test(htmlContent) &&
      /href=["']\/api\/auth\/login["']/.test(htmlContent) &&
      /fetch\(['"`]\/api\/auth\/logout/.test(htmlContent),
      'Frontend sign-in/sign-out and auth state calls found'
    );

    testResult(
      'No PAT prompt text present in frontend',
      !/(personal access token|\bPAT\b)/i.test(htmlContent),
      'No PAT prompt detected in public/index.html'
    );

    testResult(
      'Service worker bypasses auth and rate-limit token-dependent routes',
      /pathname\.startsWith\('\/api\/auth\/'\)/.test(swContent) &&
      /pathname\s*===\s*'\/api\/rate-limit'/.test(swContent),
      'SW bypass rules for auth/rate-limit found'
    );
  } catch (error) {
    testResult('Authentication test files readable', false, error.message);
  }
}

// Test 8: Verify OAuth runtime behavior with real HTTP responses
async function testAuthenticationRuntimeBehavior() {
  log('\n=== Testing Authentication Runtime Behavior ===\n', colors.blue);

  let runtime;
  try {
    runtime = await startRuntimeServer();

    // Callback error path should redirect and clear state cookie
    const callbackErrorResp = await fetch(`${runtime.baseUrl}/api/auth/callback?error=access_denied`, {
      redirect: 'manual',
    });
    const callbackErrorLocation = callbackErrorResp.headers.get('Location') || callbackErrorResp.headers.get('location') || '';
    const callbackErrorCookies = getSetCookieHeader(callbackErrorResp);

    testResult(
      'Runtime callback error returns auth error redirect',
      callbackErrorLocation.includes('?auth=error'),
      callbackErrorLocation ? `Location: ${callbackErrorLocation}` : 'Missing Location header'
    );
    testResult(
      'Runtime callback error clears OAuth state cookie',
      callbackErrorCookies.includes('blt_oauth_state=') && callbackErrorCookies.includes('Max-Age=0'),
      callbackErrorCookies ? 'Found state cookie clear header' : 'Missing Set-Cookie header'
    );

    // Missing code should redirect and clear state cookie
    const missingCodeResp = await fetch(`${runtime.baseUrl}/api/auth/callback?state=abc123`, {
      redirect: 'manual',
      headers: { Cookie: 'blt_oauth_state=abc123' },
    });
    const missingCodeLocation = missingCodeResp.headers.get('Location') || missingCodeResp.headers.get('location') || '';
    const missingCodeCookies = getSetCookieHeader(missingCodeResp);

    testResult(
      'Runtime callback missing code redirects to auth error',
      missingCodeLocation.includes('?auth=error'),
      missingCodeLocation ? `Location: ${missingCodeLocation}` : 'Missing Location header'
    );
    testResult(
      'Runtime callback missing code clears state cookie',
      missingCodeCookies.includes('blt_oauth_state=') && missingCodeCookies.includes('Max-Age=0'),
      missingCodeCookies ? 'Found state cookie clear header' : 'Missing Set-Cookie header'
    );

    // Invalid state should redirect and clear state cookie
    const invalidStateResp = await fetch(`${runtime.baseUrl}/api/auth/callback?code=fake-code&state=bad-state`, {
      redirect: 'manual',
      headers: { Cookie: 'blt_oauth_state=good-state' },
    });
    const invalidStateLocation = invalidStateResp.headers.get('Location') || invalidStateResp.headers.get('location') || '';
    const invalidStateCookies = getSetCookieHeader(invalidStateResp);

    testResult(
      'Runtime callback invalid state redirects to auth error',
      invalidStateLocation.includes('?auth=error'),
      invalidStateLocation ? `Location: ${invalidStateLocation}` : 'Missing Location header'
    );
    testResult(
      'Runtime callback invalid state clears state cookie',
      invalidStateCookies.includes('blt_oauth_state=') && invalidStateCookies.includes('Max-Age=0'),
      invalidStateCookies ? 'Found state cookie clear header' : 'Missing Set-Cookie header'
    );

    // User endpoint should invalidate malformed session cookie
    const userResp = await fetch(`${runtime.baseUrl}/api/auth/user`, {
      headers: { Cookie: 'blt_oauth_session=invalid.session.payload' },
    });
    const userData = await userResp.json();
    const userCookies = getSetCookieHeader(userResp);

    testResult(
      'Runtime auth user reports invalid session cookie',
      userData && userData.auth_reason === 'invalid_session_cookie' && userData.authenticated === false,
      `auth_reason=${userData?.auth_reason}, authenticated=${userData?.authenticated}`
    );
    testResult(
      'Runtime auth user clears invalid session cookie',
      userCookies.includes('blt_oauth_session=') && userCookies.includes('Max-Age=0'),
      userCookies ? 'Found session cookie clear header' : 'Missing Set-Cookie header'
    );

    // Logout should clear both session and state cookies
    const logoutResp = await fetch(`${runtime.baseUrl}/api/auth/logout`, {
      method: 'POST',
    });
    const logoutData = await logoutResp.json();
    const logoutCookies = getSetCookieHeader(logoutResp);

    testResult(
      'Runtime logout returns success payload',
      logoutData && logoutData.success === true && logoutData.authenticated === false,
      JSON.stringify(logoutData)
    );
    testResult(
      'Runtime logout clears session cookie',
      logoutCookies.includes('blt_oauth_session=') && logoutCookies.includes('Max-Age=0'),
      logoutCookies ? 'Found session clear cookie header' : 'Missing Set-Cookie header'
    );
    testResult(
      'Runtime logout clears state cookie',
      logoutCookies.includes('blt_oauth_state=') && logoutCookies.includes('Max-Age=0'),
      logoutCookies ? 'Found state clear cookie header' : 'Missing Set-Cookie header'
    );
  } catch (error) {
    testResult('Authentication runtime behavior test setup', false, error.message);
  } finally {
    await stopRuntimeServer(runtime);
  }
}

// Main test runner
async function runTests() {
  log('\n' + '='.repeat(60), colors.blue);
  log('  BLT-Leaf Data Display Test Suite', colors.blue);
  log('='.repeat(60) + '\n', colors.blue);

  testHTMLStructure();
  testPythonHandlers();
  testDatabaseSchema();
  testWranglerConfig();
  testPackageJson();
  testAPIRouting();
  testAuthenticationImplementation();
  await testAuthenticationRuntimeBehavior();

  // Summary
  log('\n' + '='.repeat(60), colors.blue);
  log('  Test Summary', colors.blue);
  log('='.repeat(60), colors.blue);

  const total = testsPassed + testsFailed;
  log(`\nTotal Tests: ${total}`);
  log(`Passed: ${testsPassed}`, colors.green);
  log(`Failed: ${testsFailed}`, testsFailed > 0 ? colors.red : colors.green);

  const successRate = total > 0 ? ((testsPassed / total) * 100).toFixed(1) : 0;
  log(`\nSuccess Rate: ${successRate}%\n`, successRate >= 90 ? colors.green : colors.yellow);

  // Exit with appropriate code
  if (testsFailed > 0) {
    log('❌ Some tests failed. Please review the output above.\n', colors.red);
    process.exit(1);
  } else {
    log('✅ All tests passed! Data display structure is correct.\n', colors.green);
    process.exit(0);
  }
}

// Run tests
runTests();
