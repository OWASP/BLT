#!/usr/bin/env python3
"""
Generate an HTML page listing all repositories in the OWASP GitHub organization.
"""

import base64
import concurrent.futures
import json
import os
import re
import sys
import time
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import urllib.request
import urllib.error


def parse_yaml_frontmatter(content: str) -> Dict:
    """Parse YAML front matter from markdown content."""
    result = {
        "title": "",
        "tags": [],
        "level": None,
        "pitch": "",
        "type": "",
        "region": "",
        "country": ""
    }
    
    # Check if content starts with ---
    if not content.strip().startswith('---'):
        return result
    
    # Find the closing ---
    lines = content.split('\n')
    in_frontmatter = False
    frontmatter_lines = []
    
    for line in lines:
        if line.strip() == '---':
            if not in_frontmatter:
                in_frontmatter = True
                continue
            else:
                break
        if in_frontmatter:
            frontmatter_lines.append(line)
    
    frontmatter_text = '\n'.join(frontmatter_lines)
    
    # Parse key-value pairs (simple YAML parsing without external library)
    for line in frontmatter_lines:
        if ':' in line:
            key, _, value = line.partition(':')
            key = key.strip().lower()
            value = value.strip()
            
            if key == 'title':
                result['title'] = value
            elif key == 'tags':
                # Handle both inline tags and list format
                if value:
                    # Handle [tag1, tag2] format
                    if value.startswith('[') and value.endswith(']'):
                        value = value[1:-1]
                    result['tags'] = [t.strip().strip('"\'') for t in value.split(',') if t.strip()]
            elif key == 'level':
                try:
                    result['level'] = float(value)
                except (ValueError, TypeError):
                    pass
            elif key == 'pitch':
                result['pitch'] = value
            elif key == 'type':
                result['type'] = value
            elif key == 'region':
                result['region'] = value
            elif key == 'country':
                result['country'] = value
    
    return result


def fetch_index_md(owner: str, repo: str, token: str = None) -> Optional[Dict]:
    """Fetch and parse index.md from a repository."""
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/index.md"
    
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "OWASP-Bumper-Repo-List-Generator"
    }
    
    if token:
        headers["Authorization"] = f"token {token}"
    
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            content_b64 = data.get("content", "")
            if content_b64:
                content = base64.b64decode(content_b64).decode('utf-8', errors='replace')
                return parse_yaml_frontmatter(content)
    except urllib.error.HTTPError:
        return None
    except Exception:
        return None
    
    return None


def fetch_open_prs_count(owner: str, repo: str, token: str = None) -> int:
    """Fetch the count of open pull requests for a repository."""
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls?state=open&per_page=1"
    
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "OWASP-Bumper-Repo-List-Generator"
    }
    
    if token:
        headers["Authorization"] = f"token {token}"
    
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            # Check the Link header for total count
            link_header = response.getheader('Link', '')
            if 'rel="last"' in link_header:
                # Extract the page number from the last link
                match = re.search(r'page=(\d+)>; rel="last"', link_header)
                if match:
                    return int(match.group(1))
            # If no Link header, count the items returned
            data = json.loads(response.read().decode())
            return len(data)
    except urllib.error.HTTPError:
        return 0
    except Exception:
        return 0


def fetch_last_commit(owner: str, repo: str, token: str = None) -> Optional[Dict]:
    """Fetch the most recent commit for a repository."""
    url = f"https://api.github.com/repos/{owner}/{repo}/commits?per_page=1"

    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "OWASP-Bumper-Repo-List-Generator"
    }

    if token:
        headers["Authorization"] = f"token {token}"

    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            if data:
                commit = data[0]
                author_obj = commit.get("author") or {}
                git_author = commit.get("commit", {}).get("author") or {}
                message = commit.get("commit", {}).get("message", "") or ""
                # Use only the first line of the commit message
                message = message.split("\n")[0].strip()
                return {
                    "message": message,
                    "author": author_obj.get("login") or git_author.get("name", ""),
                    "avatar_url": author_obj.get("avatar_url", ""),
                    "author_url": author_obj.get("html_url", ""),
                }
    except urllib.error.HTTPError:
        return None
    except Exception:
        return None

    return None


def fetch_participation_stats(owner: str, repo: str, token: str = None) -> Optional[List[int]]:
    """Fetch weekly commit participation stats for a repository (last 52 weeks)."""
    url = f"https://api.github.com/repos/{owner}/{repo}/stats/participation"
    
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "OWASP-Bumper-Repo-List-Generator"
    }
    
    if token:
        headers["Authorization"] = f"token {token}"
    
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 202:
                # Stats are being computed, return None
                return None
            data = json.loads(response.read().decode())
            # Return the 'all' array which contains commit counts for all contributors
            return data.get("all", [])
    except urllib.error.HTTPError as e:
        if e.code == 202:
            # Stats are being computed
            return None
        return None
    except Exception:
        return None


def fetch_repos(org: str, token: str = None) -> List[Dict]:
    """Fetch all repositories for a GitHub organization."""
    repos = []
    page = 1
    per_page = 100
    
    while True:
        url = f"https://api.github.com/orgs/{org}/repos?per_page={per_page}&page={page}&sort=updated&direction=desc"
        
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "OWASP-Bumper-Repo-List-Generator"
        }
        
        if token:
            headers["Authorization"] = f"token {token}"
        
        req = urllib.request.Request(url, headers=headers)
        
        try:
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                
                if not data:
                    break
                
                repos.extend(data)
                page += 1
                
                # Check if we've reached the last page
                if len(data) < per_page:
                    break
                    
        except urllib.error.HTTPError as e:
            print(f"Error fetching repositories: {e}", file=sys.stderr)
            print(f"Response: {e.read().decode()}", file=sys.stderr)
            sys.exit(1)
    
    return repos

def format_date(date_str: str) -> str:
    """Format ISO date string to a readable format."""
    if not date_str:
        return "N/A"
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d')
    except:
        return date_str

