"""Utility functions for PR parsing and analysis"""

import re
from datetime import datetime, timezone

# Score multiplier when changes are requested
# Reduces overall readiness score by 50% when reviewers request changes
_CHANGES_REQUESTED_SCORE_MULTIPLIER = 0.5

# Score multiplier when PR has merge conflicts
# Reduces overall readiness score by 33% when mergeable state is 'dirty' (conflicts)
_MERGE_CONFLICTS_SCORE_MULTIPLIER = 0.67


def parse_pr_url(pr_url):
    """
    Parse GitHub PR URL to extract owner, repo, and PR number.
    
    Security Hardening (Issue #45):
    - Type validation to prevent type confusion attacks
    - Anchored regex pattern to block malformed URLs with trailing junk
    - Raises ValueError instead of returning None for better error handling
    """
    # FIX Issue #45: Type validation
    if not isinstance(pr_url, str):
        raise ValueError("PR URL must be a string")
    
    if not pr_url:
        raise ValueError("PR URL is required")
    
    pr_url = pr_url.strip().rstrip('/')
    
    # FIX Issue #45: Anchored regex - must match EXACTLY, no trailing junk allowed
    pattern = r'^https?://github\.com/([^/]+)/([^/]+)/pull/(\d+)$'
    match = re.match(pattern, pr_url)
    
    if not match:
        # FIX Issue #45: Raise error instead of returning None
        raise ValueError("Invalid GitHub PR URL. Format: https://github.com/OWNER/REPO/pull/NUMBER")
    
    return {
        'owner': match.group(1),
        'repo': match.group(2),
        'pr_number': int(match.group(3))
    }


def parse_repo_url(url):
    """Parse GitHub Repo URL to extract owner and repo name"""
    if not url: return None
    url = url.strip().rstrip('/')
    pattern = r'https?://github\.com/([^/]+)/([^/]+)(?:/.*)?$'
    match = re.match(pattern, url)
    if match:
        return {
            'owner': match.group(1),
            'repo': match.group(2)
        }
    return None


def calculate_review_status(reviews_data):
    """
    Calculate overall review status from reviews data.
    
    Args:
        reviews_data: List of review objects from GitHub API
        
    Returns:
        str: 'pending', 'approved', or 'changes_requested'
    """
    review_status = 'pending'
    if reviews_data:
        # Filter out reviews without submitted_at and sort by timestamp
        valid_reviews = [r for r in reviews_data if r.get('submitted_at')]
        sorted_reviews = sorted(valid_reviews, key=lambda x: x.get('submitted_at', ''))
        latest_reviews = {}
        for review in sorted_reviews:
            # Safely access user field - can be null for deleted accounts
            user = review.get('user')
            if user and user.get('login'):
                latest_reviews[user['login']] = review['state']

        # Determine overall status: changes_requested takes precedence over approved
        if 'CHANGES_REQUESTED' in latest_reviews.values():
            review_status = 'changes_requested'
        elif 'APPROVED' in latest_reviews.values():
            review_status = 'approved'
    
    return review_status


def parse_github_timestamp(timestamp_str):
    """Parse GitHub ISO 8601 timestamp to datetime object"""
    try:
        # GitHub timestamps are in format: 2024-01-15T10:30:45Z
        return datetime.strptime(timestamp_str.replace('Z', '+00:00'), '%Y-%m-%dT%H:%M:%S%z')
    except Exception as exc:
        # Raise error instead of silently using current time to avoid incorrect event ordering
        raise ValueError(f"Invalid GitHub timestamp: {timestamp_str!r}") from exc


