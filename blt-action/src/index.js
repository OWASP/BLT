const core = require('@actions/core');
const github = require('@actions/github');
const axios = require('axios');
const { isHumanCommenter, extractUserInfo } = require('./utils');
const STALE_PR_THRESHOLD_DAYS = 60;
const CLOSED_PR_GRACE_PERIOD_MS = 12 * 60 * 60 * 1000;
const CLOSED_PR_LABEL = 'pr-closed-pending-unassign';
const CLOSED_PR_LABEL_COLOR = 'ff9800';
const CLOSED_PR_COMMENT_MARKER = '<!-- closed-pr-warning -->';

async function hasOpenLinkedPR(
    octokit,
    owner,
    repoName,
    issueNumber,
    returnDetails = false
) {
    const openPRs = [];
    const currentRepo = `${owner}/${repoName}`;
    const seen = new Set();

    const timelineEvents = await octokit.paginate(
        octokit.issues.listEventsForTimeline,
        {
            owner,
            repo: repoName,
            issue_number: issueNumber,
            per_page: 100,
            headers: {
                accept: 'application/vnd.github+json',
                'X-GitHub-Api-Version': '2022-11-28'
            }
        }
    );

    for (const e of timelineEvents) {
        if (e.event !== "cross-referenced" || !e.source?.issue?.pull_request) {
            continue;
        }

        const prNumber = e.source?.issue?.number;

        // Use the source repository from the event or assume current repo
        const sourceRepo = e.source?.repository?.full_name || currentRepo;

        // Only skip if explicitly from different repo
        if (sourceRepo !== currentRepo) continue;

        if (!prNumber || seen.has(prNumber)) continue;
        seen.add(prNumber);

        try {
            const pr = await octokit.pulls.get({
                owner,
                repo: repoName,
                pull_number: prNumber
            });

            if (pr.data.state === "open") {
                if (returnDetails) {
                    openPRs.push(pr.data);
                } else {
                    return true; // short-circuit for boolean use case
                }
            }
        } catch (err) {
            // 404 = PR deleted; safe to skip. 
            const errInfo = err?.status || err?.message || 'unknown error';
            if (err.status === 404) {
                console.log(`Skipping deleted PR #${prNumber}`);
            } else {
                console.error(`Error fetching PR #${prNumber}, skipping: ${errInfo}`);
            }
            continue;
        }
    }

    return returnDetails ? openPRs : false;
}

async function getLinkedPRsWithDetails(octokit, owner, repoName, issueNumber) {
    const allPRs = { open: [], closed: [], error: false };
    const currentRepo = `${owner}/${repoName}`;
    const seen = new Set();

    const timelineEvents = await octokit.paginate(
        octokit.issues.listEventsForTimeline,
        {
            owner,
            repo: repoName,
            issue_number: issueNumber,
            per_page: 100,
            headers: {
                accept: 'application/vnd.github+json',
                'X-GitHub-Api-Version': '2022-11-28'
            }
        }
    );

    for (const e of timelineEvents) {
        if (e.event !== "cross-referenced" || !e.source?.issue?.pull_request) {
            continue;
        }

        const prNumber = e.source?.issue?.number;
        const sourceRepo = e.source?.repository?.full_name || currentRepo;

        // Only process PRs from the same repository
        if (sourceRepo !== currentRepo) continue;
        if (!prNumber || seen.has(prNumber)) continue;
        seen.add(prNumber);

        try {
            const pr = await octokit.pulls.get({
                owner,
                repo: repoName,
                pull_number: prNumber
            });

            const prData = pr.data;
            const daysSinceUpdated = Math.floor((new Date() - new Date(prData.updated_at)) / (1000 * 3600 * 24));

            const prInfo = {
                number: prData.number,
                state: prData.state,
                author: prData.user?.login || '[deleted user]',
                created_at: prData.created_at,
                updated_at: prData.updated_at,
                age: daysSinceUpdated,
                url: prData.html_url,
                merged: prData.merged || false
            };

            if (prData.state === "open") {
                allPRs.open.push(prInfo);
            } else {
                allPRs.closed.push(prInfo);
            }
        } catch (err) {
            if (err.status !== 404) {
                console.error(`Error fetching PR #${prNumber}:`, err?.status || err?.message);
                allPRs.error = true;
            }
            continue;
        }
    }

    return allPRs;
}

