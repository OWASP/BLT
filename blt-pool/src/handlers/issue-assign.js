'use strict';

const ASSIGN_COMMAND = '/assign';
const UNASSIGN_COMMAND = '/unassign';
const MAX_ASSIGNEES = 3;
const ASSIGNMENT_DURATION_HOURS = 24;
const ASSIGNMENT_DURATION_MS = ASSIGNMENT_DURATION_HOURS * 60 * 60 * 1000;

/**
 * Handle issue comment events for /assign and /unassign commands.
 * @param {import('probot').Context} context
 */
async function handleIssueComment(context) {
  const comment = context.payload.comment;
  const issue = context.payload.issue;

  if (!isHumanUser(comment.user)) return;

  const body = comment.body.trim();

  if (body.startsWith(ASSIGN_COMMAND)) {
    await handleAssign(context, issue, comment.user.login);
  } else if (body.startsWith(UNASSIGN_COMMAND)) {
    await handleUnassign(context, issue, comment.user.login);
  }
}

/**
 * Assign the commenter to the issue.
 */
async function handleAssign(context, issue, login) {
  const { owner, repo } = context.repo();
  const issueNumber = issue.number;

  if (issue.pull_request) {
    await context.octokit.issues.createComment(context.issue({
      body: `@${login} This command only works on issues, not pull requests.`,
    }));
    return;
  }

  if (issue.state === 'closed') {
    await context.octokit.issues.createComment(context.issue({
      body: `@${login} This issue is already closed and cannot be assigned.`,
    }));
    return;
  }

  const currentAssignees = issue.assignees.map(a => a.login);

  if (currentAssignees.includes(login)) {
    await context.octokit.issues.createComment(context.issue({
      body: `@${login} You are already assigned to this issue.`,
    }));
    return;
  }

  if (currentAssignees.length >= MAX_ASSIGNEES) {
    await context.octokit.issues.createComment(context.issue({
      body: `@${login} This issue already has the maximum number of assignees (${MAX_ASSIGNEES}). Please work on a different issue.`,
    }));
    return;
  }

  await context.octokit.issues.addAssignees({
    owner,
    repo,
    issue_number: issueNumber,
    assignees: [login],
  });

  const deadline = new Date(Date.now() + ASSIGNMENT_DURATION_MS);
  const deadlineStr = deadline.toUTCString();

  await context.octokit.issues.createComment(context.issue({
    body: `@${login} You have been assigned to this issue! 🎉\n\n` +
      `Please submit a pull request within **${ASSIGNMENT_DURATION_HOURS} hours** (by ${deadlineStr}).\n\n` +
      `If you need more time or cannot complete the work, please comment \`${UNASSIGN_COMMAND}\` so others can pick it up.\n\n` +
      `Happy coding! 🚀 — [OWASP BLT](https://owaspblt.org)`,
  }));
}

/**
 * Unassign the commenter from the issue.
 */
async function handleUnassign(context, issue, login) {
  const { owner, repo } = context.repo();
  const issueNumber = issue.number;

  const currentAssignees = issue.assignees.map(a => a.login);

  if (!currentAssignees.includes(login)) {
    await context.octokit.issues.createComment(context.issue({
      body: `@${login} You are not currently assigned to this issue.`,
    }));
    return;
  }

  await context.octokit.issues.removeAssignees({
    owner,
    repo,
    issue_number: issueNumber,
    assignees: [login],
  });

  await context.octokit.issues.createComment(context.issue({
    body: `@${login} You have been unassigned from this issue. Thanks for letting us know! 👍\n\n` +
      `The issue is now open for others to pick up.`,
  }));
}

/**
 * Check if the user is a human (not a bot or app).
 * @param {Object} user
 * @returns {boolean}
 */
function isHumanUser(user) {
  return !!(user && (user.type === 'User' || user.type === 'Mannequin'));
}

module.exports = { handleIssueComment, handleAssign, handleUnassign, isHumanUser };
