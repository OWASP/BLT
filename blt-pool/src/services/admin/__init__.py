"""Admin service package for BLT-Pool."""

from .service import AdminService, has_merged_pr_in_org

__all__ = ["AdminService", "has_merged_pr_in_org"]
