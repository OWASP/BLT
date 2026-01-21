# Testing Documentation

This document describes the testing infrastructure for the BLT-Action GitHub Action.

## Overview

The BLT-Action has comprehensive test coverage across unit tests, integration tests, and build verification to ensure all features work correctly.

## Test Structure

### Unit Tests (`src/mock-test.js`)

The unit tests use Mocha and Nock to test individual components of the action. All tests use mocked HTTP requests to test functionality without requiring actual API calls.

**Total: 21 tests across 8 categories**

#### 1. Assignment Management (3 tests)
- ✅ User assignment to issues
- ✅ User unassignment from issues  
- ✅ Detection of all 10 assignment keywords:
  - `/assign`
  - `assign to me`
  - `assign this to me`
  - `assign it to me`
  - `assign me this`
  - `work on this`
  - `i can try fixing this`
  - `i am interested in doing this`
  - `be assigned this`
  - `i am interested in contributing`

#### 2. Label Management (2 tests)
- ✅ Adding "assigned" label to issues
- ✅ Removing "assigned" label from issues

#### 3. Giphy Integration (2 tests)
- ✅ Successful GIF posting from Giphy API
- ✅ Handling "no GIFs found" scenario

#### 4. Kudos System (2 tests)
- ✅ Sending kudos to OWASP BLT API
- ✅ Handling default kudos message

#### 5. Command Detection (3 tests)
- ✅ `/unassign` command detection
- ✅ `/giphy` command detection
- ✅ `/kudos` command detection

#### 6. Attribution (2 tests)
- ✅ Attribution footer in all comment types
- ✅ Consistent attribution format

#### 7. Error Handling (3 tests)
- ✅ GitHub API error handling
- ✅ Giphy API error handling
- ✅ Kudos API error handling

#### 8. Human Commenter Guard (5 tests)

- ✅ treats bots and GitHub Apps as non-human commenters
- ✅ does not allow bots to trigger /assign or /unassign, even with valid phrases
- ✅ allows human users to trigger /assign and /unassign commands
- ✅ treats mannequin accounts as human commenters

### Integration Tests (`.github/workflows/integration-test.yml`)

Integration tests verify that all components work together correctly and that the action is properly configured.

**Tests include:**

1. **Action Structure Validation**
   - Verifies required files exist (`action.yml`, `dist/index.js`, `src/index.js`)
   - Checks all required inputs are defined
   - Confirms Node.js 20 runtime is used

2. **Command Keyword Detection**
   - Validates all assignment keywords are documented
   - Confirms command implementations (`/assign`, `/unassign`, `/giphy`, `/kudos`)

3. **Feature Implementation Checks**
   - User assignment/unassignment
   - Label management (add/remove)
   - Stale issue detection
   - Inactivity calculation
   - PR cross-reference checking
   - Multi-assignment prevention
   - Giphy API integration
   - Kudos API integration
   - Attribution footer

4. **Event Handling**
   - Issue comment events
   - Pull request review comment events
   - GitHub context processing

5. **API Integration Verification**
   - GitHub API client setup
   - Octokit instance creation
   - HTTP client for external APIs

6. **Error Handling Validation**
   - Try-catch block presence
   - Error catching implementation
   - Error logging

### Build Verification (`.github/workflows/verify-build.yml`)

Ensures the compiled distribution file (`dist/index.js`) is up to date with source changes.

**Checks:**
- ✅ Build succeeds without errors
- ✅ `dist/` directory is current (no uncommitted changes)

### Test Execution (`.github/workflows/test.yml`)

Runs the full unit test suite on every push and pull request.

**Steps:**
1. Install dependencies
2. Run unit tests
3. Report test coverage summary

## Running Tests Locally

### Prerequisites
```bash
npm install
```

### Run Unit Tests
```bash
npm test
```

### Run Build Verification
```bash
npm run build
git status dist/
```

### Simulate Integration Tests
Run the verification checks manually:
```bash
# Check action structure
test -f action.yml && echo "✓ action.yml exists"
test -f dist/index.js && echo "✓ dist/index.js exists"

# Verify features
grep -q "/unassign" src/index.js && echo "✓ /unassign implemented"
grep -q "/giphy" src/index.js && echo "✓ /giphy implemented"
grep -q "/kudos" src/index.js && echo "✓ /kudos implemented"
```

## Test Coverage Summary

| Category | Tests | Status |
|----------|-------|--------|
| Assignment Management | 3 | ✅ |
| Label Management | 2 | ✅ |
| Giphy Integration | 2 | ✅ |
| Kudos System | 2 | ✅ |
| Command Detection | 3 | ✅ |
| Attribution | 2 | ✅ |
| Error Handling | 3 | ✅ |
| Human Commenter Guard | 4 | ✅ |
| **Total** | **21** | **✅** |

## Features Tested

- ✅ Self-assignment via `/assign` and natural language
- ✅ Unassignment via `/unassign`
- ✅ Multi-assignment prevention (blocks users with unfinished issues)
- ✅ Duplicate assignment prevention
- ✅ Label management ("assigned" label)
- ✅ GIF posting via `/giphy [search term]`
- ✅ Kudos sending via `/kudos @user [message]`
- ✅ Stale issue handling (24-hour auto-unassign)
- ✅ PR validation (cross-reference checking)
- ✅ Attribution footer in all comments
- ✅ Issue comment event handling
- ✅ Pull request review comment event handling
- ✅ Error handling for all API calls

## Adding New Tests

When adding new features to the action:

1. **Add unit tests** in `src/mock-test.js`:
   - Use `nock` to mock HTTP requests
   - Test both success and failure scenarios
   - Verify error handling

2. **Update integration tests** in `.github/workflows/integration-test.yml`:
   - Add feature verification checks
   - Test command detection if applicable
   - Verify API integration if needed

3. **Update this documentation** with:
   - New test descriptions
   - Updated test counts
   - New features tested

## CI/CD Pipeline

Tests run automatically on:
- Every push to any branch
- Every pull request
- Manual workflow dispatch

All tests must pass before code can be merged.

## Troubleshooting

### Tests fail locally but pass in CI
- Ensure you have the latest dependencies: `npm install`
- Check Node.js version matches CI (v20)

### Build verification fails
- Run `npm run build` to update `dist/`
- Commit the updated `dist/index.js` file

### Mock tests fail
- Check if Nock is properly cleaning up: `nock.cleanAll()` in `beforeEach`
- Verify mock URLs match actual API calls
- Ensure mock data structure matches expected responses

## Resources

- [Mocha Test Framework](https://mochajs.org/)
- [Nock HTTP Mocking](https://github.com/nock/nock)
- [GitHub Actions Testing](https://docs.github.com/en/actions/creating-actions/creating-a-javascript-action#testing-your-action)
