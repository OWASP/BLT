const nock = require('nock');
const assert = require('assert');
const axios = require('axios');

async function assignUserToIssue(owner, repo, issueNumber, username) {
  const url = `https://api.github.com/repos/${owner}/${repo}/issues/${issueNumber}/assignees`;
  const response = await axios.post(url, { assignees: [username] });
  return response.data;
}

describe('GitHub API Mock Test', () => {
  beforeEach(() => {
    nock.cleanAll();
  });

  it('should assign a user to an issue with a PR', async () => {
    const owner = 'testowner';
    const repo = 'testrepo';
    const issueNumber = 1;
    const username = 'testuser';

    const scope = nock('https://api.github.com')
      .post(`/repos/${owner}/${repo}/issues/${issueNumber}/assignees`, { assignees: [username] })
      .reply(201, { status: 'success' });

    const result = await assignUserToIssue(owner, repo, issueNumber, username);
    assert.strictEqual(result.status, 'success');

    scope.done();
  });
});