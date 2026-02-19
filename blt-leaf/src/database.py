"""Database operations for PR tracking"""

import json
from datetime import datetime, timezone


def get_db(env):
    """Helper to get DB binding from env, handling different env types.
    
    Raises an exception if database is not configured.
    """
    # Try common binding names
    for name in ['pr_tracker', 'DB']:
        # Try attribute access
        if hasattr(env, name):
            return getattr(env, name)
        # Try dict access
        if hasattr(env, '__getitem__'):
            try:
                return env[name]
            except (KeyError, TypeError):
                pass
    
    # Database not configured - raise error
    print(f"DEBUG: env attributes: {dir(env)}")
    raise Exception("Database binding 'pr_tracker' or 'DB' not found in env. Please configure a D1 database.")


async def save_readiness_to_db(env, pr_id, readiness_data):
    """Save readiness analysis results to database in the prs table.
    
    Args:
        env: Worker environment with database binding
        pr_id: PR ID
        readiness_data: Dictionary containing readiness analysis results
    """
    try:
        db = get_db(env)
        
        # Extract data from the response structure
        readiness = readiness_data.get('readiness', {})
        review_health = readiness_data.get('review_health', {})
        
        # Convert lists to JSON strings for storage
        blockers_json = json.dumps(readiness.get('blockers', []))
        warnings_json = json.dumps(readiness.get('warnings', []))
        recommendations_json = json.dumps(readiness.get('recommendations', []))
        stale_feedback_json = json.dumps(review_health.get('stale_feedback', []))
        
        # Update the existing PR row with readiness data
        stmt = db.prepare('''
            UPDATE prs SET
                overall_score = ?,
                ci_score = ?,
                review_score = ?,
                classification = ?,
                merge_ready = ?,
                blockers = ?,
                warnings = ?,
                recommendations = ?,
                review_health_classification = ?,
                review_health_score = ?,
                response_rate = ?,
                total_feedback = ?,
                responded_feedback = ?,
                stale_feedback_count = ?,
                stale_feedback = ?,
                readiness_computed_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''')
        
        await stmt.bind(
            readiness.get('overall_score'),
            readiness.get('ci_score'),
            readiness.get('review_score'),
            readiness.get('classification'),
            1 if readiness.get('merge_ready') else 0,
            blockers_json,
            warnings_json,
            recommendations_json,
            review_health.get('classification'),
            review_health.get('score'),
            review_health.get('response_rate'),
            review_health.get('total_feedback'),
            review_health.get('responded_feedback'),
            review_health.get('stale_feedback_count'),
            stale_feedback_json,
            pr_id
        ).run()
        
        print(f"Database: Saved readiness data for PR {pr_id}")
    except Exception as e:
        print(f"Error saving readiness to database for PR {pr_id}: {str(e)}")
        # Don't raise - we can continue with in-memory cache only


