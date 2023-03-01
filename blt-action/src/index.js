const core = require('@actions/core');
const github = require('@actions/github');

const run = async () => {
    console.log("starting");
    const gitHubToken = core.getInput('repo-token', { required: true });
    const repository = core.getInput('repository', { required: true });
    const octokit = github.getOctokit(gitHubToken);
    console.log(repository);

    const { issue, comment } = github.context.payload;

    const [owner, repo] = repository.split('/');

    if (issue) {
        console.log('processing issue');
        const assignees = comment.user.login.split(',').map((assigneeName) => assigneeName.trim());
        var addAssignee = true;

        if (comment.body.toLowerCase().includes("/unassign")) {
            var issue_number = issue.number;
            octokit.issues.removeAssignees({
                owner,
                repo,
                issue_number,
                assignees,
            })
        } else {
            await octokit.paginate(octokit.issues.listEventsForRepo, {
                owner,
                repo,
                per_page: 100,
            }, response => response.data.filter(r => r.event == "assigned")
            ).then(async (data) => {
                for (const event of data) {
                    // console.log(event.issue);
                    if (event.issue.assignee && event.issue.state == "open") {
                        if (event.issue.id == issue.id) {
                            addAssignee = false;
                            return;
                        }
                        for (var assignedUser of event.issue.assignees) {
                            if (assignedUser.login == comment.user.login) {
                                await octokit.issues.createComment({
                                    owner,
                                    repo,
                                    issue_number: issue.number,
                                    body: "You are already assigned to another [open issue](" + event.issue.html_url + "), please wait until until it's closed or remove your assignment to get assigned to this issue."
                                });
                                addAssignee = false;
                                return;
                            }
                        }
                    }
                }
            });
            if (addAssignee) {
                await octokit.issues.addAssignees({
                    owner,
                    repo,
                    issue_number: issue.number,
                    assignees,
                });
            }
        }

    } else {
        console.log('removing assignees greater than 3 days');
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

                        if (Difference_In_Time / (1000 * 3600 * 24) > 3) {
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

run();
