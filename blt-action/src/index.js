const core = require('@actions/core');
const github = require('@actions/github');
const fs = require('fs');
const path = require('path');

const run = async () => {
    console.log("starting");
    const gitHubToken = core.getInput('repo-token', { required: true });
    const githubOwner = github.context.repo.owner;
    const githubRepo = github.context.repo.repo;
    const repository = `${githubOwner}/${githubRepo}`;
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
        console.log('processing issue');
        const assigneeLogin = comment.user.login;
        const assignees = assigneeLogin.split(',').map(assigneeName => assigneeName.trim());

        let addAssignee = true;
        let issuesWithoutPR = [];

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
        }  if (addAssignee) {
             const currentAssignees = await octokit.issues.get({
                owner,
                repo,
                issue_number: issue.number
             });
            if (!currentAssignees.data.assignees.some(a => a.login === assigneeLogin)) {
                await octokit.issues.addAssignees({
                    owner,
                    repo,
                    issue_number: issue.number,
                    assignees
                });

                // Add the message to the issue
                await octokit.issues.createComment({
                    owner,
                    repo,
                    issue_number: issue.number,
                    body: `Hello @${assigneeLogin}! You've been assigned to [${repository} issue #${issue.number}](https://github.com/${repository}/issues/${issue.number}). You have 24 hours to complete a pull request.`
                });
            }
        }
    } else {
        console.log('Removing assignees greater than 24 hours and posting a note');

        let last_event = { issue: { number: "" } };
        let present_date = new Date();

        await octokit.paginate(octokit.issues.listEventsForRepo, {
            owner,
            repo,
            per_page: 100,
        }, response => response.data.filter(r => r.event == "assigned")
        ).then(async (data) => {
            for (const event of data) {

                if (event.issue.assignee && event.issue.state == "open") {

                    let Difference_In_Time = present_date.getTime() - Date.parse(event.issue.updated_at);

                    if (last_event.issue.number != event.issue.number) {

                        console.log(
                            event.issue.updated_at + " " +
                            event.issue.number + " " +
                            event.assignee.login + " " +
                            event.issue.assignee.login + " " +
                            event.issue.state + " " +
                            (Difference_In_Time / (1000 * 3600 * 24)).toString() + " days",
                        );

                        if ((Difference_In_Time / (1000 * 3600 * 24)) > 1) {
                            // Check if the issue has any labels
                            const issueDetails = await octokit.issues.get({
                                owner,
                                repo,
                                issue_number: event.issue.number
                            });


                            if (issueDetails.data.labels.length === 0) {
                                console.log('unassigning ' + event.issue.assignee.login + " from " + event.issue.number);

                                await octokit.issues.removeAssignees({
                                    owner,
                                    repo,
                                    issue_number: event.issue.number,
                                    assignees: [event.issue.assignee.login],
                                });

                                // Add a comment about unassignment
                                await octokit.issues.createComment({
                                    owner,
                                    repo,
                                    issue_number: event.issue.number,
                                    body: `⏰ This issue has been automatically unassigned due to 24 hours of inactivity. 
                                    The issue is now available for anyone to work on again.`
                                });
                            } else {
                                console.log(`Issue #${event.issue.number} has labels, skipping unassign.`);
                            }
                        }
                    }
                }
                last_event = event;
            }
        });
    }
}

// Function to handle symbolic links during the unwrapping process
const handleSymbolicLinks = (srcPath, destPath) => {
    if (fs.lstatSync(srcPath).isSymbolicLink()) {
        const realPath = fs.realpathSync(srcPath);
        if (fs.existsSync(realPath)) {
            fs.symlinkSync(realPath, destPath);
        } else {
            console.log(`Skipping broken symbolic link: ${srcPath}`);
        }
    } else {
        fs.copyFileSync(srcPath, destPath);
    }
};

// Example usage of handleSymbolicLinks function
const unwrap = (srcDir, destDir) => {
    fs.readdirSync(srcDir).forEach(file => {
        const srcPath = path.join(srcDir, file);
        const destPath = path.join(destDir, file);
        handleSymbolicLinks(srcPath, destPath);
    });
};

run();
