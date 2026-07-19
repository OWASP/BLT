"""
ORM model definitions for the BLT API.

Each class maps to a D1 (SQLite) table and inherits the Django-inspired
query API from :class:`libs.orm.Model`.  Models are intentionally thin –
they hold only the ``table_name`` constant.  All query logic lives in the
:class:`libs.orm.QuerySet` returned by ``Model.objects(db)``.

Example usage::

    from models import Domain, Bug, User

    # List active domains
    domains = await Domain.objects(db).filter(is_active=1).order_by('-created').all()

    # Get a single bug
    bug = await Bug.objects(db).get(id=42)

    # Count open bugs for a domain
    n = await Bug.objects(db).filter(domain=5, status='open').count()

    # Create a new tag
    tag = await Tag.create(db, name='xss')
"""

from libs.orm import Model


class Domain(Model):
    """Maps to the ``domains`` table."""
    table_name = "domains"


class Tag(Model):
    """Maps to the ``tags`` table."""
    table_name = "tags"


class DomainTag(Model):
    """Maps to the ``domain_tags`` junction table (domains ↔ tags)."""
    table_name = "domain_tags"


class Bug(Model):
    """Maps to the ``bugs`` table."""
    table_name = "bugs"


class BugScreenshot(Model):
    """Maps to the ``bug_screenshots`` table."""
    table_name = "bug_screenshots"


class BugTag(Model):
    """Maps to the ``bug_tags`` junction table (bugs ↔ tags)."""
    table_name = "bug_tags"


class BugTeamMember(Model):
    """Maps to the ``bug_team_members`` junction table."""
    table_name = "bug_team_members"


class User(Model):
    """Maps to the ``users`` table."""
    table_name = "users"


class UserAuthIdentity(Model):
    """Maps to login/provider identities linked to users."""
    table_name = "user_auth_identities"


class UserApiKey(Model):
    """Maps to user-owned API keys for programmatic access."""
    table_name = "user_api_keys"


class Job(Model):
    """Maps to user-owned job posts."""
    table_name = "jobs"


class Hackathon(Model):
    """Maps to user-owned hackathons."""
    table_name = "hackathons"


class HackathonRegistration(Model):
    """Maps to registrations for user-owned hackathons."""
    table_name = "hackathon_registrations"


class UserFollow(Model):
    """Maps to the ``user_follows`` junction table (users ↔ users)."""
    table_name = "user_follows"


class UserBugUpvote(Model):
    """Maps to the ``user_bug_upvotes`` junction table."""
    table_name = "user_bug_upvotes"


class UserBugSave(Model):
    """Maps to the ``user_bug_saves`` junction table."""
    table_name = "user_bug_saves"


class UserBugFlag(Model):
    """Maps to the ``user_bug_flags`` junction table."""
    table_name = "user_bug_flags"


class Hunt(Model):
    """Maps to the ``hunts`` table."""
    table_name = "hunts"


class Project(Model):
    """Maps to the ``projects`` table."""
    table_name = "projects"


class Repository(Model):
    """Maps to the ``repositories`` table."""
    table_name = "repositories"


class Contributor(Model):
    """Maps to the ``contributors`` table."""
    table_name = "contributors"


