'use strict';

const { handleIssueComment } = require('./src/handlers/issue-assign');
const { handleIssueOpened, handleIssueLabeled } = require('./src/handlers/issue-opened');
const { handlePullRequestOpened, handlePullRequestClosed } = require('./src/handlers/pull-request');

/**
 * BLT GitHub App - Integrates BLT services into GitHub.
 *
 * Features:
 * - /assign and /unassign commands on issues
 * - Automatic bug reporting to BLT API when issues are labeled as 'bug'
 * - Welcome messages for new issues and pull requests
 * - Merge congratulation messages
 *
 * @param {import('probot').Probot} app
 */
module.exports = (app) => {
  app.log.info('BLT GitHub App is running!');

  // Handle issue comments for /assign and /unassign commands
  app.on('issue_comment.created', handleIssueComment);

  // Handle new issues
  app.on('issues.opened', handleIssueOpened);

  // Handle issue labeling (report to BLT when labeled as bug/vulnerability)
  app.on('issues.labeled', handleIssueLabeled);

  // Handle new pull requests
  app.on('pull_request.opened', handlePullRequestOpened);

  // Handle merged/closed pull requests
  app.on('pull_request.closed', handlePullRequestClosed);
};