def generate_html(repos: List[Dict], org: str) -> str:
    """Generate HTML page with repository listing."""
    
    # Prepare repository data as JSON for JavaScript
    repo_data = []
    for repo in repos:
        index_md = repo.get("index_md", {}) or {}
        sparkline = repo.get("sparkline", [])
        activity_score = sum(sparkline) if sparkline else 0
        repo_data.append({
            "name": repo.get("name", ""),
            "full_name": repo.get("full_name", ""),
            "description": repo.get("description", "") or "",
            "html_url": repo.get("html_url", ""),
            "stargazers_count": repo.get("stargazers_count", 0),
            "forks_count": repo.get("forks_count", 0),
            "open_issues_count": repo.get("open_issues_count", 0),
            "open_prs_count": repo.get("open_prs_count", 0),
            "updated_at": repo.get("updated_at", ""),
            "created_at": repo.get("created_at", ""),
            "language": repo.get("language", "") or "N/A",
            "archived": repo.get("archived", False),
            "is_project": "www-project" in repo.get("name", "").lower(),
            "is_chapter": "www-chapter" in repo.get("name", "").lower(),
            "sparkline": sparkline,
            "activity_score": activity_score,
            # last commit data
            **{
                "last_commit_message": (lc := repo.get("last_commit") or {}).get("message", ""),
                "last_commit_author": lc.get("author", ""),
                "last_commit_avatar_url": lc.get("avatar_url", ""),
                "last_commit_author_url": lc.get("author_url", ""),
            },
            # index.md data
            "title": index_md.get("title", ""),
            "tags": index_md.get("tags", []),
            "level": index_md.get("level"),
            "pitch": index_md.get("pitch", ""),
            "type": index_md.get("type", ""),
            "region": index_md.get("region", ""),
            "country": index_md.get("country", "")
        })
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{org} GitHub Repositories</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        html {{
            overflow-x: hidden;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', sans-serif;
            line-height: 1.6;
            color: #0f172a;
            background: #f8fafc;
            padding: 20px;
            overflow-x: hidden;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        h1 {{
            color: #0f172a;
            margin-bottom: 10px;
            font-size: 2.5em;
        }}
        
        .subtitle {{
            color: #475569;
            margin-bottom: 30px;
            font-size: 1.1em;
        }}
        
        .controls {{
            display: flex;
            gap: 15px;
            margin-bottom: 25px;
            flex-wrap: wrap;
            align-items: center;
        }}
        
        .search-box {{
            flex: 1;
            min-width: 250px;
        }}
        
        input[type="text"] {{
            width: 100%;
            padding: 12px 15px;
            border: 2px solid #e2e8f0;
            border-radius: 6px;
            font-size: 14px;
            transition: border-color 0.3s;
        }}
        
        input[type="text"]:focus {{
            outline: none;
            border-color: #E10101;
        }}
        
        .btn-group {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }}
        
        button {{
            padding: 12px 20px;
            border: 2px solid #E10101;
            background: white;
            color: #E10101;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: all 0.3s;
        }}
        
        button:hover {{
            background: #E10101;
            color: white;
        }}
        
        button.active {{
            background: #E10101;
            color: white;
        }}
        
        .checkbox-label {{
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 12px 20px;
            font-size: 14px;
            font-weight: 600;
            color: #E10101;
            cursor: pointer;
            user-select: none;
        }}
        
        .checkbox-label input[type="checkbox"] {{
            width: 16px;
            height: 16px;
            cursor: pointer;
        }}
        
        .sort-buttons {{
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
            margin-bottom: 15px;
        }}
        
        .sort-btn {{
            padding: 6px 12px;
            border: 1px solid #e2e8f0;
            background: white;
            color: #475569;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            font-weight: 500;
            transition: all 0.3s;
        }}
        
        .sort-btn:hover {{
            border-color: #E10101;
            color: #E10101;
        }}
        
        .sort-btn.active {{
            background: #E10101;
            color: white;
            border-color: #E10101;
        }}
        
        .stats {{
            display: flex;
            gap: 20px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}
        
        .stat {{
            padding: 10px 20px;
            background: #ecf0f1;
            border-radius: 6px;
            font-size: 14px;
        }}
        
        .stat strong {{
            color: #0f172a;
            font-size: 18px;
        }}
        
        .stat.clickable {{
            cursor: pointer;
            transition: all 0.3s;
        }}
        
        .stat.clickable:hover {{
            background: #d5dbdb;
        }}
        
        .stat.clickable.active {{
            background: #E10101;
            color: white;
        }}
        
        .stat.clickable.active strong {{
            color: white;
        }}
        
        .stat.active-within-year {{
            border-left: 4px solid #27ae60;
        }}
        
        .stat.inactive-1yr {{
            border-left: 4px solid #e65100;
        }}
        
        .stat.inactive-3yr {{
            border-left: 4px solid #bf360c;
        }}
        
        .repo-list {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
            gap: 12px;
        }}
        
        .repo-item {{
            padding: 12px 14px;
            border: 1px solid #e1e8ed;
            border-radius: 6px;
            transition: all 0.3s;
            background: white;
            display: flex;
            flex-direction: column;
        }}
        
        .repo-item:hover {{
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            transform: translateY(-1px);
        }}
        
        .repo-item.archived {{
            opacity: 0.7;
            background: #f9f9f9;
        }}
        
        .repo-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 6px;
            gap: 8px;
        }}
        
        .repo-name {{
            flex: 1;
            min-width: 0;
        }}
        
        .repo-name a {{
            color: #E10101;
            text-decoration: none;
            font-size: 14px;
            font-weight: 600;
            word-break: break-word;
            display: block;
        }}
        
        .repo-name a:hover {{
            text-decoration: underline;
        }}
        
        .repo-title {{
            font-size: 11px;
            color: #666;
            margin-top: 2px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        
        .repo-badges {{
            display: flex;
            gap: 4px;
            flex-wrap: wrap;
            align-items: center;
            flex-shrink: 0;
        }}
        
        .badge {{
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 9px;
            font-weight: 600;
            text-transform: uppercase;
            white-space: nowrap;
        }}
        
        .badge.project {{
            background: #e8f5e9;
            color: #2e7d32;
        }}
        
        .badge.chapter {{
            background: #fee2e2;
            color: #dc2626;
        }}
        
        .badge.archived {{
            background: #ffebee;
            color: #c62828;
        }}
        
        .badge.language {{
            background: #f8fafc;
            color: #475569;
        }}
        
        .badge.inactive-1yr {{
            background: #fff3e0;
            color: #e65100;
        }}
        
        .badge.inactive-3yr {{
            background: #ffccbc;
            color: #bf360c;
        }}
        
        .badge.level {{
            background: #9c27b0;
            color: white;
        }}
        
        .badge.level-1 {{
            background: #e1bee7;
            color: #6a1b9a;
        }}
        
        .badge.level-2 {{
            background: #ce93d8;
            color: #4a148c;
        }}
        
        .badge.level-3 {{
            background: #ab47bc;
            color: white;
        }}
        
        .badge.level-4 {{
            background: #7b1fa2;
            color: white;
        }}
        
        .badge.tag {{
            background: #e0e0e0;
            color: #424242;
            font-size: 8px;
        }}
        
        .bump-btn {{
            padding: 4px 8px;
            background: #ff9800;
            color: white;
            border: none;
            border-radius: 3px;
            font-size: 10px;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 3px;
            transition: background 0.3s;
        }}
        
        .bump-btn:hover {{
            background: #f57c00;
        }}
        
        .bump-btn.archived {{
            background: #bdbdbd;
            cursor: not-allowed;
        }}
        
        .repo-description {{
            color: #666;
            margin-bottom: 6px;
            line-height: 1.4;
            font-size: 12px;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
            flex-grow: 1;
        }}
        
        .repo-pitch {{
            color: #555;
            font-size: 11px;
            font-style: italic;
            margin-bottom: 6px;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
            padding: 4px 6px;
            background: #f8fafc;
            border-radius: 3px;
            border-left: 2px solid #E10101;
        }}
        
        .repo-tags {{
            display: flex;
            gap: 3px;
            flex-wrap: wrap;
            margin-bottom: 6px;
        }}
        
        .repo-meta {{
            display: flex;
            gap: 8px;
            font-size: 11px;
            color: #475569;
            flex-wrap: nowrap;
            overflow-x: auto;
        }}
        
        .meta-item {{
            display: flex;
            align-items: center;
            gap: 3px;
            white-space: nowrap;
            flex-shrink: 0;
        }}
        
        .meta-item.prs {{
            color: #9c27b0;
        }}
        
        .sparkline-container {{
            display: flex;
            align-items: center;
            gap: 6px;
            margin-top: 6px;
            padding-top: 6px;
            border-top: 1px solid #f0f0f0;
            flex-wrap: nowrap;
            overflow-x: auto;
        }}
        
        .sparkline-label {{
            font-size: 10px;
            color: #475569;
            white-space: nowrap;
            flex-shrink: 0;
        }}
        
        .sparkline {{
            stroke: #E10101;
            fill: none;
            stroke-width: 1.5;
        }}
        
        .sparkline-fill {{
            fill: rgba(225, 1, 1, 0.1);
            stroke: none;
        }}
        
        .repo-item.archived .sparkline {{
            stroke: #cbd5e1;
        }}
        
        .repo-item.archived .sparkline-fill {{
            fill: rgba(203, 213, 225, 0.1);
        }}
        
        .activity-score {{
            font-size: 12px;
            font-weight: 600;
            color: #E10101;
            background: #fee2e2;
            padding: 2px 8px;
            border-radius: 4px;
            white-space: nowrap;
            flex-shrink: 0;
        }}
        
        .repo-item.archived .activity-score {{
            color: #475569;
            background: #f8fafc;
        }}
        
        .last-commit {{
            display: flex;
            align-items: center;
            gap: 6px;
            margin-top: 6px;
            padding-top: 6px;
            border-top: 1px solid #f0f0f0;
            font-size: 11px;
            color: #475569;
            overflow: hidden;
        }}
        
        .last-commit-avatar {{
            width: 18px;
            height: 18px;
            border-radius: 50%;
            flex-shrink: 0;
            vertical-align: middle;
        }}
        
        .last-commit-author {{
            font-weight: 600;
            white-space: nowrap;
            flex-shrink: 0;
            color: #0f172a;
            text-decoration: none;
        }}
        
        .last-commit-author:hover {{
            text-decoration: underline;
        }}
        
        .last-commit-message {{
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            color: #475569;
        }}
        
        .last-commit-cell {{
            display: flex;
            align-items: center;
            gap: 4px;
            min-width: 160px;
            max-width: 240px;
        }}
        
        .last-commit-cell-text {{
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            font-size: 11px;
        }}
        
        .no-results {{
            text-align: center;
            padding: 60px 20px;
            color: #475569;
            font-size: 18px;
            grid-column: 1 / -1;
        }}
        
        .loading {{
            text-align: center;
            padding: 40px;
            color: #E10101;
        }}
        
        .table-wrapper {{
            overflow-x: auto;
            width: 100%;
        }}
        
        table.repo-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}
        
        table.repo-table th {{
            background: #f8fafc;
            padding: 10px 12px;
            text-align: left;
            font-weight: 600;
            color: #0f172a;
            border-bottom: 2px solid #e2e8f0;
            white-space: nowrap;
            position: sticky;
            top: 0;
            z-index: 1;
        }}
        
        table.repo-table th.sortable {{
            cursor: pointer;
            user-select: none;
        }}
        
        table.repo-table th.sortable:hover {{
            background: #fee2e2;
            color: #E10101;
        }}
        
        table.repo-table th.sort-active {{
            background: #fee2e2;
            color: #E10101;
        }}
        
        table.repo-table td {{
            padding: 8px 12px;
            border-bottom: 1px solid #f0f0f0;
            vertical-align: middle;
        }}
        
        table.repo-table tbody tr:hover td {{
            background: #fef2f2;
        }}
        
        table.repo-table tbody tr.archived td {{
            opacity: 0.7;
            background: #f9f9f9;
        }}
        
        table.repo-table tbody tr.archived:hover td {{
            background: #f5f5f5;
        }}
        
        .table-name-link {{
            color: #E10101;
            text-decoration: none;
            font-weight: 600;
        }}
        
        .table-name-link:hover {{
            text-decoration: underline;
        }}
        
        .table-desc {{
            max-width: 280px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            color: #666;
            font-size: 12px;
        }}
        
        .table-num {{
            text-align: right;
            font-variant-numeric: tabular-nums;
        }}
        
        .sort-arrow {{
            margin-left: 4px;
            font-size: 10px;
            opacity: 0.6;
        }}
        
        .creation-chart-section {{
            margin-bottom: 30px;
            padding: 20px;
            background: #f8fafc;
            border-radius: 8px;
            border: 1px solid #e2e8f0;
        }}
        
        .creation-chart-title {{
            font-size: 16px;
            font-weight: 600;
            color: #0f172a;
            margin-bottom: 15px;
        }}
        
        .creation-chart-wrapper {{
            overflow-x: auto;
            width: 100%;
        }}
        
        .creation-chart-bar {{
            fill: #E10101;
            opacity: 0.85;
            transition: opacity 0.2s, fill 0.2s;
            cursor: pointer;
        }}
        
        .creation-chart-bar:hover {{
            opacity: 1;
        }}
        
        .creation-chart-bar-selected {{
            fill: #a00000;
            opacity: 1;
        }}
        
        .creation-chart-has-selection .creation-chart-bar:not(.creation-chart-bar-selected) {{
            opacity: 0.35;
        }}
        
        .creation-chart-bar-group {{
            cursor: pointer;
        }}
        
        .year-filter-clear-btn {{
            background: none;
            border: 1px solid #E10101;
            color: #E10101;
            border-radius: 4px;
            padding: 1px 6px;
            font-size: 11px;
            cursor: pointer;
            margin-left: 4px;
            vertical-align: middle;
        }}
        
        .year-filter-clear-btn:hover {{
            background: #E10101;
            color: #fff;
        }}
        
        footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e2e8f0;
            text-align: center;
            color: #475569;
            font-size: 14px;
        }}
        
        @media (max-width: 768px) {{
            body {{
                padding: 10px;
                width: 100%;
                max-width: 100vw;
            }}
            
            .container {{
                padding: 12px;
                max-width: 100%;
                width: calc(100% - 20px);
                margin: 0 auto;
                overflow-x: hidden;
                box-sizing: border-box;
            }}
            
            h1 {{
                font-size: 1.8em;
            }}
            
            .controls {{
                flex-direction: column;
            }}
            
            .search-box {{
                width: 100%;
            }}
            
            .btn-group {{
                width: 100%;
            }}
            
            button {{
                flex: 1;
            }}
            
            .sort-buttons {{
                justify-content: flex-start;
                flex-wrap: wrap;
            }}
            
            .sort-btn {{
                padding: 5px 10px;
                font-size: 11px;
            }}
            
            .repo-list {{
                display: flex;
                flex-direction: column;
                gap: 12px;
            }}
            
            .repo-item {{
                width: 100%;
                max-width: calc(100vw - 44px);
                padding: 12px;
                box-sizing: border-box;
                overflow: hidden;
                margin: 0;
            }}
            
            .repo-header {{
                flex-direction: column;
                align-items: flex-start;
            }}
            
            .repo-name {{
                width: 100%;
                margin-bottom: 8px;
            }}
            
            .repo-badges {{
                width: 100%;
                flex-wrap: wrap;
            }}
            
            .repo-description {{
                word-break: break-word;
                overflow-wrap: break-word;
            }}
            
            .repo-meta {{
                flex-direction: row;
                flex-wrap: nowrap;
                overflow-x: auto;
                gap: 8px;
            }}
            
            .meta-item {{
                display: inline-flex;
                flex-shrink: 0;
            }}
            
            .sparkline-container {{
                flex-direction: row;
                align-items: center;
                gap: 6px;
                max-width: 100%;
                flex-wrap: nowrap;
                overflow-x: auto;
            }}
            
            .sparkline-svg {{
                max-width: 100%;
            }}
            
            .stats {{
                flex-direction: column;
                gap: 10px;
            }}
            
            .stat {{
                width: 100%;
                text-align: center;
                box-sizing: border-box;
            }}
            
            .repo-badges {{
                max-width: 100%;
            }}
            
            .badge {{
                font-size: 10px;
                padding: 3px 6px;
            }}
            
            .bump-btn {{
                padding: 4px 8px;
                font-size: 11px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>OWASP Bumper 🚀💪</h1>
        <div class="subtitle">This application aims to help encourage repositories to stay active by giving them a bump of a new issue with one click! 🔔✨</div>
        <div class="subtitle">Comprehensive listing of all {org} GitHub repositories | <a href="https://github.com/OWASP-BLT/OWASP-Bumper" target="_blank" style="color: #E10101;">View on GitHub</a></div>
        
        <div class="creation-chart-section">
            <div class="creation-chart-title">📊 New Repositories Created Over Time<span id="creationYearFilterLabel" style="display:none"> — <span id="creationYearFilterValue"></span> <button class="year-filter-clear-btn" onclick="setCreationYearFilter(null)">✕ Clear</button></span></div>
            <div class="creation-chart-subtitle" id="creationChartSubtitle" style="font-size:12px;color:#64748b;margin-bottom:8px;">Click a bar to filter repositories by creation year</div>
            <div class="creation-chart-wrapper">
                <div id="creationChartSvg"></div>
            </div>
        </div>
        
        <div class="controls">
            <div class="search-box">
                <input type="text" id="searchInput" placeholder="Search by name, description, title, pitch, or tags...">
            </div>
            <div class="btn-group">
                <button id="filterAll" class="active" onclick="setFilter('all')">All</button>
                <button id="filterProject" onclick="setFilter('project')">Projects</button>
                <button id="filterChapter" onclick="setFilter('chapter')">Chapters</button>
                <button id="filterOther" onclick="setFilter('other')">Other</button>
            </div>
            <label class="checkbox-label">
                <input type="checkbox" id="hideArchived" checked onchange="toggleHideArchived()">
                Hide Archived
            </label>
            <div class="btn-group">
                <button id="viewCards" class="active" onclick="setViewMode('cards')">🃏 Cards</button>
                <button id="viewTable" onclick="setViewMode('table')">📋 Table</button>
            </div>
        </div>
        
        <div class="sort-buttons">
            <button class="sort-btn active" data-sort="updated-desc">Updated ↓</button>
            <button class="sort-btn" data-sort="updated-asc">Updated ↑</button>
            <button class="sort-btn" data-sort="name-asc">Name A-Z</button>
            <button class="sort-btn" data-sort="name-desc">Name Z-A</button>
            <button class="sort-btn" data-sort="stars-desc">Stars ↓</button>
            <button class="sort-btn" data-sort="stars-asc">Stars ↑</button>
            <button class="sort-btn" data-sort="forks-desc">Forks ↓</button>
            <button class="sort-btn" data-sort="forks-asc">Forks ↑</button>
            <button class="sort-btn" data-sort="activity-desc">Activity ↓</button>
            <button class="sort-btn" data-sort="activity-asc">Activity ↑</button>
            <button class="sort-btn" data-sort="prs-desc">PRs ↓</button>
            <button class="sort-btn" data-sort="prs-asc">PRs ↑</button>
            <button class="sort-btn" data-sort="issues-desc">Issues ↓</button>
            <button class="sort-btn" data-sort="issues-asc">Issues ↑</button>
            <button class="sort-btn" data-sort="level-desc">Level ↓</button>
            <button class="sort-btn" data-sort="level-asc">Level ↑</button>
            <button class="sort-btn" data-sort="created-desc">Created ↓</button>
            <button class="sort-btn" data-sort="created-asc">Created ↑</button>
        </div>
        
        <div class="stats">
            <div class="stat">
                <strong id="totalCount">0</strong> Total Repositories
                (<strong id="activeReposCount">0</strong> active, <strong id="archivedReposCount">0</strong> archived)
            </div>
            <div class="stat">
                <strong id="visibleCount">0</strong> Visible
            </div>
            <div class="stat">
                <strong id="projectCount">0</strong> Projects
                (<strong id="activeProjectsCount">0</strong> active, <strong id="archivedProjectsCount">0</strong> archived)
            </div>
            <div class="stat">
                <strong id="chapterCount">0</strong> Chapters
                (<strong id="activeChaptersCount">0</strong> active, <strong id="archivedChaptersCount">0</strong> archived)
            </div>
        </div>
        
        <div class="stats">
            <div class="stat clickable active-within-year" id="filterActiveYear" onclick="setActivityFilter('within-year')">
                <strong id="activeYearCount">0</strong> Updated within 1 year
            </div>
            <div class="stat clickable inactive-1yr" id="filterInactive1yr" onclick="setActivityFilter('1yr-old')">
                <strong id="inactive1yrCount">0</strong> Older than 1 year
            </div>
            <div class="stat clickable inactive-3yr" id="filterInactive3yr" onclick="setActivityFilter('3yr-old')">
                <strong id="inactive3yrCount">0</strong> Older than 3 years
            </div>
        </div>
        
        <div id="repoList" class="repo-list"></div>
        
        <footer>
            Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC | Total: {len(repos)} repositories
        </footer>
    </div>
    
    <script>
        const repos = {json.dumps(repo_data, indent=8)};
        
        let currentFilter = 'all';
        let currentSort = 'activity-desc';
        let searchTerm = '';
        let activityFilter = 'all';
        let hideArchived = true;
        let viewMode = 'cards';
        let creationYearFilter = null;
        
        // HTML escape function to prevent XSS
        function escapeHtml(text) {{
            if (!text) return '';
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }}
        
        function formatDate(dateStr) {{
            if (!dateStr) return 'N/A';
            const date = new Date(dateStr);
            return date.toLocaleDateString('en-US', {{ year: 'numeric', month: 'short', day: 'numeric' }});
        }}
        
        function getTimeAgo(dateStr) {{
            if (!dateStr) return '';
            const date = new Date(dateStr);
            const now = new Date();
            const diffMs = now - date;
            const diffSeconds = Math.floor(diffMs / 1000);
            const diffMinutes = Math.floor(diffSeconds / 60);
            const diffHours = Math.floor(diffMinutes / 60);
            const diffDays = Math.floor(diffHours / 24);
            const diffWeeks = Math.floor(diffDays / 7);
            const diffMonths = Math.floor(diffDays / 30);
            const diffYears = Math.floor(diffDays / 365);
            
            if (diffYears > 0) {{
                return diffYears === 1 ? '1 year ago' : `${{diffYears}} years ago`;
            }} else if (diffMonths > 0) {{
                return diffMonths === 1 ? '1 month ago' : `${{diffMonths}} months ago`;
            }} else if (diffWeeks > 0) {{
                return diffWeeks === 1 ? '1 week ago' : `${{diffWeeks}} weeks ago`;
            }} else if (diffDays > 0) {{
                return diffDays === 1 ? '1 day ago' : `${{diffDays}} days ago`;
            }} else if (diffHours > 0) {{
                return diffHours === 1 ? '1 hour ago' : `${{diffHours}} hours ago`;
            }} else if (diffMinutes > 0) {{
                return diffMinutes === 1 ? '1 minute ago' : `${{diffMinutes}} minutes ago`;
            }} else {{
                return 'just now';
            }}
        }}
        
        function getYearsSinceUpdate(dateStr) {{
            if (!dateStr) return 0;
            const lastUpdate = new Date(dateStr);
            const now = new Date();
            const diffTime = now - lastUpdate;
            const diffYears = diffTime / (1000 * 60 * 60 * 24 * 365.25);
            return diffYears;
        }}
        
        function generateSparklineSVG(data, width = 100, height = 20) {{
            if (!data || data.length === 0) {{
                return '<span class="sparkline-label" style="color: #bdc3c7;">No activity data</span>';
            }}
            
            const max = Math.max(...data, 1);
            const divisor = data.length > 1 ? data.length - 1 : 1;
            
            // Helper to calculate coordinates
            const getCoord = (value, index) => {{
                const x = (index / divisor) * width;
                const y = height - (value / max) * height;
                return `${{x.toFixed(1)}},${{y.toFixed(1)}}`;
            }};
            
            const points = data.map((value, index) => getCoord(value, index)).join(' ');
            
            // Create fill path (area under the line)
            const fillPoints = data.map((value, index) => getCoord(value, index));
            const fillPath = `M0,${{height}} L${{fillPoints.join(' L')}} L${{width}},${{height}} Z`;
            
            const totalCommits = data.reduce((a, b) => a + b, 0);
            const title = `${{totalCommits}} commits in the last 52 weeks`;
            
            return `<svg class="sparkline-svg" width="${{width}}" height="${{height}}" viewBox="0 0 ${{width}} ${{height}}" title="${{title}}">
                <title>${{title}}</title>
                <path class="sparkline-fill" d="${{fillPath}}"></path>
                <polyline class="sparkline" points="${{points}}"></polyline>
            </svg>`;
        }}
        
        function getBumpIssueUrl(repo) {{
            const title = encodeURIComponent('Repository Activity Reminder');
            const body = encodeURIComponent(
`Hello from the OWASP BLT team! 👋

We noticed that this repository hasn't seen much activity recently. We wanted to reach out to check on the status of this project.

**Please consider one of the following actions:**
- ✅ If this project is still active, please update it with any recent changes or a simple commit to show it's maintained
- 📦 If this project is no longer maintained, please consider archiving it to help keep the OWASP organization tidy
- 💬 If you need help or resources, please let us know in the comments

Thank you for contributing to the OWASP community!

---
*This issue was created via the [OWASP Bumper](https://github.com/OWASP-BLT/OWASP-Bumper) tool to help keep track of repository activity.*`
            );
            return `${{repo.html_url}}/issues/new?title=${{title}}&body=${{body}}`;
        }}
        
        function setFilter(filter) {{
            currentFilter = filter;
            
            // Update button states
            document.querySelectorAll('.btn-group button').forEach(btn => btn.classList.remove('active'));
            document.getElementById('filter' + filter.charAt(0).toUpperCase() + filter.slice(1)).classList.add('active');
            
            renderRepos();
        }}
        
        function setActivityFilter(filter) {{
            // Toggle filter - if clicking the same one, clear it
            if (activityFilter === filter) {{
                activityFilter = 'all';
            }} else {{
                activityFilter = filter;
            }}
            
            // Update button states
            document.querySelectorAll('.stat.clickable').forEach(stat => stat.classList.remove('active'));
            if (activityFilter !== 'all') {{
                if (activityFilter === 'within-year') {{
                    document.getElementById('filterActiveYear').classList.add('active');
                }} else if (activityFilter === '1yr-old') {{
                    document.getElementById('filterInactive1yr').classList.add('active');
                }} else if (activityFilter === '3yr-old') {{
                    document.getElementById('filterInactive3yr').classList.add('active');
                }}
            }}
            
            renderRepos();
        }}
        
        function setCreationYearFilter(year) {{
            // Toggle filter - if clicking the same year or passing null, clear it
            if (year === null || creationYearFilter === year) {{
                creationYearFilter = null;
            }} else {{
                creationYearFilter = year;
            }}
            renderCreationChart();
            renderRepos();
        }}
        
        function toggleHideArchived() {{
            hideArchived = document.getElementById('hideArchived').checked;
            renderRepos();
        }}
        
        function setViewMode(mode) {{
            viewMode = mode;
            document.getElementById('viewCards').classList.toggle('active', mode === 'cards');
            document.getElementById('viewTable').classList.toggle('active', mode === 'table');
            renderRepos();
        }}
        
        function getSortArrow(colKey) {{
            if (currentSort === colKey + '-desc') return '↓';
            if (currentSort === colKey + '-asc') return '↑';
            return '⇅';
        }}
        
        function sortByColumn(colKey) {{
            if (currentSort === colKey + '-desc') {{
                currentSort = colKey + '-asc';
            }} else {{
                currentSort = colKey + '-desc';
            }}
            document.querySelectorAll('.sort-btn').forEach(b => {{
                b.classList.toggle('active', b.dataset.sort === currentSort);
            }});
            renderRepos();
        }}
        
        function sortRepos(repos, sortBy) {{
            const sorted = [...repos];
            
            switch(sortBy) {{
                case 'updated-desc':
                    sorted.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));
                    break;
                case 'updated-asc':
                    sorted.sort((a, b) => new Date(a.updated_at) - new Date(b.updated_at));
                    break;
                case 'created-desc':
                    sorted.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
                    break;
                case 'created-asc':
                    sorted.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
                    break;
                case 'name-asc':
                    sorted.sort((a, b) => a.name.localeCompare(b.name));
                    break;
                case 'name-desc':
                    sorted.sort((a, b) => b.name.localeCompare(a.name));
                    break;
                case 'stars-desc':
                    sorted.sort((a, b) => b.stargazers_count - a.stargazers_count);
                    break;
                case 'stars-asc':
                    sorted.sort((a, b) => a.stargazers_count - b.stargazers_count);
                    break;
                case 'forks-desc':
                    sorted.sort((a, b) => b.forks_count - a.forks_count);
                    break;
                case 'forks-asc':
                    sorted.sort((a, b) => a.forks_count - b.forks_count);
                    break;
                case 'activity-desc':
                    sorted.sort((a, b) => b.activity_score - a.activity_score);
                    break;
                case 'activity-asc':
                    sorted.sort((a, b) => a.activity_score - b.activity_score);
                    break;
                case 'prs-desc':
                    sorted.sort((a, b) => (b.open_prs_count || 0) - (a.open_prs_count || 0));
                    break;
                case 'prs-asc':
                    sorted.sort((a, b) => (a.open_prs_count || 0) - (b.open_prs_count || 0));
                    break;
                case 'issues-desc':
                    sorted.sort((a, b) => b.open_issues_count - a.open_issues_count);
                    break;
                case 'issues-asc':
                    sorted.sort((a, b) => a.open_issues_count - b.open_issues_count);
                    break;
                case 'level-desc':
                    sorted.sort((a, b) => (b.level || 0) - (a.level || 0));
                    break;
                case 'level-asc':
                    sorted.sort((a, b) => (a.level || 0) - (b.level || 0));
                    break;
            }}
            
            return sorted;
        }}
        
        function filterRepos(repos) {{
            let filtered = repos;
            
            // Apply hide archived filter
            if (hideArchived) {{
                filtered = filtered.filter(repo => !repo.archived);
            }}
            
            // Apply filter
            if (currentFilter === 'project') {{
                filtered = filtered.filter(repo => repo.is_project);
            }} else if (currentFilter === 'chapter') {{
                filtered = filtered.filter(repo => repo.is_chapter);
            }} else if (currentFilter === 'other') {{
                filtered = filtered.filter(repo => !repo.is_project && !repo.is_chapter);
            }}
            
            // Apply activity filter
            if (activityFilter === 'within-year') {{
                filtered = filtered.filter(repo => getYearsSinceUpdate(repo.updated_at) < 1);
            }} else if (activityFilter === '1yr-old') {{
                filtered = filtered.filter(repo => getYearsSinceUpdate(repo.updated_at) >= 1);
            }} else if (activityFilter === '3yr-old') {{
                filtered = filtered.filter(repo => getYearsSinceUpdate(repo.updated_at) >= 3);
            }}
            
            // Apply creation year filter
            if (creationYearFilter !== null) {{
                filtered = filtered.filter(repo => {{
                    if (!repo.created_at) return false;
                    return new Date(repo.created_at).getFullYear() === creationYearFilter;
                }});
            }}
            
            // Apply search
            if (searchTerm) {{
                const term = searchTerm.toLowerCase();
                filtered = filtered.filter(repo => 
                    repo.name.toLowerCase().includes(term) || 
                    repo.description.toLowerCase().includes(term) ||
                    (repo.title && repo.title.toLowerCase().includes(term)) ||
                    (repo.pitch && repo.pitch.toLowerCase().includes(term)) ||
                    (repo.tags && repo.tags.some(tag => tag.toLowerCase().includes(term)))
                );
            }}
            
            return filtered;
        }}
        
        function renderCards(filtered) {{
            const container = document.getElementById('repoList');
            container.className = 'repo-list';
            
            if (filtered.length === 0) {{
                container.innerHTML = '<div class="no-results">No repositories match your criteria</div>';
                document.getElementById('visibleCount').textContent = '0';
                return;
            }}
            
            container.innerHTML = filtered.map(repo => {{
                const badges = [];
                const yearsSinceUpdate = getYearsSinceUpdate(repo.updated_at);
                
                // Level badge
                if (repo.level !== null && repo.level !== undefined) {{
                    const levelClass = repo.level >= 4 ? 'level-4' : 
                                       repo.level >= 3 ? 'level-3' : 
                                       repo.level >= 2 ? 'level-2' : 'level-1';
                    badges.push(`<span class="badge level ${{levelClass}}" title="OWASP Level ${{repo.level}}">L${{repo.level}}</span>`);
                }}
                
                if (repo.is_project) {{
                    badges.push('<span class="badge project">Project</span>');
                }}
                if (repo.is_chapter) {{
                    badges.push('<span class="badge chapter">Chapter</span>');
                }}
                if (repo.archived) {{
                    badges.push('<span class="badge archived">Archived</span>');
                }}
                if (repo.language && repo.language !== 'N/A') {{
                    badges.push(`<span class="badge language">${{repo.language}}</span>`);
                }}
                
                // Add activity indicator badges
                if (yearsSinceUpdate >= 3) {{
                    badges.push('<span class="badge inactive-3yr" title="No activity in 3+ years">3yr+</span>');
                }} else if (yearsSinceUpdate >= 1) {{
                    badges.push('<span class="badge inactive-1yr" title="No activity in 1+ year">1yr+</span>');
                }}
                
                // Only show bump button for repos not updated in over 1 year (and not archived)
                let bumpButton = '';
                if (yearsSinceUpdate >= 1) {{
                    bumpButton = repo.archived 
                        ? `<span class="bump-btn archived" title="Cannot bump archived repositories">🔔</span>`
                        : `<a href="${{getBumpIssueUrl(repo)}}" target="_blank" class="bump-btn" title="Create a reminder issue in this repository">🔔</a>`;
                }}
                
                // Generate sparkline
                const sparklineHtml = generateSparklineSVG(repo.sparkline, 80, 16);
                
                // Display title if different from name (escaped)
                const escapedTitle = escapeHtml(repo.title);
                const displayTitle = repo.title && repo.title !== repo.name ? 
                    `<div class="repo-title" title="${{escapedTitle}}">${{escapedTitle}}</div>` : '';
                
                // Display pitch if available (escaped)
                const escapedPitch = escapeHtml(repo.pitch);
                const pitchHtml = repo.pitch ? 
                    `<div class="repo-pitch" title="${{escapedPitch}}">${{escapedPitch}}</div>` : '';
                
                // Display tags (escaped)
                const tagsHtml = repo.tags && repo.tags.length > 0 ?
                    `<div class="repo-tags">${{repo.tags.slice(0, 5).map(tag => `<span class="badge tag">${{escapeHtml(tag)}}</span>`).join('')}}</div>` : '';
                
                // Escape description
                const escapedDesc = escapeHtml(repo.description) || 'No description';
                
                // Last commit section
                let lastCommitHtml = '';
                if (repo.last_commit_message || repo.last_commit_author) {{
                    const avatarHtml = repo.last_commit_avatar_url
                        ? `<img class="last-commit-avatar" src="${{escapeHtml(repo.last_commit_avatar_url)}}" alt="${{escapeHtml(repo.last_commit_author)}}" loading="lazy">`
                        : '💬';
                    const authorHtml = repo.last_commit_author
                        ? (repo.last_commit_author_url
                            ? `<a class="last-commit-author" href="${{escapeHtml(repo.last_commit_author_url)}}" target="_blank" rel="noopener noreferrer">${{escapeHtml(repo.last_commit_author)}}</a>`
                            : `<span class="last-commit-author">${{escapeHtml(repo.last_commit_author)}}</span>`)
                        : '';
                    lastCommitHtml = `<div class="last-commit">
                        ${{avatarHtml}}
                        ${{authorHtml}}
                        <span class="last-commit-message" title="${{escapeHtml(repo.last_commit_message)}}">${{escapeHtml(repo.last_commit_message)}}</span>
                    </div>`;
                }}
                
                return `
                    <div class="repo-item ${{repo.archived ? 'archived' : ''}}">
                        <div class="repo-header">
                            <div class="repo-name">
                                <a href="${{repo.html_url}}" target="_blank">${{escapeHtml(repo.name)}}</a>
                                ${{displayTitle}}
                            </div>
                            <div class="repo-badges">
                                ${{badges.join('')}}
                                ${{bumpButton}}
                            </div>
                        </div>
                        ${{pitchHtml || `<div class="repo-description">${{escapedDesc}}</div>`}}
                        ${{tagsHtml}}
                        <div class="repo-meta">
                            <span class="meta-item">⭐ ${{repo.stargazers_count}}</span>
                            <span class="meta-item">🔱 ${{repo.forks_count}}</span>
                            <span class="meta-item">📝 ${{repo.open_issues_count}}</span>
                            ${{repo.open_prs_count > 0 ? `<span class="meta-item prs">🔀 ${{repo.open_prs_count}} PRs</span>` : ''}}
                            <span class="meta-item">📅 ${{getTimeAgo(repo.updated_at)}}</span>
                        </div>
                        ${{lastCommitHtml}}
                        <div class="sparkline-container">
                            <span class="sparkline-label">📈 Activity (52 weeks):</span>
                            ${{sparklineHtml}}
                            <span class="activity-score" title="Total commits in the last 52 weeks">Score: ${{repo.activity_score}}</span>
                        </div>
                    </div>
                `;
            }}).join('');
            
            document.getElementById('visibleCount').textContent = filtered.length;
        }}
        
        function renderTable(filtered) {{
            const container = document.getElementById('repoList');
            container.className = '';
            
            if (filtered.length === 0) {{
                container.innerHTML = '<div class="no-results">No repositories match your criteria</div>';
                document.getElementById('visibleCount').textContent = '0';
                return;
            }}
            
            const columns = [
                {{ key: 'name',        label: 'Name',        sortKey: 'name' }},
                {{ key: 'type',        label: 'Type',        sortKey: null }},
                {{ key: 'description', label: 'Description', sortKey: null }},
                {{ key: 'tags',        label: 'Tags',        sortKey: null }},
                {{ key: 'language',    label: 'Language',    sortKey: null }},
                {{ key: 'level',       label: 'Level',       sortKey: 'level' }},
                {{ key: 'stars',       label: '⭐ Stars',    sortKey: 'stars' }},
                {{ key: 'forks',       label: '🔱 Forks',   sortKey: 'forks' }},
                {{ key: 'issues',      label: '📝 Issues',  sortKey: 'issues' }},
                {{ key: 'prs',         label: '🔀 PRs',     sortKey: 'prs' }},
                {{ key: 'activity',    label: '📈 Activity', sortKey: 'activity' }},
                {{ key: 'updated',     label: '📅 Updated',  sortKey: 'updated' }},
                {{ key: 'created',     label: '📅 Created',  sortKey: 'created' }},
                {{ key: 'lastcommit',  label: '💬 Last Commit', sortKey: null }},
                {{ key: 'bump',        label: 'Bump',        sortKey: null }},
            ];
            
            const thead = columns.map(col => {{
                if (col.sortKey) {{
                    const isActive = currentSort.startsWith(col.sortKey + '-');
                    const arrow = getSortArrow(col.sortKey);
                    return `<th class="sortable${{isActive ? ' sort-active' : ''}}" onclick="sortByColumn('${{col.sortKey}}')">${{col.label}} <span class="sort-arrow">${{arrow}}</span></th>`;
                }}
                return `<th>${{col.label}}</th>`;
            }}).join('');
            
            const rows = filtered.map(repo => {{
                const yearsSinceUpdate = getYearsSinceUpdate(repo.updated_at);
                
                // Type badges
                const typeBadges = [];
                if (repo.is_project) typeBadges.push('<span class="badge project">Project</span>');
                if (repo.is_chapter) typeBadges.push('<span class="badge chapter">Chapter</span>');
                if (repo.archived) typeBadges.push('<span class="badge archived">Archived</span>');
                if (yearsSinceUpdate >= 3) typeBadges.push('<span class="badge inactive-3yr" title="No activity in 3+ years">3yr+</span>');
                else if (yearsSinceUpdate >= 1) typeBadges.push('<span class="badge inactive-1yr" title="No activity in 1+ year">1yr+</span>');
                
                // Level badge
                let levelCell = '';
                if (repo.level !== null && repo.level !== undefined) {{
                    const levelClass = repo.level >= 4 ? 'level-4' : repo.level >= 3 ? 'level-3' : repo.level >= 2 ? 'level-2' : 'level-1';
                    levelCell = `<span class="badge level ${{levelClass}}" title="OWASP Level ${{repo.level}}">L${{repo.level}}</span>`;
                }}
                
                // Language
                const langCell = repo.language && repo.language !== 'N/A' ? `<span class="badge language">${{escapeHtml(repo.language)}}</span>` : '';
                
                // Description (prefer pitch, fall back to description)
                const descText = repo.pitch || repo.description || 'No description';
                
                // Tags (up to 4)
                const tagsCell = repo.tags && repo.tags.length > 0
                    ? repo.tags.slice(0, 4).map(t => `<span class="badge tag">${{escapeHtml(t)}}</span>`).join(' ')
                    : '';
                
                // Sparkline
                const sparklineHtml = generateSparklineSVG(repo.sparkline, 60, 14);
                
                // Bump button
                let bumpButton = '';
                if (yearsSinceUpdate >= 1) {{
                    bumpButton = repo.archived
                        ? `<span class="bump-btn archived" title="Cannot bump archived repositories">🔔</span>`
                        : `<a href="${{getBumpIssueUrl(repo)}}" target="_blank" class="bump-btn" title="Create a reminder issue in this repository">🔔</a>`;
                }}
                
                // Title (if different from name)
                const titleHtml = repo.title && repo.title !== repo.name
                    ? `<div class="repo-title" title="${{escapeHtml(repo.title)}}">${{escapeHtml(repo.title)}}</div>`
                    : '';
                
                // Last commit cell
                let lastCommitCell = '';
                if (repo.last_commit_message || repo.last_commit_author) {{
                    const avatarHtml = repo.last_commit_avatar_url
                        ? `<img class="last-commit-avatar" src="${{escapeHtml(repo.last_commit_avatar_url)}}" alt="${{escapeHtml(repo.last_commit_author)}}" loading="lazy"> `
                        : '';
                    const authorHtml = repo.last_commit_author
                        ? (repo.last_commit_author_url
                            ? `<a class="last-commit-author" href="${{escapeHtml(repo.last_commit_author_url)}}" target="_blank" rel="noopener noreferrer">${{escapeHtml(repo.last_commit_author)}}</a>: `
                            : `<span class="last-commit-author">${{escapeHtml(repo.last_commit_author)}}</span>: `)
                        : '';
                    lastCommitCell = `<div class="last-commit-cell">
                        ${{avatarHtml}}<span class="last-commit-cell-text" title="${{escapeHtml(repo.last_commit_author + (repo.last_commit_message ? ': ' + repo.last_commit_message : ''))}}">${{authorHtml}}${{escapeHtml(repo.last_commit_message)}}</span>
                    </div>`;
                }}
                
                return `<tr class="${{repo.archived ? 'archived' : ''}}">
                    <td><a href="${{repo.html_url}}" target="_blank" class="table-name-link">${{escapeHtml(repo.name)}}</a>${{titleHtml}}</td>
                    <td><div style="display:flex;gap:3px;flex-wrap:wrap">${{typeBadges.join('')}}</div></td>
                    <td><div class="table-desc" title="${{escapeHtml(descText)}}">${{escapeHtml(descText)}}</div></td>
                    <td><div style="display:flex;gap:3px;flex-wrap:wrap">${{tagsCell}}</div></td>
                    <td>${{langCell}}</td>
                    <td>${{levelCell}}</td>
                    <td class="table-num">${{repo.stargazers_count}}</td>
                    <td class="table-num">${{repo.forks_count}}</td>
                    <td class="table-num">${{repo.open_issues_count}}</td>
                    <td class="table-num">${{repo.open_prs_count || 0}}</td>
                    <td style="white-space:nowrap">${{sparklineHtml}} <span style="font-size:11px;font-weight:600;color:#E10101">${{repo.activity_score}}</span></td>
                    <td style="white-space:nowrap;font-size:12px">${{getTimeAgo(repo.updated_at)}}</td>
                    <td style="white-space:nowrap;font-size:12px">${{formatDate(repo.created_at)}}</td>
                    <td>${{lastCommitCell}}</td>
                    <td>${{bumpButton}}</td>
                </tr>`;
            }}).join('');
            
            container.innerHTML = `<div class="table-wrapper"><table class="repo-table"><thead><tr>${{thead}}</tr></thead><tbody>${{rows}}</tbody></table></div>`;
            document.getElementById('visibleCount').textContent = filtered.length;
        }}
        
        function renderRepos() {{
            const sorted = sortRepos(repos, currentSort);
            const filtered = filterRepos(sorted);
            if (viewMode === 'table') {{
                renderTable(filtered);
            }} else {{
                renderCards(filtered);
            }}
        }}
        
        function updateStats() {{
            const totalRepos = repos.length;
            const archivedRepos = repos.filter(r => r.archived).length;
            const activeRepos = totalRepos - archivedRepos;
            
            const totalProjects = repos.filter(r => r.is_project).length;
            const archivedProjects = repos.filter(r => r.is_project && r.archived).length;
            const activeProjects = totalProjects - archivedProjects;
            
            const totalChapters = repos.filter(r => r.is_chapter).length;
            const archivedChapters = repos.filter(r => r.is_chapter && r.archived).length;
            const activeChapters = totalChapters - archivedChapters;
            
            // Activity-based counts
            const activeWithinYear = repos.filter(r => getYearsSinceUpdate(r.updated_at) < 1).length;
            const olderThan1Year = repos.filter(r => getYearsSinceUpdate(r.updated_at) >= 1).length;
            const olderThan3Years = repos.filter(r => getYearsSinceUpdate(r.updated_at) >= 3).length;
            
            document.getElementById('totalCount').textContent = totalRepos;
            document.getElementById('visibleCount').textContent = totalRepos;
            document.getElementById('activeReposCount').textContent = activeRepos;
            document.getElementById('archivedReposCount').textContent = archivedRepos;
            
            document.getElementById('projectCount').textContent = totalProjects;
            document.getElementById('activeProjectsCount').textContent = activeProjects;
            document.getElementById('archivedProjectsCount').textContent = archivedProjects;
            
            document.getElementById('chapterCount').textContent = totalChapters;
            document.getElementById('activeChaptersCount').textContent = activeChapters;
            document.getElementById('archivedChaptersCount').textContent = archivedChapters;
            
            // Update activity-based counts
            document.getElementById('activeYearCount').textContent = activeWithinYear;
            document.getElementById('inactive1yrCount').textContent = olderThan1Year;
            document.getElementById('inactive3yrCount').textContent = olderThan3Years;
        }}
        
        // Event listeners
        document.getElementById('searchInput').addEventListener('input', (e) => {{
            searchTerm = e.target.value;
            renderRepos();
        }});
        
        // Sort button event listeners
        document.querySelectorAll('.sort-btn').forEach(btn => {{
            btn.addEventListener('click', (e) => {{
                document.querySelectorAll('.sort-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                currentSort = e.target.dataset.sort;
                renderRepos();
            }});
        }});
        
        function renderCreationChart() {{
            const yearCounts = {{}};
            repos.forEach(repo => {{
                if (repo.created_at) {{
                    const year = new Date(repo.created_at).getFullYear();
                    yearCounts[year] = (yearCounts[year] || 0) + 1;
                }}
            }});
            
            const years = Object.keys(yearCounts).sort();
            if (years.length === 0) return;
            
            const counts = years.map(y => yearCounts[y]);
            const maxCount = Math.max(...counts);
            
            const barWidth = 44;
            const barGap = 10;
            const chartHeight = 130;
            const topPadding = 20;
            const labelHeight = 22;
            const svgWidth = years.length * (barWidth + barGap) + barGap;
            const svgHeight = topPadding + chartHeight + labelHeight;
            
            const hasSelection = creationYearFilter !== null;
            
            const bars = years.map((year, i) => {{
                const count = yearCounts[year];
                const barH = maxCount > 0 ? Math.max(2, (count / maxCount) * chartHeight) : 2;
                const x = barGap + i * (barWidth + barGap);
                const y = topPadding + chartHeight - barH;
                const isSelected = hasSelection && creationYearFilter === parseInt(year);
                const barClass = isSelected ? 'creation-chart-bar creation-chart-bar-selected' : 'creation-chart-bar';
                const labelColor = isSelected ? '#a00000' : '#475569';
                const labelWeight = isSelected ? '700' : 'normal';
                const tooltipText = `${{year}}: ${{count}} ${{count === 1 ? 'repository' : 'repositories'}} — click to ${{isSelected ? 'clear filter' : 'filter by this year'}}`;
                return `<g class="creation-chart-bar-group" onclick="setCreationYearFilter(${{year}})" role="button" tabindex="0" aria-label="Filter by ${{year}}: ${{count}} ${{count === 1 ? 'repository' : 'repositories'}}">
                    <rect class="${{barClass}}" x="${{x}}" y="${{y}}" width="${{barWidth}}" height="${{barH}}" rx="3">
                        <title>${{tooltipText}}</title>
                    </rect>
                    <text x="${{x + barWidth / 2}}" y="${{y - 5}}" text-anchor="middle" font-size="11" fill="#0f172a" font-weight="600" pointer-events="none">${{count}}</text>
                    <text x="${{x + barWidth / 2}}" y="${{topPadding + chartHeight + 16}}" text-anchor="middle" font-size="11" fill="${{labelColor}}" font-weight="${{labelWeight}}" pointer-events="none">${{year}}</text>
                </g>`;
            }}).join('');
            
            const svgClass = hasSelection ? 'creation-chart-has-selection' : '';
            const svg = `<svg class="${{svgClass}}" width="${{svgWidth}}" height="${{svgHeight}}" viewBox="0 0 ${{svgWidth}} ${{svgHeight}}" role="img" aria-label="Bar chart of new repositories created per year">
                <title>New repositories created per year</title>
                <line x1="0" y1="${{topPadding + chartHeight}}" x2="${{svgWidth}}" y2="${{topPadding + chartHeight}}" stroke="#e2e8f0" stroke-width="1"/>
                ${{bars}}
            </svg>`;
            
            document.getElementById('creationChartSvg').innerHTML = svg;
            
            // Update filter label
            const label = document.getElementById('creationYearFilterLabel');
            if (hasSelection) {{
                document.getElementById('creationYearFilterValue').textContent = creationYearFilter;
                label.style.display = 'inline';
            }} else {{
                label.style.display = 'none';
            }}
        }}
        
        // Initial render
        updateStats();
        renderCreationChart();
        renderRepos();
    </script>
</body>
</html>
"""
    
    return html

def _fetch_repo_extra_data(repo: Dict, org: str, token: str, fetch_sparklines: bool, fetch_metadata: bool) -> Dict:
    """Fetch all extra data for a single repository (sparkline + metadata).

    Modifies *repo* in-place and also returns it, so it can be used both as a
    concurrent.futures worker target and for direct calls.

    Parameters:
        repo: Repository dict from the GitHub API (modified in place).
        org: GitHub organisation name, used as fallback owner.
        token: GitHub API token; pass empty string to skip authenticated calls.
        fetch_sparklines: Whether to fetch 52-week participation stats.
        fetch_metadata: Whether to fetch index.md, PR count, and last commit.

    Returns:
        The same *repo* dict with sparkline/index_md/open_prs_count/last_commit set.
    """
    owner = repo.get("owner", {}).get("login", org)
    repo_name = repo.get("name", "")

    if not repo_name:
        repo["sparkline"] = []
        repo["index_md"] = {}
        repo["open_prs_count"] = 0
        repo["last_commit"] = {}
        return repo

    if fetch_sparklines and token:
        sparkline_data = fetch_participation_stats(owner, repo_name, token)
        repo["sparkline"] = sparkline_data if sparkline_data else []
    else:
        repo["sparkline"] = []

    if fetch_metadata and token:
        repo["index_md"] = fetch_index_md(owner, repo_name, token) or {}
        repo["open_prs_count"] = fetch_open_prs_count(owner, repo_name, token)
        repo["last_commit"] = fetch_last_commit(owner, repo_name, token) or {}
    else:
        repo["index_md"] = {}
        repo["open_prs_count"] = 0
        repo["last_commit"] = {}

    return repo


def main():
    org = os.environ.get('GITHUB_ORG', 'owasp')
    token = os.environ.get('GITHUB_TOKEN', '')
    output_file = os.environ.get('OUTPUT_FILE', 'index.html')
    fetch_sparklines = os.environ.get('FETCH_SPARKLINES', 'true').lower() == 'true'
    fetch_metadata = os.environ.get('FETCH_METADATA', 'true').lower() == 'true'
    max_workers = 20
    try:
        max_workers = int(os.environ.get('MAX_WORKERS', '20'))
    except ValueError:
        print("Warning: MAX_WORKERS is not a valid integer, defaulting to 20", file=sys.stderr)

    print(f"Fetching repositories for organization: {org}")
    repos = fetch_repos(org, token)
    print(f"Found {len(repos)} repositories")

    if (fetch_sparklines and token) or (fetch_metadata and token):
        print(f"Fetching extra data for {len(repos)} repositories using {max_workers} parallel workers...")
        completed = 0
        total = len(repos)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    _fetch_repo_extra_data, repo, org, token, fetch_sparklines, fetch_metadata
                ): repo
                for repo in repos
            }
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()  # re-raises any exception; repo dict is modified in place
                except Exception as exc:
                    failed_repo = futures[future]
                    print(f"  Warning: failed to fetch extra data for {failed_repo.get('name', '?')}: {exc}", file=sys.stderr)
                completed += 1
                if completed % 100 == 0 or completed == total:
                    print(f"  Completed {completed}/{total}")

        print(f"  Done fetching extra data for {total} repositories")
    else:
        print("Skipping extra data fetch (no token or both FETCH_SPARKLINES and FETCH_METADATA are false)")
        for repo in repos:
            repo["sparkline"] = []
            repo["index_md"] = {}
            repo["open_prs_count"] = 0
            repo["last_commit"] = {}

    print("Generating HTML page...")
    html = generate_html(repos, org.upper())

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"HTML page generated: {output_file}")

if __name__ == "__main__":
    main()