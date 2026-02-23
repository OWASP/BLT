'use strict';

/**
 * Handle pull_request opened events. Post a BLT welcome message.
 * @param {import('probot').Context} context
 */
async function handlePullRequestOpened(context) {
  const pr = context.payload.pull_request;
  const sender = context.payload.sender;

  if (!isHumanUser(sender)) return;

  const body = `👋 Thanks for opening this pull request, @${sender.login}!\n\n` +
    `**Before your PR is reviewed, please ensure:**\n` +
    `- [ ] Your code follows the project's coding style and guidelines.\n` +
    `- [ ] You have written or updated tests for your changes.\n` +
    `- [ ] The commit messages are clear and descriptive.\n` +
    `- [ ] You have linked any relevant issues (e.g., \`Closes #123\`).\n\n` +
    `🔍 Our team will review your PR shortly. If you have questions, feel free to ask in the comments.\n\n` +
    `🚀 Keep up the great work! — [OWASP BLT](https://owaspblt.org)`;

  await context.octokit.issues.createComment(context.issue({ body }));
}

/**
 * Handle pull_request closed events. If the PR was merged and linked to issues, acknowledge.
 * @param {import('probot').Context} context
 */
async function handlePullRequestClosed(context) {
  const pr = context.payload.pull_request;
  const sender = context.payload.sender;

  if (!pr.merged) return;
  if (!isHumanUser(sender)) return;

  const body = `🎉 PR merged! Thanks for your contribution, @${pr.user.login}!\n\n` +
    `Your work is now part of the project. Keep contributing to [OWASP BLT](https://owaspblt.org) ` +
    `and help make the web a safer place! 🛡️`;

  await context.octokit.issues.createComment(context.issue({ body }));
}

/**
 * Check if the user is a human (not a bot or app).
 * @param {Object} user
 * @returns {boolean}
 */
function isHumanUser(user) {
  return !!(user && (user.type === 'User' || user.type === 'Mannequin'));
}

module.exports = { handlePullRequestOpened, handlePullRequestClosed };
