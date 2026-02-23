'use strict';

const { handleIssueOpened, handleIssueLabeled, BUG_LABELS } = require('../src/handlers/issue-opened');

jest.mock('../src/blt-api', () => ({
  reportBugToBLT: jest.fn().mockResolvedValue({ id: 42 }),
}));

const { reportBugToBLT } = require('../src/blt-api');

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
      issue: {
        number: 1,
        title: 'Test issue',
        html_url: 'https://github.com/OWASP-BLT/TestRepo/issues/1',
        labels: [],
        ...overrides.issue,
      },
      sender: {
        login: 'alice',
        type: 'User',
        ...overrides.sender,
      },
      label: overrides.label,
    },
    _calls: calls,
  };
  return context;
}

describe('handleIssueOpened', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('posts welcome message for new issue', async () => {
    const context = makeContext();
    await handleIssueOpened(context);
    expect(context.octokit.issues.createComment).toHaveBeenCalled();
    const comment = context._calls.createComment[0].body;
    expect(comment).toContain('Thanks for opening this issue');
    expect(comment).toContain('/assign');
  });

  test('reports bug to BLT when issue has bug label', async () => {
    const context = makeContext({ issue: { labels: [{ name: 'bug' }] } });
    await handleIssueOpened(context);
    expect(reportBugToBLT).toHaveBeenCalled();
    const comment = context._calls.createComment[0].body;
    expect(comment).toContain('Bug ID: #42');
  });

  test('does not report bug to BLT without bug label', async () => {
    const context = makeContext({ issue: { labels: [] } });
    await handleIssueOpened(context);
    expect(reportBugToBLT).not.toHaveBeenCalled();
  });

  test('ignores bot users', async () => {
    const context = makeContext({ sender: { login: 'bot', type: 'Bot' } });
    await handleIssueOpened(context);
    expect(context.octokit.issues.createComment).not.toHaveBeenCalled();
  });
});

describe('handleIssueLabeled', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('reports to BLT when bug label added', async () => {
    const context = makeContext({
      issue: { labels: [{ name: 'bug' }] },
      label: { name: 'bug' },
    });
    await handleIssueLabeled(context);
    expect(reportBugToBLT).toHaveBeenCalled();
    const comment = context._calls.createComment[0].body;
    expect(comment).toContain('Bug ID: #42');
  });

  test('does not report to BLT for non-bug labels', async () => {
    const context = makeContext({
      issue: { labels: [{ name: 'enhancement' }] },
      label: { name: 'enhancement' },
    });
    await handleIssueLabeled(context);
    expect(reportBugToBLT).not.toHaveBeenCalled();
  });

  test('does not report if bug label already present before this event', async () => {
    const context = makeContext({
      issue: { labels: [{ name: 'bug' }, { name: 'vulnerability' }] },
      label: { name: 'vulnerability' },
    });
    await handleIssueLabeled(context);
    expect(reportBugToBLT).not.toHaveBeenCalled();
  });
});

describe('BUG_LABELS', () => {
  test('includes expected labels', () => {
    expect(BUG_LABELS).toContain('bug');
    expect(BUG_LABELS).toContain('vulnerability');
    expect(BUG_LABELS).toContain('security');
  });
});