async def load_readiness_from_db(env, pr_id):
    """Load readiness analysis results from database (prs table).
    
    Args:
        env: Worker environment with database binding
        pr_id: PR ID
        
    Returns:
        Dictionary with complete response data including PR info and readiness, or None if not found
    """
    try:
        db = get_db(env)
        
        # Load PR data with readiness fields - explicitly select needed columns
        stmt = db.prepare('''
            SELECT id, title, author_login, repo_owner, repo_name, pr_number, 
                   state, is_merged, mergeable_state, files_changed,
                   checks_passed, checks_failed, checks_skipped,
                   overall_score, ci_score, review_score, classification, 
                   merge_ready, blockers, warnings, recommendations,
                   review_health_classification, review_health_score, 
                   response_rate, total_feedback, responded_feedback,
                   stale_feedback_count, stale_feedback,
                   readiness_computed_at
            FROM prs WHERE id = ?
        ''')
        result = await stmt.bind(pr_id).first()
        
        if not result:
            print(f"Database: PR {pr_id} not found")
            return None
        
        # Convert result to Python dict
        pr = result.to_py() if hasattr(result, 'to_py') else dict(result)
        
        # Check if readiness data exists (overall_score will be None if never computed)
        if pr.get('overall_score') is None:
            print(f"Database: No readiness data found for PR {pr_id}")
            return None
        
        # Parse JSON strings back to lists - with error handling
        try:
            blockers = json.loads(pr.get('blockers', '[]'))
        except Exception as e:
            print(f"Failed to parse blockers JSON for PR {pr_id}: {str(e)}")
            return None
        
        try:
            warnings = json.loads(pr.get('warnings', '[]'))
        except Exception as e:
            print(f"Failed to parse warnings JSON for PR {pr_id}: {str(e)}")
            return None
        
        try:
            recommendations = json.loads(pr.get('recommendations', '[]'))
        except Exception as e:
            print(f"Failed to parse recommendations JSON for PR {pr_id}: {str(e)}")
            return None
        
        try:
            stale_feedback = json.loads(pr.get('stale_feedback', '[]'))
        except Exception as e:
            print(f"Failed to parse stale_feedback JSON for PR {pr_id}: {str(e)}")
            return None
        
        # Get numeric values for display formatting
        overall_score = pr.get('overall_score', 0)
        ci_score = pr.get('ci_score', 0)
        review_score = pr.get('review_score', 0)
        response_rate = pr.get('response_rate', 0.0)
        
        # Reconstruct the complete response structure with PR info and display fields
        readiness_data = {
            'pr': {
                'id': pr['id'],
                'title': pr.get('title'),
                'author': pr.get('author_login'),
                'repo': f"{pr['repo_owner']}/{pr['repo_name']}",
                'number': pr['pr_number'],
                'state': pr.get('state'),
                'is_merged': pr.get('is_merged') == 1,
                'mergeable_state': pr.get('mergeable_state'),
                'files_changed': pr.get('files_changed')
            },
            'readiness': {
                'overall_score': overall_score,
                'overall_score_display': f"{overall_score}%",
                'ci_score': ci_score,
                'ci_score_display': f"{ci_score}%",
                'review_score': review_score,
                'review_score_display': f"{review_score}%",
                'classification': pr.get('classification'),
                'merge_ready': bool(pr.get('merge_ready')),
                'blockers': blockers,
                'warnings': warnings,
                'recommendations': recommendations
            },
            'review_health': {
                'classification': pr.get('review_health_classification'),
                'score': pr.get('review_health_score'),
                'score_display': f"{pr.get('review_health_score', 0)}%",
                'response_rate': response_rate,
                'response_rate_display': f"{int(response_rate * 100)}%",
                'total_feedback': pr.get('total_feedback') or 0,
                'responded_feedback': pr.get('responded_feedback') or 0,
                'stale_feedback_count': pr.get('stale_feedback_count') or 0,
                'stale_feedback': stale_feedback
            },
            'ci_checks': {
                'passed': pr.get('checks_passed'),
                'failed': pr.get('checks_failed'),
                'skipped': pr.get('checks_skipped')
            }
        }
        
        print(f"Database: Loaded readiness data for PR {pr_id}")
        return readiness_data
    except Exception as e:
        print(f"Error loading readiness from database for PR {pr_id}: {str(e)}")
        return None


async def delete_readiness_from_db(env, pr_id):
    """Clear readiness analysis results from database (prs table).
    
    Args:
        env: Worker environment with database binding
        pr_id: PR ID
    """
    try:
        db = get_db(env)
        
        # Clear readiness fields in the prs table
        stmt = db.prepare('''
            UPDATE prs SET
                overall_score = NULL,
                ci_score = NULL,
                review_score = NULL,
                classification = NULL,
                merge_ready = NULL,
                blockers = NULL,
                warnings = NULL,
                recommendations = NULL,
                review_health_classification = NULL,
                review_health_score = NULL,
                response_rate = NULL,
                total_feedback = NULL,
                responded_feedback = NULL,
                stale_feedback_count = NULL,
                stale_feedback = NULL,
                readiness_computed_at = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''')
        await stmt.bind(pr_id).run()
        
        print(f"Database: Cleared readiness data for PR {pr_id}")
    except Exception as e:
        print(f"Error clearing readiness from database for PR {pr_id}: {str(e)}")
        # Don't raise - cache invalidation is already done