def build_pr_timeline(timeline_data):
    """
    Build unified chronological timeline from PR events
    
    Args:
        timeline_data: Dict with commits, reviews, review_comments, issue_comments
    
    Returns:
        List of event dicts sorted by timestamp:
        {
            'type': 'commit' | 'review' | 'review_comment' | 'issue_comment',
            'timestamp': datetime object,
            'author': str,
            'data': dict with event-specific data
        }
    """
    events = []
    
    # Process commits
    for commit in timeline_data.get('commits', []):
        try:
            commit_data = commit.get('commit', {})
            author_data = commit_data.get('author', {})
            
            events.append({
                'type': 'commit',
                'timestamp': parse_github_timestamp(author_data.get('date', '')),
                'author': commit.get('author', {}).get('login', author_data.get('name', 'Unknown')),
                'data': {
                    'sha': commit.get('sha', '')[:7],
                    'message': commit_data.get('message', '').split('\n')[0]  # First line only
                }
            })
        except Exception:
            continue  # Skip malformed commits
    
    # Process reviews
    for review in timeline_data.get('reviews', []):
        try:
            # Skip pending reviews
            if review.get('state') == 'PENDING':
                continue
            
            events.append({
                'type': 'review',
                'timestamp': parse_github_timestamp(review.get('submitted_at', '')),
                'author': review.get('user', {}).get('login', 'Unknown'),
                'data': {
                    'state': review.get('state', ''),  # APPROVED, CHANGES_REQUESTED, COMMENTED
                    'body': review.get('body', '')
                }
            })
        except Exception:
            continue
    
    # Process review comments (inline code comments)
    for comment in timeline_data.get('review_comments', []):
        try:
            events.append({
                'type': 'review_comment',
                'timestamp': parse_github_timestamp(comment.get('created_at', '')),
                'author': comment.get('user', {}).get('login', 'Unknown'),
                'data': {
                    'body': comment.get('body', ''),
                    'path': comment.get('path', ''),
                    'in_reply_to': comment.get('in_reply_to_id')
                }
            })
        except Exception:
            continue
    
    # Process issue comments (general PR comments)
    for comment in timeline_data.get('issue_comments', []):
        try:
            events.append({
                'type': 'issue_comment',
                'timestamp': parse_github_timestamp(comment.get('created_at', '')),
                'author': comment.get('user', {}).get('login', 'Unknown'),
                'data': {
                    'body': comment.get('body', '')
                }
            })
        except Exception:
            continue
    
    # Sort all events by timestamp
    events.sort(key=lambda x: x['timestamp'])
    
    return events


def analyze_review_progress(timeline, pr_author):
    """
    Analyze review feedback loops and author responsiveness
    
    Args:
        timeline: List of timeline events from build_pr_timeline()
        pr_author: GitHub login of PR author
    
    Returns:
        Dict with:
        {
            'feedback_loops': List of feedback/response pairs,
            'total_feedback_count': int,
            'responded_count': int,
            'response_rate': float (0-1),
            'awaiting_author': bool,
            'awaiting_reviewer': bool,
            'stale_feedback': List of unaddressed feedback,
            'latest_review_state': str or None,
            'last_reviewer_action': datetime or None,
            'last_author_action': datetime or None
        }
    """
    feedback_loops = []
    latest_review_state = None
    last_reviewer_action = None
    last_author_action = None
    
    # Iterate through timeline to detect feedback patterns
    for event in timeline:
        author = event['author']
        timestamp = event['timestamp']
        event_type = event['type']
        
        # Track reviewer actions (reviews and comments from non-authors)
        if event_type in ['review', 'review_comment'] and author != pr_author:
            last_reviewer_action = timestamp
            
            # Update latest review state
            if event_type == 'review':
                latest_review_state = event['data'].get('state', '')
            
            # Create feedback loop entry
            feedback_loops.append({
                'reviewer': author,
                'feedback_time': timestamp,
                'feedback_type': event_type,
                'author_responded': False,
                'response_time': None,
                'response_type': None,
                'response_delay_hours': None
            })
        
        # Track author actions (commits and comments from author)
        elif author == pr_author and event_type in ['commit', 'issue_comment', 'review_comment']:
            last_author_action = timestamp
            
            # Check if this responds to pending feedback
            # Match to the most recent unresponded feedback
            for loop in reversed(feedback_loops):
                if not loop['author_responded'] and loop['feedback_time'] < timestamp:
                    loop['author_responded'] = True
                    loop['response_time'] = timestamp
                    loop['response_type'] = event_type
                    
                    # Calculate delay in hours
                    delay = (timestamp - loop['feedback_time']).total_seconds() / 3600
                    loop['response_delay_hours'] = round(delay, 1)
                    break
    
    # Calculate response metrics
    total_feedback = len(feedback_loops)
    responded_count = sum(1 for loop in feedback_loops if loop['author_responded'])
    response_rate = responded_count / total_feedback if total_feedback > 0 else 1.0
    
    # Determine current state
    awaiting_author = (
        latest_review_state == 'CHANGES_REQUESTED' or
        (last_reviewer_action and 
         (not last_author_action or last_reviewer_action > last_author_action))
    )
    
    awaiting_reviewer = (
        not awaiting_author and
        last_author_action and
        (not last_reviewer_action or last_author_action > last_reviewer_action)
    )
    
    # Find stale feedback (older than 3 days without response)
    now = datetime.now(timezone.utc)
    stale_threshold_hours = 72  # 3 days
    
    stale_feedback = []
    for loop in feedback_loops:
        if not loop['author_responded']:
            hours_old = (now - loop['feedback_time']).total_seconds() / 3600
            if hours_old > stale_threshold_hours:
                stale_feedback.append({
                    'reviewer': loop['reviewer'],
                    'feedback_type': loop['feedback_type'],
                    'days_old': round(hours_old / 24, 1)
                })
    
    return {
        'feedback_loops': feedback_loops,
        'total_feedback_count': total_feedback,
        'responded_count': responded_count,
        'response_rate': response_rate,
        'awaiting_author': awaiting_author,
        'awaiting_reviewer': awaiting_reviewer,
        'stale_feedback': stale_feedback,
        'latest_review_state': latest_review_state,
        'last_reviewer_action': last_reviewer_action.isoformat() if last_reviewer_action else None,
        'last_author_action': last_author_action.isoformat() if last_author_action else None
    }


