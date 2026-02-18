"""
GitHub integration for the advisory engine.
Fetches PR context from GitHub and provides advisory feedback.
"""

import os
import json
from typing import Dict, List, Optional
from .core import AdvisoryEngine, AdvisoryContext


class GitHubIntegration:
    """Integration with GitHub for PR advisory."""
    
    def __init__(self, engine: Optional[AdvisoryEngine] = None):
        self.engine = engine or AdvisoryEngine()
        self.github_token = os.environ.get('GITHUB_TOKEN', '')
        self.repo = os.environ.get('GITHUB_REPOSITORY', '')
        self.event_path = os.environ.get('GITHUB_EVENT_PATH', '')
    
    def get_pr_context(self) -> Optional[AdvisoryContext]:
        """Extract context from GitHub PR event."""
        if not os.path.exists(self.event_path):
            return None
        
        with open(self.event_path, 'r') as f:
            event_data = json.load(f)
        
        # Extract PR information
        pr = event_data.get('pull_request', {})
        issue = event_data.get('issue', {})
        
        # Get labels
        labels = [label['name'] for label in pr.get('labels', [])]
        if not labels and issue:
            labels = [label['name'] for label in issue.get('labels', [])]
        
        # Get changed files
        files = self._get_changed_files(pr)
        
        # Get repo metadata
        repo_metadata = {
            'repository': self.repo,
            'pr_number': pr.get('number', issue.get('number')),
            'author': pr.get('user', {}).get('login', ''),
            'title': pr.get('title', issue.get('title', ''))
        }
        
        # Check for intent in PR description
        intent = self._extract_intent(pr.get('body', ''))
        
        return AdvisoryContext(
            issue_labels=labels,
            repo_metadata=repo_metadata,
            file_patterns=files,
            contributor_intent=intent
        )
    
    def _get_changed_files(self, pr: Dict) -> List[str]:
        """Get list of changed files from PR."""
        # In a real implementation, this would use GitHub API
        # For now, we'll use a simple approach
        files = []
        
        # Try to get from PR files
        if 'files' in pr:
            files = [f['filename'] for f in pr['files']]
        
        return files
    
    def _extract_intent(self, body: str) -> Optional[str]:
        """Extract contributor intent from PR description."""
        if not body:
            return None
        
        # Look for intent markers
        markers = ['intent:', 'goal:', 'purpose:', 'this pr']
        body_lower = body.lower()
        
        for marker in markers:
            if marker in body_lower:
                # Extract the line with the intent
                lines = body.split('\n')
                for line in lines:
                    if marker in line.lower():
                        return line.strip()
        
        # Default: use first meaningful line
        lines = [l.strip() for l in body.split('\n') if l.strip() and not l.strip().startswith('#')]
        return lines[0] if lines else None
    
    def post_advisory_comment(self, advisory_report: str) -> bool:
        """Post advisory as a PR comment."""
        # This would use GitHub API in production
        # For now, we'll write to a file for the action to handle
        output_file = os.environ.get('GITHUB_OUTPUT', '/tmp/advisory_output.md')
        
        try:
            with open(output_file, 'w') as f:
                f.write(advisory_report)
            return True
        except Exception as e:
            print(f"Error writing advisory output: {e}")
            return False
