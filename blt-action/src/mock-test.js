const nock = require('nock');
const assert = require('assert');
const axios = require('axios');

async function assignUserToIssue(owner, repo, issueNumber, username) {
  const url = `https://api.github.com/repos/${owner}/${repo}/issues/${issueNumber}/assignees`;
  const response = await axios.post(url, { assignees: [username] });
  return response.data;
}

async function postGiphyComment(owner, repo, issueNumber, searchText, giphyApiKey) {
  const giphyResponse = await axios.get(`https://api.giphy.com/v1/gifs/search?api_key=${giphyApiKey}&q=${searchText}&limit=1`);
  const gifUrl = giphyResponse.data.data[0]?.images?.original?.url;

  if (gifUrl) {
    const url = `https://api.github.com/repos/${owner}/${repo}/issues/${issueNumber}/comments`;
    const response = await axios.post(url, { body: `![Giphy GIF](${gifUrl})` });
    return response.data;
  } else {
    throw new Error(`No GIFs found for "${searchText}".`);
  }
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

  it('should post a Giphy comment on an issue', async () => {
    const owner = 'testowner';
    const repo = 'testrepo';
    const issueNumber = 1;
    const searchText = 'funny cat';
    const giphyApiKey = 'testapikey';

    const giphyScope = nock('https://api.giphy.com')
      .get(`/v1/gifs/search?api_key=${giphyApiKey}&q=${searchText}&limit=1`)
      .reply(200, {
        data: [
          {
            images: {
              original: {
                url: 'https://giphy.com/gifs/moodman-dog-confused-rigley-beans-Z5xk7fGO5FjjTElnpT'
              }
            }
          }
        ]
      });

    const githubScope = nock('https://api.github.com')
      .post(`/repos/${owner}/${repo}/issues/${issueNumber}/comments`, { body: '![Giphy GIF](https://giphy.com/gifs/moodman-dog-confused-rigley-beans-Z5xk7fGO5FjjTElnpT)' })
      .reply(201, { status: 'success' });

    const result = await postGiphyComment(owner, repo, issueNumber, searchText, giphyApiKey);
    assert.strictEqual(result.status, 'success');

    giphyScope.done();
    githubScope.done();
  });

  it('should send kudos to BLT API', async () => {
    const owner = 'testowner';
    const repo = 'testrepo';
    const issueNumber = 1;
    const sender = 'githubuser';
    const receiver = 'bltuser';
    const comment = 'Great work on the PR!';
    const link = `https://github.com/${owner}/${repo}/issues/${issueNumber}`;

    const bltScope = nock('https://owaspblt.org')
      .post('/teams/give-kudos/', {
        kudosReceiver: receiver,
        kudosSender: sender,
        link: link,
        comment: comment
      })
      .reply(201, { success: true, message: 'Kudos sent successfully!' });

    const githubScope = nock('https://api.github.com')
      .post(`/repos/${owner}/${repo}/issues/${issueNumber}/comments`)
      .reply(201, { status: 'success' });

    // Simulate the kudos sending
    await axios.post('https://owaspblt.org/teams/give-kudos/', {
      kudosReceiver: receiver,
      kudosSender: sender,
      link: link,
      comment: comment
    });

    bltScope.done();
  });
});