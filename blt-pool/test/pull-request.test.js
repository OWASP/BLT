'use strict';

const { handlePullRequestOpened, handlePullRequestClosed } = require('../src/handlers/pull-request');

function makeContext(overrides = {}) {
  const calls = { createComment: [] };
  const context = {
    repo: () => ({ owner: 'OWASP-BLT', repo: 'TestRepo' }),
    issue: (params) => ({ owner: 'OWASP-BLT', repo: 'TestRepo', issue_number: 1, ...params }),
    octokit: {
      issues: {
        createComment: jest.fn(async (p) => calls.createComment.push(p)),
      },
    },
    payload: {
      pull_request: {
        number: 1,
        merged: false,
        user: { login: 'alice', type: 'User' },
        ...overrides.pull_request,
      },
      sender: {
        login: 'alice',
        type: 'User',
        ...overrides.sender,
      },
    },
    _calls: calls,
  };
  return context;
}

describe('handlePullRequestOpened', () => {
  test('posts welcome message for new PR', async () => {
    const context = makeContext();
    await handlePullRequestOpened(context);
    expect(context.octokit.issues.createComment).toHaveBeenCalled();
    const comment = context._calls.createComment[0].body;
    expect(comment).toContain('Thanks for opening this pull request');
    expect(comment).toContain('OWASP BLT');
  });

  test('ignores bot users', async () => {
    const context = makeContext({ sender: { login: 'bot', type: 'Bot' } });
    await handlePullRequestOpened(context);
    expect(context.octokit.issues.createComment).not.toHaveBeenCalled();
  });
});

describe('handlePullRequestClosed', () => {
  test('posts merge congratulations when PR is merged', async () => {
    const context = makeContext({
      pull_request: { merged: true, user: { login: 'alice', type: 'User' } },
    });
    await handlePullRequestClosed(context);
    expect(context.octokit.issues.createComment).toHaveBeenCalled();
    const comment = context._calls.createComment[0].body;
    expect(comment).toContain('PR merged');
    expect(comment).toContain('alice');
  });

  test('does not post when PR is closed without merging', async () => {
    const context = makeContext({ pull_request: { merged: false } });
    await handlePullRequestClosed(context);
    expect(context.octokit.issues.createComment).not.toHaveBeenCalled();
  });

  test('ignores bot merges', async () => {
    const context = makeContext({
      pull_request: { merged: true, user: { login: 'alice', type: 'User' } },
      sender: { login: 'bot', type: 'Bot' },
    });
    await handlePullRequestClosed(context);
    expect(context.octokit.issues.createComment).not.toHaveBeenCalled();
  });
});