async def upsert_pr(db, pr_url, owner, repo, pr_number, pr_data):
    """Helper to insert or update PR in database (Deduplicates logic)"""
    current_timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    
    stmt = db.prepare('''
        INSERT INTO prs (pr_url, repo_owner, repo_name, pr_number, title, state, 
                       is_merged, mergeable_state, files_changed, author_login,                        author_avatar, repo_owner_avatar, checks_passed, checks_failed, checks_skipped, 
                       commits_count, behind_by, review_status, last_updated_at, 
                       last_refreshed_at, updated_at, is_draft, open_conversations_count, reviewers_json, etag)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(pr_url) DO UPDATE SET
            title = excluded.title,
            state = excluded.state,
            is_merged = excluded.is_merged,
            mergeable_state = excluded.mergeable_state,
            files_changed = excluded.files_changed,
            repo_owner_avatar = excluded.repo_owner_avatar,
            checks_passed = excluded.checks_passed,
            checks_failed = excluded.checks_failed,
            checks_skipped = excluded.checks_skipped,
            commits_count = excluded.commits_count,
            behind_by = excluded.behind_by,
            review_status = excluded.review_status,
            last_updated_at = excluded.last_updated_at,
            last_refreshed_at = excluded.last_refreshed_at,
            updated_at = CURRENT_TIMESTAMP,
            is_draft = excluded.is_draft,
            open_conversations_count = excluded.open_conversations_count,
            reviewers_json = excluded.reviewers_json,
            etag = excluded.etag
    ''').bind(
        pr_url, owner, repo, pr_number,
        pr_data['title'], 
        pr_data['state'],
        pr_data['is_merged'],
        pr_data['mergeable_state'], 
        pr_data['files_changed'],
        pr_data['author_login'], 
        pr_data['author_avatar'],
        pr_data.get('repo_owner_avatar', ''),
        pr_data['checks_passed'], 
        pr_data['checks_failed'],
        pr_data['checks_skipped'],
        pr_data.get('commits_count', 0),
        pr_data.get('behind_by', 0),
        pr_data['review_status'],
        pr_data['last_updated_at'], current_timestamp, current_timestamp,
        pr_data.get('is_draft', 0),
        pr_data.get('open_conversations_count', 0),
        pr_data.get('reviewers_json', '[]'),
        pr_data.get('etag')
    )
    await stmt.run()


async def save_timeline_to_db(env, owner, repo, pr_number, data):
    """Save timeline data to D1 database.
    
    Args:
        env: Worker environment with database binding
        owner: Repository owner
        repo: Repository name
        pr_number: PR number
        data: Timeline data to cache (dict)
    """
    try:
        db = get_db(env)
        from js import Date
        current_time = str(Date.now() / 1000)
        
        stmt = db.prepare('''
            INSERT INTO timeline_cache (owner, repo, pr_number, data, timestamp)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(owner, repo, pr_number) DO UPDATE SET
                data = excluded.data,
                timestamp = excluded.timestamp
        ''').bind(owner, repo, pr_number, json.dumps(data), current_time)
        
        await stmt.run()
        print(f"Database: Saved timeline data for {owner}/{repo}#{pr_number}")
    except Exception as e:
        print(f"Error saving timeline to database for {owner}/{repo}#{pr_number}: {str(e)}")


async def load_timeline_from_db(env, owner, repo, pr_number):
    """Load timeline data from D1 database.
    
    Args:
        env: Worker environment with database binding
        owner: Repository owner
        repo: Repository name
        pr_number: PR number
        
    Returns:
        tuple: (data, timestamp) or (None, None) if not found
    """
    try:
        db = get_db(env)
        stmt = db.prepare('''
            SELECT data, timestamp FROM timeline_cache 
            WHERE owner = ? AND repo = ? AND pr_number = ?
        ''').bind(owner, repo, pr_number)
        
        result = await stmt.first()
        if not result:
            return None, None
            
        result = result.to_py() if hasattr(result, 'to_py') else dict(result)
        return json.loads(result['data']), float(result['timestamp'])
    except Exception as e:
        print(f"Error loading timeline from database for {owner}/{repo}#{pr_number}: {str(e)}")
        return None, None


async def delete_timeline_from_db(env, owner, repo, pr_number):
    """Delete timeline data from D1 database.
    
    Args:
        env: Worker environment with database binding
        owner: Repository owner
        repo: Repository name
        pr_number: PR number
    """
    try:
        db = get_db(env)
        stmt = db.prepare('''
            DELETE FROM timeline_cache 
            WHERE owner = ? AND repo = ? AND pr_number = ?
        ''').bind(owner, repo, pr_number)
        
        await stmt.run()
        print(f"Database: Deleted timeline cache for {owner}/{repo}#{pr_number}")
    except Exception as e:
        print(f"Error deleting timeline from database for {owner}/{repo}#{pr_number}: {str(e)}")
