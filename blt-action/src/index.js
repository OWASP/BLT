const core = require('@actions/core');
const github = require('@actions/github');

const run = async () => {
    console.log("starting");
    const gitHubToken = core.getInput('repo-token', { required: true });
    const repository = core.getInput('repository', { required: true });
    const octokit = github.getOctokit(gitHubToken);
    console.log(repository);

    const { eventName, payload } = github.context;
    const { issue, comment } = payload;
    const [owner, repo] = repository.split('/');
    let proceedWithIssueProcessing = false; // Initialize the flag
    console.log(eventName);

    if (eventName === 'issue_comment' && issue && comment) {
        console.log('processing issue comment');
        const commentBody = comment.body.toLowerCase(); // Convert to lower case for case-insensitive comparison
        const assignKeywords = ['/assign', 'assign to me', 'assign this to me', 'please assign me this', 'i can try fixing this', 'i am interested in doing this', 'i am interested in contributing'];
        const unassignKeywords = ['/unassign'];

        const shouldAssign = assignKeywords.some(keyword => commentBody.includes(keyword));
        const shouldUnassign = unassignKeywords.some(keyword => commentBody.startsWith(keyword));

        if (shouldAssign) {
            proceedWithIssueProcessing = true; // Set flag to true
        } else if (shouldUnassign) {
            console.log(`Unassigning issue #${issue.number} from ${comment.user.login}`);
            await octokit.issues.removeAssignees({
                owner,
                repo,
                issue_number: issue.number,
                assignees: [comment.user.login]
            });
        }
    }


    if (issue && proceedWithIssueProcessing) {
        if (issue) {
            console.log('processing issue');
            const assigneeLogin = comment.user.login;
            const assignees = assigneeLogin.split(',').map(assigneeName => assigneeName.trim());
            var addAssignee = true;
            var issuesWithoutPR = [];
        
            // Retrieve all open issues assigned to the user
            const assignedIssues = await octokit.paginate(octokit.issues.listForRepo, {
                owner,
                repo,
                state: 'open',
                assignee: assigneeLogin
            });
            for (const assignedIssue of assignedIssues) {
                // Skip if it's the same issue
                if (assignedIssue.number === issue.number) {
                    continue;
                }

                // Construct a search query to find pull requests that mention the assigned issue
                const query = `type:pr state:open repo:${owner}/${repo} ${assignedIssue.number} in:body`;
                const pullRequests = await octokit.search.issuesAndPullRequests({
                    q: query
                });

                // If there are no pull requests mentioning the issue number in their body, add it to the list
                if (pullRequests.data.total_count === 0) {
                    console.log(`Issue #${assignedIssue.number} does not have an open pull request`);
                    issuesWithoutPR.push(assignedIssue.number);
                    break;
                }
            }
            if (issuesWithoutPR.length > 0) {
                addAssignee = false;
                const issueList = issuesWithoutPR.join(', #');
                await octokit.issues.createComment({
                    owner,
                    repo,
                    issue_number: issue.number,
                    body: `You cannot be assigned to this issue because you are already assigned to the following issues without an open pull request: #${issueList}. Please submit a pull request for these issues before getting assigned to a new one.`
                });
            } else if (addAssignee) {
                await octokit.issues.addAssignees({
                    owner,
                    repo,
                    issue_number: issue.number,
                    assignees
                });
            }
        } else {
            console.log('removing assignees greater than 5 days');
            var last_event = new Object()
            last_event.issue = new Object()
            last_event.issue.number = "";
            var present_date = new Date();

            await octokit.paginate(octokit.issues.listEventsForRepo, {
                owner,
                repo,
                per_page: 100,
            }, response => response.data.filter(r => r.event == "assigned")
            ).then((data) => {
                for (const event of data) {

                    if (event.issue.assignee && event.issue.state == "open") {

                        var Difference_In_Time = present_date.getTime() - Date.parse(event.created_at);

                        if (last_event.issue.number != event.issue.number) {

                            console.log(
                                event.created_at + " " +
                                event.issue.number + " " +
                                event.assignee.login + " " +
                                event.issue.assignee.login + " " +
                                event.issue.state + " " +
                                (Difference_In_Time / (1000 * 3600 * 24)).toString() + " days",
                            );

                            if ((Difference_In_Time / (1000 * 3600 * 24)) > 5) {
                                console.log('unassigning ' + event.issue.assignee.login + " from " + event.issue.number);

                                const assignees = event.issue.assignee.login.split(',').map((assigneeName) => assigneeName.trim());

                                var issue_number = event.issue.number;

                                octokit.issues.removeAssignees({
                                    owner,
                                    repo,
                                    issue_number,
                                    assignees,
                                })
                            }
                        }
                    }
                    last_event = event;
                }
            });
        }
    }
    else {
        console.log('No matching keywords found or not an issue comment event. Skipping further processing.');
    }
}

run();
