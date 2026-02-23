'use strict';

const { reportBugToBLT } = require('../blt-api');

const BUG_LABELS = ['bug', 'vulnerability', 'security'];

/**
 * Handle issue opened events. Post a welcome message and report to BLT if labeled as bug.
 * @param {import('probot').Context} context
 */
async function handleIssueOpened(context) {
  const issue = context.payload.issue;
  const sender = context.payload.sender;

  if (!isHumanUser(sender)) return;

  const labels = issue.labels.map(l => l.name.toLowerCase());
  const isBug = labels.some(l => BUG_LABELS.includes(l));

  let welcomeMessage = `👋 Thanks for opening this issue, @${sender.login}!\n\n` +
    `Our team will review it shortly. In the meantime:\n` +
    `- If you'd like to work on this issue, comment \`/assign\` to get assigned.\n` +
    `- Visit [OWASP BLT](https://owaspblt.org) for more information about our bug bounty platform.\n`;

  if (isBug) {
    const { owner, repo } = context.repo();
    const githubUrl = issue.html_url;

    const bugData = await reportBugToBLT({
      url: githubUrl,
      description: issue.title,
      githubUrl,
      label: labels[0] || 'bug',
    });

    if (bugData && bugData.id) {
      welcomeMessage += `\n🐛 This issue has been automatically reported to [OWASP BLT](https://owaspblt.org) ` +
        `(Bug ID: #${bugData.id}). Thank you for helping improve security!\n`;
    }
  }

  await context.octokit.issues.createComment(context.issue({ body: welcomeMessage }));
}

/**
 * Handle issue labeled events. When a bug label is added, report to BLT.
 * @param {import('probot').Context} context
 */
async function handleIssueLabeled(context) {
  const issue = context.payload.issue;
  const label = context.payload.label;

  if (!label || !BUG_LABELS.includes(label.name.toLowerCase())) return;

  const allLabels = issue.labels.map(l => l.name.toLowerCase());
  const otherBugLabels = allLabels.filter(l => BUG_LABELS.includes(l) && l !== label.name.toLowerCase());

  if (otherBugLabels.length > 0) return;

  const githubUrl = issue.html_url;
  const bugData = await reportBugToBLT({
    url: githubUrl,
    description: issue.title,
    githubUrl,
    label: label.name,
  });

  if (bugData && bugData.id) {
    await context.octokit.issues.createComment(context.issue({
      body: `🐛 This issue has been reported to [OWASP BLT](https://owaspblt.org) ` +
        `(Bug ID: #${bugData.id}) after being labeled as \`${label.name}\`.`,
    }));
  }
}

/**
 * Check if the user is a human (not a bot or app).
 * @param {Object} user
 * @returns {boolean}
 */
function isHumanUser(user) {
  return !!(user && (user.type === 'User' || user.type === 'Mannequin'));
}

module.exports = { handleIssueOpened, handleIssueLabeled, BUG_LABELS };
