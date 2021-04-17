const core = require('@actions/core');
const github = require('@actions/github');

const run = async () => {
    const gitHubToken = core.getInput('repo-token', { required: true });
    const octokit = github.getOctokit(gitHubToken);

    const { repository, issue, comment } = github.context.payload;
    const [owner, repo] = repository.full_name.split('/');

    if (issue) {
        console.log('processing issue');
        const assignees = comment.user.login.split(',').map((assigneeName) => assigneeName.trim());

        if (comment.body.toLowerCase().includes("/unassign")) {
            var issue_number = issue.number;
            octokit.issues.removeAssignees({
                owner,
                repo,
                issue_number,
                assignees,
            })
        } else {
            await octokit.issues.addAssignees({
                owner,
                repo,
                issue_number: issue.number,
                assignees,
            });
        }

    } else {
        console.log('removing assignees greater than 3 days');
        var last_event = new Object()
        last_event.issue = new Object()
        last_event.issue.number = "";
        var present_date = new Date();

        // options = await octokit.issues.listEventsForRepo({
        //     owner,
        //     repo,
        //     per_page: 100,
        // });

        // const repos = await octokit.paginate(
        //     octokit.repos.listForAuthenticatedUser,
        //     {
        //         per_page: 100,
        //     },
        //     response => response.data
        // )



        await octokit.paginate(

            octokit.issues.listEventsForRepo({
                owner,
                repo,
            },
                response => response.data.filter(r => r.event.event == "assigned")

            ).then((data) => {
                for (const event of data) {
                    console.log(event.event);
                    if (event.issue.assignee && event.issue.state == "open") {

                        var Difference_In_Time = present_date.getTime() - Date.parse(event.created_at);

                        console.log(
                            event.created_at + " " +
                            event.issue.number + " " +
                            event.assignee.login + " " +
                            event.issue.assignee.login + " " +
                            event.issue.state + " " +
                            (Difference_In_Time / (1000 * 3600 * 24)).toString() + " days",
                        );

                        if (last_event.issue.number != event.issue.number) {

                            if (Difference_In_Time / (1000 * 3600 * 24) > 3) {

                                var assignee = event.issue.assignee.login;
                                var issue_number = event.issue.number;

                                octokit.issues.removeAssignees({
                                    owner,
                                    repo,
                                    issue_number,
                                    assignee,
                                })
                            }
                        }
                    }
                    last_event = event;
                }
            })
        );



        // await octokit.paginate(

        //     octokit.issues.listEventsForRepo({
        //         owner,
        //         repo,
        //         per_page: 100,
        //     },
        //         response => response.data

        //     ).then(({ data }) => {
        //         for (const event of data) {
        //             console.log(event.event);
        //             if (event.event == "assigned" && event.issue.assignee && event.issue.state == "open") {

        //                 var Difference_In_Time = present_date.getTime() - Date.parse(event.created_at);

        //                 console.log(
        //                     event.created_at + " " +
        //                     event.issue.number + " " +
        //                     event.assignee.login + " " +
        //                     event.issue.assignee.login + " " +
        //                     event.issue.state + " " +
        //                     (Difference_In_Time / (1000 * 3600 * 24)).toString() + " days",
        //                 );

        //                 if (last_event.issue.number != event.issue.number) {

        //                     if (Difference_In_Time / (1000 * 3600 * 24) > 3) {

        //                         var assignee = event.issue.assignee.login;
        //                         var issue_number = event.issue.number;

        //                         octokit.issues.removeAssignees({
        //                             owner,
        //                             repo,
        //                             issue_number,
        //                             assignee,
        //                         })
        //                     }
        //                 }
        //             }
        //             last_event = event;
        //         }
        //     })
        // );



    }
}

run();
// try {
//     run();
// } catch (error) {
//     core.setFailed(error.message);
// }