def classify_review_health(review_data):
    """
    Classify review health and assign score (0-100)
    
    Args:
        review_data: Output from analyze_review_progress()
    
    Returns:
        Tuple of (classification: str, score: int)
        
        Classifications:
        - APPROVED: 90-100 - Reviews approved
        - ACTIVE: 70-85 - Good progress, responsive
        - AWAITING_REVIEWER: 60-80 - Waiting on reviewers
        - AWAITING_AUTHOR: 35-55 - Needs author response
        - STALLED: 10-30 - No activity or unaddressed feedback
        - NO_ACTIVITY: 50 - No reviews or feedback yet
    """
    response_rate = review_data['response_rate']
    stale_count = len(review_data['stale_feedback'])
    awaiting_author = review_data['awaiting_author']
    awaiting_reviewer = review_data['awaiting_reviewer']
    latest_state = review_data['latest_review_state']
    total_feedback = review_data['total_feedback_count']
    
    # No feedback yet
    if total_feedback == 0:
        return ('NO_ACTIVITY', 50)
    
    # Approved state
    if latest_state == 'APPROVED':
        return ('APPROVED', 95)
    
    # Stalled (has stale feedback)
    if stale_count > 0:
        # More stale feedback = lower score
        score = max(10, 50 - (stale_count * 15))
        return ('STALLED', score)
    
    # Awaiting author with poor response rate
    if awaiting_author and response_rate < 0.5:
        classification = 'AWAITING_AUTHOR'
        score = 35
    # Awaiting author with good response rate
    elif awaiting_author:
        classification = 'AWAITING_AUTHOR'
        score = 55
    # Awaiting reviewer
    elif awaiting_reviewer:
        # Higher score if author has been responsive
        classification = 'AWAITING_REVIEWER'
        score = 70 + int(response_rate * 10)
        score = min(score, 80)
    # Active (good back and forth)
    elif response_rate > 0.7:
        classification = 'ACTIVE'
        score = 85
    # Default active state
    else:
        classification = 'ACTIVE'
        score = 70
    
    # Apply penalty if changes were requested
    if latest_state == 'CHANGES_REQUESTED':
        score = max(0, score - 10)
    
    return (classification, score)


def calculate_ci_confidence(checks_passed, checks_failed, checks_skipped):
    """
    Calculate CI confidence score from check results
    
    Args:
        checks_passed: Number of passing checks
        checks_failed: Number of failing checks
        checks_skipped: Number of skipped checks
    
    Returns:
        int: Confidence score 0-100
    """
    total_checks = checks_passed + checks_failed + checks_skipped
    
    # No checks = neutral score
    if total_checks == 0:
        return 50
    
    # All failed = 0
    if checks_passed == 0 and checks_failed > 0:
        return 0
    
    # All passed = 100
    if checks_failed == 0 and checks_passed > 0:
        return 100
    
    # Calculate based on pass rate, penalize failures more than skipped
    pass_rate = checks_passed / total_checks
    fail_rate = checks_failed / total_checks
    skip_rate = checks_skipped / total_checks
    
    # Weighted score: passes add, failures subtract (reduced for flaky test tolerance), skips slightly reduce
    score = (pass_rate * 100) - (fail_rate * 50) - (skip_rate * 20)
    
    return max(0, min(100, int(score)))


