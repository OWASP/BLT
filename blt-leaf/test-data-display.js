#!/usr/bin/env node

/**
 * Test script to verify data display functionality
 * This tests both API endpoints and HTML structure
 */

const fs = require('fs');
const path = require('path');

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
      { pattern: /def\s+handle_add_pr/, name: 'handle_add_pr function' },
      { pattern: /def\s+handle_refresh_pr/, name: 'handle_refresh_pr function' },
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
      /'issues_count':\s*'\(.*json_array_length\(blockers\).*json_array_length\(warnings\).*\)'/.test(handlersContent),
      'issues_count SQL expression found in column mapping'
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

// Test 3: Verify database schema supports required data fields
function testDatabaseSchema() {
  log('\n=== Testing Database Schema ===\n', colors.blue);
  
  const schemaPath = path.join(__dirname, 'schema.sql');
  
  try {
    const schemaContent = fs.readFileSync(schemaPath, 'utf8');
    
    testResult('schema.sql exists', true, 'schema.sql found');
    
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
      const found = pattern.test(schemaContent);
      testResult(name, found, found ? 'Field defined in schema' : 'Field missing from schema');
    });
    
    // Test for prs table
    testResult(
      'PRs table definition',
      /CREATE\s+TABLE.*prs/i.test(schemaContent),
      'PRs table defined'
    );
    
  } catch (error) {
    testResult('schema.sql readable', false, error.message);
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
      { pattern: /\/api\/refresh/, name: '/api/refresh endpoint' },
      { pattern: /\/api\/status/, name: '/api/status endpoint' },
    ];
    
    requiredRoutes.forEach(({ pattern, name }) => {
      const found = pattern.test(indexContent);
      testResult(name, found, found ? 'Route configured' : 'Route missing');
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

// Main test runner
function runTests() {
  log('\n' + '='.repeat(60), colors.blue);
  log('  BLT-Leaf Data Display Test Suite', colors.blue);
  log('='.repeat(60) + '\n', colors.blue);
  
  testHTMLStructure();
  testPythonHandlers();
  testDatabaseSchema();
  testWranglerConfig();
  testPackageJson();
  testAPIRouting();
  
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
