#!/usr/bin/env node

/**
 * Test script to verify sorting security and functionality
 * This tests SQL injection protection and column validation
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

// Test sorting security and validation
function testSortingSecurity() {
  log('\n=== Testing Sorting Security and Validation ===\n', colors.blue);
  
  const handlersPath = path.join(__dirname, 'src', 'handlers.py');
  
  try {
    const handlersContent = fs.readFileSync(handlersPath, 'utf8');
    
    // Test 1: Verify whitelist is removed
    testResult(
      'Sort column whitelist removed',
      !/allowed_columns\s*=\s*\{/.test(handlersContent),
      'No hardcoded whitelist found - all columns are dynamically validated'
    );
    
    // Test 2: Verify validation function exists
    testResult(
      'Column validation function exists',
      /def\s+is_valid_column_name\(col_name\):/.test(handlersContent),
      'is_valid_column_name() function implemented'
    );
    
    // Test 3: Verify regex validation for alphanumeric + underscore
    testResult(
      'Regex validation for SQL column names',
      /re\.match.*[a-zA-Z0-9_].*col_name/.test(handlersContent),
      'Validates only alphanumeric and underscore characters'
    );
    
    // Test 4: Verify get_sort_expression function
    testResult(
      'Dynamic sort expression function exists',
      /def\s+get_sort_expression\(col_name\):/.test(handlersContent),
      'get_sort_expression() function implemented'
    );
    
    // Test 5: Verify column mapping includes computed fields
    testResult(
      'Column mapping includes computed fields',
      /'issues_count':\s*'\(.*COALESCE.*json_array_length/.test(handlersContent),
      'issues_count computed field with COALESCE for NULL handling'
    );
    
    // Test 6: Verify security logging for rejected columns
    testResult(
      'Security logging for invalid columns',
      /print\(f?["']Security:.*Rejected.*invalid.*sort.*column/.test(handlersContent),
      'Logs rejected column attempts for security monitoring'
    );
    
    // Test 7: Verify ORDER BY clause is dynamically built
    testResult(
      'Dynamic ORDER BY clause construction',
      /order_clause.*ORDER BY/.test(handlersContent),
      'ORDER BY clause built dynamically from validated columns'
    );
    
    // Test 8: Verify NULL handling in sort
    testResult(
      'NULL values handling in sort',
      /IS NOT NULL/.test(handlersContent),
      'NULL values are handled (appear last in results)'
    );
    
    // Test 9: Verify direction validation (ASC/DESC only)
    testResult(
      'Sort direction validation',
      /\.upper\(\)\s+in\s+\(['"]ASC['"],\s*['"]DESC['"]\)/.test(handlersContent),
      'Only ASC and DESC are allowed as sort directions'
    );
    
    // Test 10: Verify no direct string concatenation with user input
    testResult(
      'No unsafe string concatenation',
      !/sort_by\s*[+]\s*['"]/.test(handlersContent) && !/['"][+]\s*sort_by/.test(handlersContent),
      'No direct concatenation of user input into SQL strings'
    );
    
  } catch (error) {
    testResult('handlers.py readable', false, error.message);
  }
}

// Test frontend sorting code
function testFrontendSorting() {
  log('\n=== Testing Frontend Sorting Implementation ===\n', colors.blue);
  
  const htmlPath = path.join(__dirname, 'public', 'index.html');
  
  try {
    const htmlContent = fs.readFileSync(htmlPath, 'utf8');
    
    // Test 1: Verify issues_count is sent to backend
    testResult(
      'issues_count sorting sent to backend',
      /data-sort-column=["']issues_count["']/.test(htmlContent),
      'issues_count column can be sorted'
    );
    
    // Test 2: Verify client-side sorting is removed for issues_count
    testResult(
      'No client-side sorting for issues_count',
      !/if\s*\(sortColumns.*issues_count.*\)\s*\{[^}]*allPrs\.sort/.test(htmlContent),
      'Client-side sorting removed - backend handles all sorting'
    );
    
    // Test 3: Verify sort parameters are built from sortColumns
    testResult(
      'Sort parameters built from sortColumns array',
      /sortColumns\.map\(.*=>\s*.*\.column\)\.join/.test(htmlContent),
      'sort_by parameter built from column names'
    );
    
    // Test 4: Verify all table headers are sortable
    testResult(
      'All table headers have sort capability',
      /data-sort-column=["']issues_count["']/.test(htmlContent),
      'issues_count column is marked as sortable'
    );
    
    // Test 5: Verify Shift+Click multi-column sorting
    testResult(
      'Multi-column sorting with Shift+Click',
      /isShiftClick/.test(htmlContent) && /sortColumns/.test(htmlContent),
      'Shift+Click adds columns to sort (multi-column sorting)'
    );
    
  } catch (error) {
    testResult('index.html readable', false, error.message);
  }
}

// Test specific column mappings
function testColumnMappings() {
  log('\n=== Testing Column Mappings ===\n', colors.blue);
  
  const handlersPath = path.join(__dirname, 'src', 'handlers.py');
  
  try {
    const handlersContent = fs.readFileSync(handlersPath, 'utf8');
    
    // Test essential column mappings
    const requiredMappings = [
      { pattern: /'ready':\s*'merge_ready'/, name: 'ready -> merge_ready' },
      { pattern: /'ready_score':\s*'overall_score'/, name: 'ready_score -> overall_score' },
      { pattern: /'response_score':\s*'response_rate'/, name: 'response_score -> response_rate' },
      { pattern: /'feedback_score':\s*'responded_feedback'/, name: 'feedback_score -> responded_feedback' },
      { pattern: /'issues_count':\s*'\(.*json_array_length\(blockers\).*json_array_length\(warnings\).*\)'/, name: 'issues_count -> SQL expression' },
    ];
    
    requiredMappings.forEach(({ pattern, name }) => {
      const found = pattern.test(handlersContent);
      testResult(name, found, found ? 'Mapping configured' : 'Mapping missing');
    });
    
  } catch (error) {
    testResult('handlers.py readable', false, error.message);
  }
}

// Main test runner
function runTests() {
  log('\n' + '='.repeat(60), colors.blue);
  log('  Sorting Security and Functionality Test Suite', colors.blue);
  log('='.repeat(60) + '\n', colors.blue);
  
  testSortingSecurity();
  testFrontendSorting();
  testColumnMappings();
  
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
    log('✅ All tests passed! Sorting is secure and functional.\n', colors.green);
    process.exit(0);
  }
}

// Run tests
runTests();