def calculate_pr_readiness(pr_data, review_classification, review_score):
    """
    Calculate overall PR readiness combining CI and review health
    
    Args:
        pr_data: Dict with PR info including CI checks
        review_classification: str from classify_review_health
        review_score: int from classify_review_health
    
    Returns:
        Dict with:
        {
            'overall_score': int 0-100,
            'ci_score': int 0-100,
            'review_score': int 0-100,
            'classification': str,
            'merge_ready': bool,
            'blockers': List[str],
            'warnings': List[str],
            'recommendations': List[str]
        }
    """
    # Calculate CI score
    ci_score = calculate_ci_confidence(
        pr_data.get('checks_passed', 0),
        pr_data.get('checks_failed', 0),
        pr_data.get('checks_skipped', 0)
    )
    
    # Weighted combination: 45% CI, 55% Review (reduced CI weight due to flaky tests)
    overall_score_raw = (ci_score * 0.45) + (review_score * 0.55)
    
    # Reduce readiness by 50% when changes are requested
    if review_classification == 'AWAITING_AUTHOR':
        overall_score_raw *= _CHANGES_REQUESTED_SCORE_MULTIPLIER
    
    # Reduce readiness by 33% when PR has merge conflicts.
    # Note: this multiplier compounds with other score multipliers (e.g. changes
    # requested), so a PR with both conditions would be scaled by
    # 0.5 * 0.67 = 0.335 (~66.5% total reduction).
    mergeable_state = pr_data.get('mergeable_state', '')
    if mergeable_state == 'dirty':
        overall_score_raw *= _MERGE_CONFLICTS_SCORE_MULTIPLIER
    
    overall_score = int(overall_score_raw)
    
    # Force score to 0% for Draft PRs
    is_draft = pr_data.get('is_draft') == 1 or pr_data.get('is_draft') == True
    if is_draft:
        overall_score = 0
    
    # Deduct 3 points for each open conversation
    open_conversations_count = pr_data.get('open_conversations_count', 0)
    if open_conversations_count > 0:
        overall_score = max(0, overall_score - (open_conversations_count * 3))
    
    # Identify blockers, warnings, recommendations
    blockers = []
    warnings = []
    recommendations = []
    
    # Draft blocker
    if is_draft:
        blockers.append("PR is in draft mode")
        recommendations.append("Convert to 'Ready for review' when finished")
    
    # CI blockers (with tolerance for 1-2 flaky test failures)
    checks_failed = pr_data.get('checks_failed', 0)
    checks_skipped = pr_data.get('checks_skipped', 0)
    
    if checks_failed > 2:
        blockers.append(f"{checks_failed} CI check(s) failing")
        recommendations.append("Fix failing CI checks before merging")
    elif checks_failed > 0:
        warnings.append(f"{checks_failed} CI check(s) failing (possibly flaky tests)")
        recommendations.append("Verify if failures are from known flaky tests (Selenium, Docker)")
    
    if checks_skipped > 0:
        warnings.append(f"{checks_skipped} CI check(s) skipped")
    
    # Review blockers
    if review_classification == 'AWAITING_AUTHOR':
        blockers.append("Awaiting author response to feedback")
        recommendations.append("Address reviewer comments and push updates")
    
    if review_classification == 'STALLED':
        blockers.append("PR has stale unaddressed feedback")
        recommendations.append("Review and respond to old comments")
    
    if review_classification == 'NO_ACTIVITY':
        warnings.append("No review activity yet")
        recommendations.append("Request reviews from maintainers")
    
    if review_classification == 'AWAITING_REVIEWER':
        warnings.append("Awaiting reviewer approval")
        recommendations.append("Ping reviewers or request re-review")
    
    # PR state warnings
    if pr_data.get('state') == 'closed':
        blockers.append("PR is closed")
    
    if pr_data.get('is_merged') == 1:
        blockers.append("PR is already merged")
    
    mergeable_state = pr_data.get('mergeable_state', '')
    if mergeable_state == 'dirty':
        blockers.append("PR has merge conflicts")
        recommendations.append("Resolve merge conflicts with base branch")
    elif mergeable_state == 'blocked':
        warnings.append("PR is blocked by required status checks or reviews")
    
    # File change warnings
    files_changed = pr_data.get('files_changed', 0)
    if files_changed > 30:
        warnings.append(f"Large PR ({files_changed} files changed)")
        recommendations.append("Consider splitting into smaller PRs for easier review")
    
    # Open conversations warning
    if open_conversations_count > 0:
        warnings.append(f"{open_conversations_count} open conversation(s) unresolved")
        recommendations.append("Resolve open review conversations before merging")
    
    # Determine if merge ready
    merge_ready = (
        overall_score >= 70 and
        len(blockers) == 0 and
        review_classification in ['APPROVED', 'AWAITING_REVIEWER', 'ACTIVE']
    )
    
    # Overall classification
    if merge_ready:
        classification = 'READY_TO_MERGE'
    elif overall_score >= 60:
        classification = 'NEARLY_READY'
    elif overall_score >= 40:
        classification = 'NEEDS_WORK'
    else:
        classification = 'NOT_READY'
    
    return {
        'overall_score': overall_score,
        'ci_score': ci_score,
        'review_score': review_score,
        'classification': classification,
        'merge_ready': merge_ready,
        'blockers': blockers,
        'warnings': warnings,
        'recommendations': recommendations
    }
