'use strict';

const { isHumanUser, handleAssign, handleUnassign } = require('../src/handlers/issue-assign');

describe('isHumanUser', () => {
  test('returns true for User type', () => {
    expect(isHumanUser({ type: 'User', login: 'alice' })).toBe(true);
  });

  test('returns true for Mannequin type', () => {
    expect(isHumanUser({ type: 'Mannequin', login: 'mannequin1' })).toBe(true);
  });

  test('returns false for Bot type', () => {
    expect(isHumanUser({ type: 'Bot', login: 'some-bot' })).toBe(false);
  });

  test('returns false for null', () => {
    expect(isHumanUser(null)).toBe(false);
  });

  test('returns false for undefined', () => {
    expect(isHumanUser(undefined)).toBe(false);
  });
});

describe('handleAssign', () => {
  function makeContext(overrides = {}) {
    const calls = { addAssignees: [], createComment: [], removeAssignees: [] };
    const context = {
      repo: () => ({ owner: 'OWASP-BLT', repo: 'TestRepo' }),
      issue: (params) => ({ owner: 'OWASP-BLT', repo: 'TestRepo', issue_number: 1, ...params }),
      octokit: {
        issues: {
          addAssignees: jest.fn(async (p) => calls.addAssignees.push(p)),
          removeAssignees: jest.fn(async (p) => calls.removeAssignees.push(p)),
          createComment: jest.fn(async (p) => calls.createComment.push(p)),
        },
      },
      payload: {
        issue: {
          number: 1,
          state: 'open',
          assignees: [],
          pull_request: undefined,
          ...overrides.issue,
        },
        comment: {
          user: { login: 'alice', type: 'User' },
          body: '/assign',
          ...overrides.comment,
        },
      },
      _calls: calls,
    };
    return context;
  }

  test('assigns user to open issue', async () => {
    const context = makeContext();
    await handleAssign(context, context.payload.issue, 'alice');
    expect(context.octokit.issues.addAssignees).toHaveBeenCalledWith(
      expect.objectContaining({ assignees: ['alice'] })
    );
    expect(context.octokit.issues.createComment).toHaveBeenCalled();
    const comment = context._calls.createComment[0].body;
    expect(comment).toContain('assigned to this issue');
  });

  test('does not assign user to closed issue', async () => {
    const context = makeContext({ issue: { state: 'closed', assignees: [] } });
    await handleAssign(context, context.payload.issue, 'alice');
    expect(context.octokit.issues.addAssignees).not.toHaveBeenCalled();
    const comment = context._calls.createComment[0].body;
    expect(comment).toContain('already closed');
  });

  test('does not assign user already assigned', async () => {
    const context = makeContext({ issue: { state: 'open', assignees: [{ login: 'alice' }] } });
    await handleAssign(context, context.payload.issue, 'alice');
    expect(context.octokit.issues.addAssignees).not.toHaveBeenCalled();
    const comment = context._calls.createComment[0].body;
    expect(comment).toContain('already assigned');
  });

  test('does not assign when max assignees reached', async () => {
    const context = makeContext({
      issue: {
        state: 'open',
        assignees: [{ login: 'bob' }, { login: 'carol' }, { login: 'dave' }],
      },
    });
    await handleAssign(context, context.payload.issue, 'alice');
    expect(context.octokit.issues.addAssignees).not.toHaveBeenCalled();
    const comment = context._calls.createComment[0].body;
    expect(comment).toContain('maximum number of assignees');
  });

  test('does not assign on pull requests', async () => {
    const context = makeContext({ issue: { state: 'open', assignees: [], pull_request: {} } });
    await handleAssign(context, context.payload.issue, 'alice');
    expect(context.octokit.issues.addAssignees).not.toHaveBeenCalled();
    const comment = context._calls.createComment[0].body;
    expect(comment).toContain('pull requests');
  });
});

describe('handleUnassign', () => {
  function makeContext(overrides = {}) {
    const calls = { addAssignees: [], createComment: [], removeAssignees: [] };
    const context = {
      repo: () => ({ owner: 'OWASP-BLT', repo: 'TestRepo' }),
      issue: (params) => ({ owner: 'OWASP-BLT', repo: 'TestRepo', issue_number: 1, ...params }),
      octokit: {
        issues: {
          addAssignees: jest.fn(async (p) => calls.addAssignees.push(p)),
          removeAssignees: jest.fn(async (p) => calls.removeAssignees.push(p)),
          createComment: jest.fn(async (p) => calls.createComment.push(p)),
        },
      },
      payload: {
        issue: {
          number: 1,
          state: 'open',
          assignees: [{ login: 'alice' }],
          ...overrides.issue,
        },
      },
      _calls: calls,
    };
    return context;
  }

  test('removes user from assigned issue', async () => {
    const context = makeContext();
    await handleUnassign(context, context.payload.issue, 'alice');
    expect(context.octokit.issues.removeAssignees).toHaveBeenCalledWith(
      expect.objectContaining({ assignees: ['alice'] })
    );
    const comment = context._calls.createComment[0].body;
    expect(comment).toContain('unassigned');
  });

  test('does not remove user not assigned', async () => {
    const context = makeContext({ issue: { assignees: [] } });
    await handleUnassign(context, context.payload.issue, 'alice');
    expect(context.octokit.issues.removeAssignees).not.toHaveBeenCalled();
    const comment = context._calls.createComment[0].body;
    expect(comment).toContain('not currently assigned');
  });
});