async function ensureClosedPRLabel(octokit, owner, repoName) {
    try {
        await octokit.rest.issues.getLabel({ owner, repo: repoName, name: CLOSED_PR_LABEL });
    } catch (e) {
        if (e.status === 404) {
            await octokit.rest.issues.createLabel({
                owner,
                repo: repoName,
                name: CLOSED_PR_LABEL,
                color: CLOSED_PR_LABEL_COLOR,
                description: 'PR was closed, assignee will be removed after 12 hours'
            });
            console.log(`Created label: ${CLOSED_PR_LABEL}`);
        } else {
            console.log(`Failed to get label ${CLOSED_PR_LABEL} for ${owner}/${repoName}: ${e.message || e.stack}`);
            throw e;
        }
    }
}

function extractLinkedIssuesFromPRBody(prBody, currentOwner, currentRepo) {
    if (!prBody) return [];
    const regex = /(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)(?:\s*:\s*|\s+)(?:#(\d+)|https?:\/\/github\.com\/([^\/]+)\/([^\/]+)\/issues\/(\d+))/gi;
    const matches = [...prBody.matchAll(regex)];
    const issues = [];
    
    for (const match of matches) {
        if (match[1]) {
            issues.push(parseInt(match[1]));
        } else if (match[2] && match[3] && match[4]) {
            const urlOwner = match[2];
            const urlRepo = match[3];
            const issueNumber = parseInt(match[4]);
            
            if (urlOwner === currentOwner && urlRepo === currentRepo) {
                issues.push(issueNumber);
            }
        }
    }
    
    return [...new Set(issues)];
}

async function findLinkedIssuesFromTimeline(octokit, owner, repoName, prNumber) {
    try {
        const timeline = await octokit.paginate(octokit.rest.issues.listEventsForTimeline, {
            owner,
            repo: repoName,
            issue_number: prNumber,
            per_page: 100
        });
        
        const linked = new Set();
        for (const event of timeline) {
            if (event.event === 'connected' && event.issue && !event.issue.pull_request) {
                linked.add(event.issue.number);
            }
        }
        return Array.from(linked);
    } catch (e) {
        console.log(`Failed to get timeline for PR #${prNumber}: ${e.message}`);
        return [];
    }
}

async function handleClosedPR(octokit, owner, repoName, pr, attribution) {
    if (pr.merged) {
        console.log(`PR #${pr.number} was merged, no action needed`);
        return;
    }
    
    console.log(`PR #${pr.number} was closed (not merged) by @${pr.user.login}`);
    
    await ensureClosedPRLabel(octokit, owner, repoName);
    
    const bodyIssues = extractLinkedIssuesFromPRBody(pr.body, owner, repoName);
    const timelineIssues = await findLinkedIssuesFromTimeline(octokit, owner, repoName, pr.number);
    const linkedIssues = [...new Set([...bodyIssues, ...timelineIssues])];
    
    if (linkedIssues.length === 0) {
        console.log('No linked issues found');
        return;
    }
    
    console.log(`Found linked issues: ${linkedIssues.join(', ')}`);
    
    for (const issueNumber of linkedIssues) {
        try {
            const issue = await octokit.rest.issues.get({ owner, repo: repoName, issue_number: issueNumber });
            
            if (issue.data.state !== 'open') {
                console.log(`Issue #${issueNumber}: closed, skipping`);
                continue;
            }
            
            const isAssigned = issue.data.assignees.some(a => a.login === pr.user.login);
            if (!isAssigned) {
                console.log(`Issue #${issueNumber}: PR author not assigned, skipping`);
                continue;
            }
            
            await octokit.rest.issues.addLabels({
                owner,
                repo: repoName,
                issue_number: issueNumber,
                labels: [CLOSED_PR_LABEL]
            });
            
            const timestamp = new Date().toISOString();
            const commentBody = `${CLOSED_PR_COMMENT_MARKER}\n` +
                `PR Closed - Unassignment Pending\n\n` +
                `Hi @${pr.user.login},\n\n` +
                `Your PR #${pr.number} linked to this issue was closed.\n\n` +
                `You have 12 hours to open a new PR for this issue, or you'll be automatically unassigned.\n\n` +
                `If you're still working on this, simply open a new PR and this warning will be cancelled.\n\n` +
                `Timestamp: ${timestamp}${attribution}`;
            
            await octokit.rest.issues.createComment({
                owner,
                repo: repoName,
                issue_number: issueNumber,
                body: commentBody
            });
            
            console.log(`Issue #${issueNumber}: Added label and warning comment`);
        } catch (e) {
            console.log(`Failed to process issue #${issueNumber}: ${e.message}`);
        }
    }
}

async function handleOpenedPR(octokit, owner, repoName, pr, attribution) {
    console.log(`PR #${pr.number} was opened by @${pr.user.login}`);
    
    const bodyIssues = extractLinkedIssuesFromPRBody(pr.body, owner, repoName);
    const timelineIssues = await findLinkedIssuesFromTimeline(octokit, owner, repoName, pr.number);
    const linkedIssues = [...new Set([...bodyIssues, ...timelineIssues])];
    
    if (linkedIssues.length === 0) {
        console.log('No linked issues found');
        return;
    }
    
    console.log(`Found linked issues: ${linkedIssues.join(', ')}`);
    
    for (const issueNumber of linkedIssues) {
        try {
            const issue = await octokit.rest.issues.get({ owner, repo: repoName, issue_number: issueNumber });
            
            if (issue.data.state !== 'open') {
                console.log(`Issue #${issueNumber}: closed, skipping`);
                continue;
            }
            
            const hasLabel = issue.data.labels.some(l => l.name === CLOSED_PR_LABEL);
            if (!hasLabel) {
                console.log(`Issue #${issueNumber}: No pending label, skipping`);
                continue;
            }
            
            try {
                await octokit.rest.issues.removeLabel({
                    owner,
                    repo: repoName,
                    issue_number: issueNumber,
                    name: CLOSED_PR_LABEL
                });
            } catch (labelError) {
                if (labelError.status !== 404 && labelError.statusCode !== 404) {
                    throw labelError;
                }
                console.log(`Label already removed from issue #${issueNumber}`);
            }
            
            const comments = await octokit.paginate(octokit.rest.issues.listComments, {
                owner,
                repo: repoName,
                issue_number: issueNumber,
                per_page: 100
            });
            
            const sortedComments = comments.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
            const warningComment = sortedComments.find(c => c.body?.includes(CLOSED_PR_COMMENT_MARKER));
            if (warningComment) {
                await octokit.rest.issues.deleteComment({
                    owner,
                    repo: repoName,
                    comment_id: warningComment.id
                });
            }
            
            await octokit.rest.issues.createComment({
                owner,
                repo: repoName,
                issue_number: issueNumber,
                body: `New PR #${pr.number} opened. Unassignment cancelled.${attribution}`
            });
            
            console.log(`Issue #${issueNumber}: Removed label and warning, posted success comment`);
        } catch (e) {
            console.log(`Failed to process issue #${issueNumber}: ${e.message}`);
        }
    }
}

async function enforceClosedPRGracePeriod(octokit, owner, repoName, attribution) {
    console.log('Running closed PR grace period enforcement...');
    
    const issues = await octokit.paginate(octokit.rest.issues.listForRepo, {
        owner,
        repo: repoName,
        state: 'open',
        labels: CLOSED_PR_LABEL,
        per_page: 100
    });
    
    console.log(`Found ${issues.length} issues with pending unassignment`);
    
    const now = Date.now();
    
    for (const issue of issues) {
        try {
            console.log(`Processing issue #${issue.number}: ${issue.title}`);
            
            const comments = await octokit.paginate(octokit.rest.issues.listComments, {
                owner,
                repo: repoName,
                issue_number: issue.number,
                per_page: 100
            });
            
            const sortedComments = comments.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
            const warningComment = sortedComments.find(c => c.body?.includes(CLOSED_PR_COMMENT_MARKER));
            if (!warningComment) {
                console.log(`No warning comment found, removing label`);
                try {
                    await octokit.rest.issues.removeLabel({ 
                        owner, 
                        repo: repoName, 
                        issue_number: issue.number, 
                        name: CLOSED_PR_LABEL 
                    });
                } catch (labelError) {
                    if (labelError.status !== 404 && labelError.statusCode !== 404) {
                        throw labelError;
                    }
                }
                continue;
            }
            
            const commentTime = new Date(warningComment.created_at).getTime();
            const elapsed = now - commentTime;
            const hoursElapsed = (elapsed / (60 * 60 * 1000)).toFixed(1);
            
            console.log(`Warning posted ${hoursElapsed} hours ago`);
            
            if (elapsed < CLOSED_PR_GRACE_PERIOD_MS) {
                console.log(`Grace period not expired yet, skipping`);
                continue;
            }
            
            const linkedPRs = await getLinkedPRsWithDetails(octokit, owner, repoName, issue.number);
            const hasOpen = linkedPRs.open.length > 0;
            const prNumber = linkedPRs.open.length > 0 ? linkedPRs.open[0].number : null;
            const error = linkedPRs.error;
            
            if (error) {
                console.log(`API error checking for open PRs, skipping to be safe`);
                continue;
            }
            
            if (hasOpen) {
                console.log(`Found open PR #${prNumber}, removing label`);
                try {
                    await octokit.rest.issues.removeLabel({ 
                        owner, 
                        repo: repoName, 
                        issue_number: issue.number, 
                        name: CLOSED_PR_LABEL 
                    });
                } catch (labelError) {
                    if (labelError.status !== 404 && labelError.statusCode !== 404) {
                        throw labelError;
                    }
                }
                await octokit.rest.issues.deleteComment({ 
                    owner, 
                    repo: repoName, 
                    comment_id: warningComment.id 
                });
                await octokit.rest.issues.createComment({
                    owner,
                    repo: repoName,
                    issue_number: issue.number,
                    body: `Open PR #${prNumber} found. Unassignment cancelled.${attribution}`
                });
                continue;
            }
            
            console.log(`Grace period expired and no open PR, unassigning`);
            
            // Extract PR author from warning comment
            const prAuthorMatch = warningComment.body.match(/Hi @([^,]+),/);
            const prAuthor = prAuthorMatch ? prAuthorMatch[1] : null;
            
            let unassigned = false;
            if (prAuthor) {
                const isAssigned = issue.assignees.some(a => a.login === prAuthor);
                if (isAssigned) {
                    await octokit.rest.issues.removeAssignees({
                        owner,
                        repo: repoName,
                        issue_number: issue.number,
                        assignees: [prAuthor]
                    });
                    unassigned = true;
                    console.log(`Unassigned: ${prAuthor}`);
                } else {
                    console.log(`PR author ${prAuthor} not assigned to issue, skipping unassignment`);
                }
            } else {
                console.log(`Could not extract PR author from warning comment, skipping unassignment`);
            }
            
            try {
                await octokit.rest.issues.removeLabel({ 
                    owner, 
                    repo: repoName, 
                    issue_number: issue.number, 
                    name: CLOSED_PR_LABEL 
                });
            } catch (labelError) {
                if (labelError.status !== 404 && labelError.statusCode !== 404) {
                    throw labelError;
                }
            }
            await octokit.rest.issues.deleteComment({ 
                owner, 
                repo: repoName, 
                comment_id: warningComment.id 
            });
            
            const finalMessage = unassigned
                ? `Your PR was closed over 12 hours ago and no new PR was opened. You've been unassigned from this issue.\n\n` +
                `Feel free to comment /assign if you'd like to work on this again.${attribution}`
                : `Grace period expired and no new PR was opened. No assignee was removed because the original assignee could not be verified.\n\n` +
                `Feel free to comment /assign if you'd like to work on this again.${attribution}`;
            await octokit.rest.issues.createComment({
                owner,
                repo: repoName,
                issue_number: issue.number,
                body: finalMessage
            });
            
            console.log(`Unassignment complete for issue #${issue.number}`);
        } catch (e) {
            console.log(`Failed to process issue #${issue.number}: ${e.message}`);
        }
    }
    
    console.log('Closed PR grace period enforcement complete');
}

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

        const attribution = '\n\n---\n*This comment was generated by [OWASP BLT-Action](https://github.com/OWASP-BLT/BLT-Action)*';

        if (eventName === 'pull_request_target' && pull_request) {
            const action = payload.action;
            
            if (action === 'closed') {
                await handleClosedPR(octokit, owner, repoName, pull_request, attribution);
                return;
            }
            
            if (action === 'opened' || action === 'reopened') {
                await handleOpenedPR(octokit, owner, repoName, pull_request, attribution);
                return;
            }
        }

        if (eventName === 'schedule' || eventName === 'workflow_dispatch') {
            await enforceClosedPRGracePeriod(octokit, owner, repoName, attribution);
        }

        // Assignment keywords
        const assignKeywords = ['/assign', 'assign to me', 'assign this to me', 'assign it to me', 'assign me this', 'work on this', 'i can try fixing this', 'i am interested in doing this', 'be assigned this', 'i am interested in contributing'];
        const unassignKeywords = ['/unassign'];
        const giphyKeyword = '/giphy';
        const kudosKeyword = '/kudos';
        const tipKeyword = '/tip';

        if ((eventName === 'issue_comment' && issue && comment) || (eventName === 'pull_request_review_comment' && pull_request && comment)) {
            console.log('Processing comment...');
            const commentBody = comment.body.toLowerCase();
            const shouldAssign = assignKeywords.some(keyword => commentBody.includes(keyword));
            const shouldUnassign = unassignKeywords.some(keyword => commentBody.startsWith(keyword));
            const shouldGiphy = commentBody.startsWith(giphyKeyword);
            const shouldKudos = commentBody.startsWith(kudosKeyword);
            const shouldTip = commentBody.startsWith(tipKeyword);

            if ((shouldAssign || shouldUnassign) && !isHumanCommenter(comment)) {
                const { login, type } = extractUserInfo(comment);
                console.log(`Skipping command from non-user account: ${login} (type=${type})`);
                return; // Block bots and GitHub Apps from triggering assignment/unassignment
            }

            if (shouldUnassign) {
                if (!issue) {
                    console.log('Skipping /unassign: no issue context for this event.');
                    return;
                }
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
                            comment.body.includes('⏰ This issue has been automatically unassigned from') ||
                            comment.body.includes('You have been unassigned from this issue.')
                        );

                        if (!unassignMessageExists) {
                            await octokit.issues.createComment({
                                owner,
                                repo: repoName,
                                issue_number: issue.number,
                                body: `You have been unassigned from this issue. It's now open for others. You can reassign it anytime by typing \`/assign\`.${attribution}`
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
                try {
                    if (!issue) {
                        console.log('Skipping /assign: no issue context for this event.');
                        // Skip assignment - no issue context for this event
                        return;
                    }
                    
                    console.log(`Assigning issue #${issue.number} to ${comment.user.login}`);
                    const assigneeLogin = comment.user.login;

                    // Step 3: Updated assignment logic with 60-day stale PR handling
                    // Get all linked PRs (open and closed)
                    const linkedPRs = await getLinkedPRsWithDetails(octokit, owner, repoName, issue.number);

                    // Define state variables at the correct scope
                    let stalePRs = [];
                    let activePRs = [];
                    let shouldSkipNormalAssignmentCheck = false;

                    // Check for open PRs
                    if (linkedPRs.open.length > 0) {
                        stalePRs = linkedPRs.open.filter(pr => pr.age >= STALE_PR_THRESHOLD_DAYS);
                        activePRs = linkedPRs.open.filter(pr => pr.age < STALE_PR_THRESHOLD_DAYS);

                        if (activePRs.length > 0) {
                            // Block assignment - recent open PRs exist
                            const prList = activePRs.map(pr =>
                                `- #${pr.number} by @${pr.author} (${pr.age} days old)`
                            ).join('\n');

                            await octokit.issues.createComment({
                                owner,
                                repo: repoName,
                                issue_number: issue.number,
                                body: `**This issue has active open pull request(s):**\n\n${prList}\n\nPlease coordinate with the PR author(s) before taking over this issue.${attribution}`
                            });
                            return; // Block assignment
                        }

                        if (stalePRs.length > 0 && issue.assignees?.length > 0) {
                            // Mark takeover intent; perform mutations only after new-assignee eligibility checks pass.
                            shouldSkipNormalAssignmentCheck = true;
                        }
                    }

                    // Show closed PR history if exists (but only if we're proceeding with assignment)
                    if (linkedPRs.closed.length > 0) {
                        const closedList = linkedPRs.closed.map(pr => {
                            const status = pr.merged ? '✅ merged' : '❌ closed';
                            return `- #${pr.number} by @${pr.author} (${status}, ${pr.age} days ago)`;
                        }).join('\n');

                        await octokit.issues.createComment({
                            owner,
                            repo: repoName,
                            issue_number: issue.number,
                            body: `📋 **Previous work on this issue:**\n\n${closedList}\n\nPlease review the previous PR(s) to understand the context and avoid duplicate work.${attribution}`
                        });
                    }

                    // Check if we should proceed with takeover assignment (stale PRs + removed assignee)
                    if (shouldSkipNormalAssignmentCheck) {
                        // Direct assignment after removing previous assignee
                        // Get assigned issues for the new assignee
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

                            // Use the fixed helper function
                            if (!(await hasOpenLinkedPR(octokit, owner, repoName, assignedIssue.number))) {
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
                                body: `You cannot be assigned to this issue because you are already assigned to the following issues without an open pull request: #${issueList}. Please submit a pull request for these issues before getting assigned to a new one.${attribution}`
                            });
                            return; // Stop here - assignment blocked
                        }

                        // Store original assignees for potential rollback
                        const originalAssignees = issue.assignees || [];

                        try {
                            // Now it's safe to unassign previous assignee(s) (and keep label consistency)
                            await octokit.issues.removeAssignees({
                                owner,
                                repo: repoName,
                                issue_number: issue.number,
                                assignees: originalAssignees.map(a => a.login)
                            });

                            await octokit.issues.removeLabel({
                                owner,
                                repo: repoName,
                                issue_number: issue.number,
                                name: "assigned"
                            }).catch(() => console.log("Label already removed or not found."));

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

                            // Post takeover message after successful assignment
                            const prList = stalePRs.map(pr =>
                                `- #${pr.number} by @${pr.author} (${pr.age} days old, stale)`
                            ).join('\n');
                            await octokit.issues.createComment({
                                owner,
                                repo: repoName,
                                issue_number: issue.number,
                                body: `⏰ Previous assignee removed due to stale PR(s):\n\n${prList}\n\n@${assigneeLogin} is taking over.${attribution}`
                            });
                            return; // Done with assignment
                        } catch (error) {
                            console.error(`Failed to complete takeover assignment for issue #${issue.number}:`, error);

                            // Attempt to restore original state
                            try {
                                if (originalAssignees.length > 0) {
                                    // Try to reassign original assignees
                                    await octokit.issues.addAssignees({
                                        owner,
                                        repo: repoName,
                                        issue_number: issue.number,
                                        assignees: originalAssignees.map(a => a.login)
                                    });

                                    // Re-add the assigned label
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
                                        body: `⚠️ **Takeover failed**: Could not assign @${assigneeLogin} to this issue.\n\nError: ${error.message || 'Unknown error'}\n\nIssue has been restored to original assignee @${originalAssignees[0].login}.${attribution}`
                                    });
                                } else {
                                    // No original assignees - just add the label
                                    await octokit.issues.addLabels({
                                        owner,
                                        repo: repoName,
                                        issue_number: issue.number,
                                        labels: ["assigned"]
                                    }).catch(() => console.log("Label operation failed during restore"));

                                    await octokit.issues.createComment({
                                        owner,
                                        repo: repoName,
                                        issue_number: issue.number,
                                        body: `⚠️ **Takeover failed**: Could not assign @${assigneeLogin} to this issue.\n\nError: ${error.message || 'Unknown error'}\n\nIssue has been left unassigned. Please try again or contact maintainers.${attribution}`
                                    });
                                }
                            } catch (restoreError) {
                                console.error(`Failed to restore original state for issue #${issue.number}:`, restoreError);

                                // Last resort - notify about broken state
                                await octokit.issues.createComment({
                                    owner,
                                    repo: repoName,
                                    issue_number: issue.number,
                                    body: `🚨 **Critical assignment error**: Takeover failed and could not restore original state.\n\nError: ${error.message || 'Unknown error'}\nRestore error: ${restoreError.message || 'Unknown error'}\n\nPlease contact maintainers to manually fix this issue's assignment.${attribution}`
                                });
                            }
                            return; // Stop here - assignment failed
                        }
                    }

                    // NORMAL ASSIGNMENT FLOW (no stale PR takeover)
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

                        // Use the fixed helper function
                        if (!(await hasOpenLinkedPR(octokit, owner, repoName, assignedIssue.number))) {
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
                            body: `You cannot be assigned to this issue because you are already assigned to the following issues without an open pull request: #${issueList}. Please submit a pull request for these issues before getting assigned to a new one.${attribution}`
                        });
                        return; // Stop here -- assignment blocked
                    }

                    // prevent multiple assignees
                    const currentAssignees = issue.assignees || [];

                    if (currentAssignees.length > 0) {
                        const currentAssignee = currentAssignees[0].login;

                        if (currentAssignee !== assigneeLogin) {
                            console.log(`Issue #${issue.number} is already assigned to ${currentAssignee}`);

                            await octokit.issues.createComment({
                                owner,
                                repo: repoName,
                                issue_number: issue.number,
                                body: `⚠️ This issue is already assigned to @${currentAssignee}. Please pick another issue.${attribution}`
                            });

                            return; // Stop here -- assignment blocked
                        }

                        // If already assigned to the same user → proceed silently
                        console.log(`Issue #${issue.number} is already assigned to ${assigneeLogin}. Notifying user.`);
                        await octokit.issues.createComment({
                            owner,
                            repo: repoName,
                            issue_number: issue.number,
                            body: `ℹ️ You are already assigned to this issue.${attribution}`
                        });
                        return; // Stop here -- nothing to do
                    }

                    try {
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
                            body: `Hello @${assigneeLogin}! You've been assigned to [${repository} issue #${issue.number}](https://github.com/${repository}/issues/${issue.number}). You have 24 hours to complete a pull request.${attribution}`
                        });
                    } catch (error) {
                        console.error(`Failed to assign @${assigneeLogin} to issue #${issue.number}:`, error);
                        
                        // Clean up any partial changes
                        try {
                            // Remove assignee if it was partially added
                            await octokit.issues.removeAssignees({
                                owner,
                                repo: repoName,
                                issue_number: issue.number,
                                assignees: [assigneeLogin]
                            }).catch(() => { /* Ignore if not assigned */ });
                            
                            // Remove label if it was partially added
                            await octokit.issues.removeLabel({
                                owner,
                                repo: repoName,
                                issue_number: issue.number,
                                name: "assigned"
                            }).catch(() => { /* Ignore if not present */ });
                            
                            await octokit.issues.createComment({
                                owner,
                                repo: repoName,
                                issue_number: issue.number,
                                body: `⚠️ **Assignment failed**: Could not assign @${assigneeLogin} to this issue.\n\nError: ${error.message || 'Unknown error'}\n\nPlease try again or contact maintainers.${attribution}`
                            });
                        } catch (cleanupError) {
                            console.error(`Failed to clean up after assignment error for issue #${issue.number}:`, cleanupError);
                        }
                    }
                } catch (error) {
                    console.error(`Error in assignment flow${issue ? ` for issue #${issue.number}` : ''}:`, error);
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
                        body: `![Giphy GIF](${gifUrl})${attribution}`
                    });
                } else {
                    await octokit.issues.createComment({
                        owner,
                        repo: repoName,
                        issue_number: issue ? issue.number : pull_request.number,
                        body: `No GIFs found for "${searchText}".${attribution}`
                    });
                }
            } else if (shouldKudos) {
                const kudosCommand = comment.body.trim().split(/\s+/);
                if (kudosCommand.length >= 2) {
                    const sender = comment.user.login; // GitHub username of the commenter
                    let receiver = kudosCommand[1]; // Receiver from the command
                    const kudosComment = kudosCommand.slice(2).join(' ') || 'Great work!'; // Optional comment

                    // Strip @ symbol from receiver if present
                    receiver = receiver.replace(/^@/, '');

                    // Build the link to the issue or PR where kudos was given
                    const issueNumber = issue ? issue.number : pull_request.number;
                    const link = `https://github.com/${owner}/${repoName}/issues/${issueNumber}`;

                    console.log(`Sending kudos from ${sender} to @${receiver} with comment: "${kudosComment}"`);

                    // Always post kudos comment on GitHub first
                    await octokit.issues.createComment({
                        owner,
                        repo: repoName,
                        issue_number: issueNumber,
                        body: `🎉 Kudos from @${sender} to @${receiver}! 🎉\n\n> ${kudosComment}${attribution}`
                    });

                    // Try to send to BLT API (optional, won't fail if user doesn't have profile)
                    try {
                        await axios.post('https://owaspblt.org/teams/give-kudos/', {
                            kudosReceiver: receiver,
                            kudosSender: sender,
                            link: link,
                            comment: kudosComment
                        });

                        // If successful, add a follow-up comment about BLT tracking
                        await octokit.issues.createComment({
                            owner,
                            repo: repoName,
                            issue_number: issueNumber,
                            body: `✅ Kudos tracked on [BLT profile](https://owaspblt.org/profile/${receiver})!${attribution}`
                        });

                        console.log(`Kudos successfully tracked on BLT for ${receiver}`);
                    } catch (apiError) {
                        console.log(`Note: Kudos not tracked on BLT (user may not have a profile): ${apiError.message}`);

                        // Post informational message about BLT profile (only if it's a 404 or similar)
                        if (apiError.response && (apiError.response.status === 404 || apiError.response.status === 400)) {
                            await octokit.issues.createComment({
                                owner,
                                repo: repoName,
                                issue_number: issueNumber,
                                body: `💡 @${receiver} - Create a [BLT profile](https://owaspblt.org) to track all your kudos in one place!${attribution}`
                            });
                        }
                    }
                } else {
                    console.log('Invalid /kudos command format.');
                    await octokit.issues.createComment({
                        owner,
                        repo: repoName,
                        issue_number: issue ? issue.number : pull_request.number,
                        body: `⚠️ Invalid /kudos command format.\n\nUsage: \`/kudos @username [optional comment]\`\n\nExample: \`/kudos @alice Great work on the PR!\`${attribution}`
                    });
                }
            } else if (shouldTip) {
                const tipCommand = comment.body.trim().split(/\s+/);
                if (tipCommand.length >= 3) {
                    const sender = comment.user.login; // GitHub username of the commenter
                    const receiver = tipCommand[1].replace('@', ''); // Remove @ if present
                    const amount = tipCommand[2]; // Amount with $ symbol

                    // Validate amount format
                    const amountMatch = amount.match(/^\$?(\d+(?:\.\d{1,2})?)$/);
                    if (!amountMatch) {
                        await octokit.issues.createComment({
                            owner,
                            repo: repoName,
                            issue_number: issue ? issue.number : pull_request.number,
                            body: `⚠️ Invalid amount format. Use: \`/tip @username $amount\` (e.g., \`/tip @user $5\` or \`/tip @user $10.50\`)${attribution}`
                        });
                        return;
                    }

                    const amountValue = amountMatch[1];
                    const sponsorUrl = `https://github.com/sponsors/${receiver}`;

                    console.log(`Generating tip link from ${sender} to ${receiver} for $${amountValue}`);

                    try {
                        const sponsorCheckResponse = await axios.head(sponsorUrl, {
                            timeout: 8000,
                            validateStatus: () => true, // don't throw; we inspect status
                        });

                        const status = sponsorCheckResponse.status;

                        if (status === 404) {
                            await octokit.issues.createComment({
                                owner,
                                repo: repoName,
                                issue_number: issue ? issue.number : pull_request.number,
                                body: `⚠️ @${receiver} does not appear to have GitHub Sponsors enabled. Please verify the username or ask them to set up GitHub Sponsors first.\n\nLearn more: https://github.com/sponsors${attribution}`
                            });
                            return;
                        }
                        if (status < 200 || status >= 300) {
                            await octokit.issues.createComment({
                                owner,
                                repo: repoName,
                                issue_number: issue ? issue.number : pull_request.number,
                                body: `⚠️ Could not verify GitHub Sponsors for @${receiver} right now (status ${status}). Please try again later or visit ${sponsorUrl}.${attribution}`
                            });
                            return;
                        }

                        // Post success message with sponsor link
                        await octokit.issues.createComment({
                            owner,
                            repo: repoName,
                            issue_number: issue ? issue.number : pull_request.number,
                            body: `💰 **Tip Request from @${sender} to @${receiver}**\n\n` +
                                `Amount: **$${amountValue}**\n\n` +
                                `To complete this tip, please visit @${receiver}'s GitHub Sponsors page and select a one-time payment:\n\n` +
                                `🔗 [Sponsor @${receiver}](${sponsorUrl})\n\n` +
                                `*Note: GitHub Sponsors does not support automated payments via API. Please complete the transaction manually by selecting "One-time" on the sponsor page and entering your desired amount.*${attribution}`
                        });
                    } catch (error) {
                        console.error('Error processing tip command:', error);
                        await octokit.issues.createComment({
                            owner,
                            repo: repoName,
                            issue_number: issue ? issue.number : pull_request.number,
                            body: `⚠️ Failed to process tip request. Please try again later or visit https://github.com/sponsors/${receiver} directly.${attribution}`
                        });
                    }
                } else {
                    console.log('Invalid /tip command format.');
                    await octokit.issues.createComment({
                        owner,
                        repo: repoName,
                        issue_number: issue ? issue.number : pull_request.number,
                        body: `⚠️ Invalid /tip command format. Use: \`/tip @username $amount\`\n\nExample: \`/tip @contributor $10\`${attribution}`
                    });
                }
            }
        }

        // Only run stale assignment checks on scheduled events
        if (eventName !== 'schedule') {
            console.log('Skipping stale assignment checks - not a scheduled event');
            return;
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
                            // Use the new function to check for open PRs
                            const linkedPRs = await getLinkedPRsWithDetails(octokit, owner, repoName, event.issue.number);
                            const hasOpenPR = linkedPRs.open.length > 0;

                            if (hasOpenPR) {
                                console.log(`Issue #${event.issue.number} has ${linkedPRs.open.length} open PR(s), checking if any are active...`);

                                // Check if any open PRs are less than 60 days old
                                const activePRs = linkedPRs.open.filter(pr => pr.age < STALE_PR_THRESHOLD_DAYS);
                                if (activePRs.length > 0) {
                                    console.log(`Issue #${event.issue.number} has active PR(s), skipping unassign.`);
                                    continue;
                                }

                                // All open PRs are stale (60+ days) - allow unassignment
                                console.log(`All open PRs for issue #${event.issue.number} are stale (60+ days), proceeding with unassignment.`);
                            }
                        } catch (searchError) {
                            console.log(`Error checking for open pull requests for issue #${event.issue.number}:`, searchError);
                            console.log(`Skipping unassignment for issue #${event.issue.number} due to verification failure.`);
                            continue;
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
                                body: `⏰ This issue has been automatically unassigned from @${event.issue.assignee.login} due to 24 hours of inactivity without an *active* linked pull request.\n\n**Next Steps:**\n1. If you were working on this, you can reassign it by typing \`/assign\`\n2. If you have a WIP pull request, please link it to this issue\n3. The issue is now available for others to work on\n\nNote: If there's an existing PR linked to this issue that needs attention, please coordinate with the PR author.${attribution}`
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