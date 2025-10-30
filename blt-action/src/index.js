const core = require('@actions/core');
const github = require('@actions/github');
const axios = require('axios');

const run = async () => {
    try {
        console.log("Starting GitHub Action...");

        // Get necessary inputs
        const gitHubToken = core.getInput('repo-token', { required: true });
        const giphyApiKey = core.getInput('giphy-api-key', { required: true });
        const octokit = github.getOctokit(gitHubToken);

        const { eventName, payload, repo } = github.context;
        const { issue, comment, pull_request } = payload;
        const repository = `${repo.owner}/${repo.repo}`;
        const [owner, repoName] = repository.split('/');

        console.log(`Processing event: ${eventName} in repository ${repository}`);

        // Assignment keywords
        const assignKeywords = ['/assign', 'assign to me', 'assign this to me', 'assign it to me', 'assign me this', 'work on this', 'i can try fixing this', 'i am interested in doing this', 'be assigned this', 'i am interested in contributing'];
        const unassignKeywords = ['/unassign'];
        const giphyKeyword = '/giphy';
        const kudosKeyword = '/kudos';

        if ((eventName === 'issue_comment' && issue && comment) || (eventName === 'pull_request_review_comment' && pull_request && comment)) {
            console.log('Processing comment...');
            const commentBody = comment.body.toLowerCase();
            const shouldAssign = assignKeywords.some(keyword => commentBody.includes(keyword));
            const shouldUnassign = unassignKeywords.some(keyword => commentBody.startsWith(keyword));
            const shouldGiphy = commentBody.startsWith(giphyKeyword);
            const shouldKudos = commentBody.startsWith(kudosKeyword);

            if (shouldUnassign) {
                console.log(`Unassigning issue #${issue.number} from ${comment.user.login}`);

                try {
                    // Fetch issue details
                    const issueDetails = await octokit.issues.get({
                        owner,
                        repo: repoName,
                        issue_number: issue.number
                    });

                    const hasAssignedLabel = issueDetails.data.labels.some(label => label.name === "assigned");

                    if (hasAssignedLabel) {
                        await octokit.issues.removeAssignees({
                            owner,
                            repo: repoName,
                            issue_number: issue.number,
                            assignees: [comment.user.login]
                        });

                        await octokit.issues.removeLabel({
                            owner,
                            repo: repoName,
                            issue_number: issue.number,
                            name: "assigned"
                        }).catch(() => console.log("Label already removed or not found."));

                        // Check existing comments to avoid duplicates
                        const existingComments = await octokit.issues.listComments({
                            owner,
                            repo: repoName,
                            issue_number: issue.number
                        });

                        const unassignMessageExists = existingComments.data.some(comment =>
                            comment.body.includes('⏰ This issue has been automatically unassigned from  due to 24 hours of inactivity.') ||
                            comment.body.includes('You have been unassigned from this issue.')
                        );

                        if (!unassignMessageExists) {
                            await octokit.issues.createComment({
                                owner,
                                repo: repoName,
                                issue_number: issue.number,
                                body: `You have been unassigned from this issue. It’s now open for others. You can reassign it anytime by typing /assign.`
                            });
                        }
                    } else {
                        console.log(`Issue #${issue.number} does not have the "assigned" label, skipping unassign.`);
                    }
                } catch (error) {
                    console.error(`Error unassigning issue #${issue.number}:`, error);
                }
            }

            if (shouldAssign) {
                console.log(`Assigning issue #${issue.number} to ${comment.user.login}`);
                try {
                    const assigneeLogin = comment.user.login;

                    // Get assigned issues
                    const assignedIssues = await octokit.paginate(octokit.issues.listForRepo, {
                        owner,
                        repo: repoName,
                        state: 'open',
                        assignee: assigneeLogin
                    });

                    // Check if user has unresolved issues without a PR
                    let issuesWithoutPR = [];
                    for (const assignedIssue of assignedIssues) {
                        if (assignedIssue.number === issue.number) continue;

                        const query = `repo:${owner}/${repoName} is:pr is:open ${assignedIssue.number} in:body`;
                        const pullRequests = await octokit.search.issuesAndPullRequests({ q: query });

                        if (pullRequests.data.total_count === 0) {
                            console.log(`Issue #${assignedIssue.number} does not have an open pull request`);
                            issuesWithoutPR.push(assignedIssue.number);
                        }
                    }

                    if (issuesWithoutPR.length > 0) {
                        const issueList = issuesWithoutPR.join(', #');
                        await octokit.issues.createComment({
                            owner,
                            repo: repoName,
                            issue_number: issue.number,
                            body: `You cannot be assigned to this issue because you are already assigned to the following issues without an open pull request: #${issueList}. Please submit a pull request for these issues before getting assigned to a new one.`
                        });
                        return;
                    }

                    // Assign user to the issue
                    await octokit.issues.addAssignees({
                        owner,
                        repo: repoName,
                        issue_number: issue.number,
                        assignees: [assigneeLogin]
                    });

                    // Add "assigned" label
                    await octokit.issues.addLabels({
                        owner,
                        repo: repoName,
                        issue_number: issue.number,
                        labels: ["assigned"]
                    });

                    await octokit.issues.createComment({
                        owner,
                        repo: repoName,
                        issue_number: issue.number,
                        body: `Hello @${assigneeLogin}! You've been assigned to [${repository} issue #${issue.number}](https://github.com/${repository}/issues/${issue.number}). You have 24 hours to complete a pull request.`
                    });

                } catch (error) {
                    console.error(`Error assigning issue #${issue.number}:`, error);
                }
            } else if (shouldGiphy) {
                const searchText = commentBody.replace(giphyKeyword, '').trim();
                const giphyResponse = await axios.get(`https://api.giphy.com/v1/gifs/search?api_key=${giphyApiKey}&q=${searchText}&limit=1`);
                const gifUrl = giphyResponse.data.data[0]?.images?.original?.url;

                if (gifUrl) {
                    await octokit.issues.createComment({
                        owner,
                        repo: repoName,
                        issue_number: issue ? issue.number : pull_request.number,
                        body: `![Giphy GIF](${gifUrl})`
                    });
                } else {
                    await octokit.issues.createComment({
                        owner,
                        repo: repoName,
                        issue_number: issue ? issue.number : pull_request.number,
                        body: `No GIFs found for "${searchText}".`
                    });
                }
            } else if (shouldKudos) {
                const kudosCommand = comment.body.trim().split(/\s+/);
                if (kudosCommand.length >= 2) {
                    const sender = comment.user.login; // GitHub username of the commenter
                    const receiver = kudosCommand[1]; // Receiver from the command
                    const kudosComment = kudosCommand.slice(2).join(' ') || 'awesome work'; // Optional comment

                    console.log(`Sending kudos from ${sender} to ${receiver} with comment: "${kudosComment}"`);

                    try {
                        // Send kudos to the API
                        await axios.post('https://owaspblt.org/teams/give-kudos/', {
                            kudosReceiver: receiver,
                            kudosSender: sender,
                            comment: kudosComment
                        });

                        // Confirm success in the issue or PR comment
                        await octokit.issues.createComment({
                            owner,
                            repo: repoName,
                            issue_number: issue ? issue.number : pull_request.number,
                            body: `🎉 Kudos from @${sender} to @${receiver}! 🎉\n\n${kudosComment}\n\n✅ Kudos successfully sent to the team API!`
                        });
                    } catch (apiError) {
                        console.error('Error sending kudos to the API:', apiError);
                        await octokit.issues.createComment({
                            owner,
                            repo: repoName,
                            issue_number: issue ? issue.number : pull_request.number,
                            body: `⚠️ Failed to send kudos to the team API. Please try again later.`
                        });
                    }
                } else {
                    console.log('Invalid /kudos command format.');
                    await octokit.issues.createComment({
                        owner,
                        repo: repoName,
                        issue_number: issue ? issue.number : pull_request.number,
                        body: `⚠️ Invalid /kudos command format. Use: \`/kudos receiver comment(optional)\``
                    });
                }
            }
        }

        console.log('Checking for stale assignments...');
        const presentDate = new Date();

        try {
            const events = await octokit.paginate(octokit.issues.listEventsForRepo, {
                owner,
                repo: repoName,
                per_page: 100,
            }, response => response.data.filter(event => event.event === "assigned"));

            for (const event of events) {
                if (event.issue.assignee && event.issue.state === "open") {
                    const timeSinceUpdate = presentDate.getTime() - new Date(event.issue.updated_at).getTime();
                    const daysInactive = timeSinceUpdate / (1000 * 3600 * 24);

                    if (daysInactive > 1) {
                        console.log(`Unassigning issue #${event.issue.number} due to inactivity`);
                        try { 
                          const timelineEvents = await octokit.paginate(octokit.issues.listEventsForTimeline, {
                            owner,
                            repo: repoName,
                            issue_number: event.issue.number,
                            per_page: 100,
                          });

                          const hasOpenLinkedPR = timelineEvents.some(e =>
                            e.event === "cross-referenced" &&
                            e.source &&
                            e.source.issue &&
                            e.source.issue.pull_request &&
                            e.source.issue.state === "open"
                          );
                          if (hasOpenLinkedPR) {
                              console.log(`Issue #${event.issue.number} has an open pull request (cross-referenced), skipping unassign.`);
                              continue; 
                          }
                        } catch (searchError) {
                          console.log(`Error checking for open pull requests for issue #${event.issue.number}:`, searchError);
                        }
                        
                        const issueDetails = await octokit.issues.get({
                            owner,
                            repo: repoName,
                            issue_number: event.issue.number
                        });

                        const hasAssignedLabel = issueDetails.data.labels.some(label => label.name === "assigned");

                        if (hasAssignedLabel) {
                            await octokit.issues.removeAssignees({
                                owner,
                                repo: repoName,
                                issue_number: event.issue.number,
                                assignees: [event.issue.assignee.login]
                            });

                            await octokit.issues.removeLabel({
                                owner,
                                repo: repoName,
                                issue_number: event.issue.number,
                                name: "assigned"
                            });

                            await octokit.issues.createComment({
                                owner,
                                repo: repoName,
                                issue_number: event.issue.number,
                                body: `⏰ This issue has been automatically unassigned from ${event.issue.assignee.login} due to 24 hours of inactivity. The issue is now available for anyone to work on again.`
                            });
                        } else {
                            console.log(`Issue #${event.issue.number} does not have the "assigned" label, skipping unassign.`);
                        }
                    }
                }
            }
        } catch (error) {
            console.error("Error processing stale assignments:", error);
        }

    } catch (error) {
        console.error("Critical error in GitHub Action:", error);
    }
};

run();
