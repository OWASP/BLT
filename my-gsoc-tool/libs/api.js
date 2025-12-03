let token = null;
import { BRANCH, EMAIL, IS_EDITABLE } from "./constants.js";

export function getGitHubToken() {
    if (!IS_EDITABLE) return null;
    if (!token) {
        token = localStorage.getItem('github_token');
    }
    return token;
}

export function setGitHubToken(newToken) {
    token = newToken;
    if (newToken) {
        localStorage.setItem('github_token', newToken);
    } else {
        localStorage.removeItem('github_token');
    }
}

export function hasToken() {
    return !!localStorage.getItem('github_token');
}

export const getRepoContent = async (owner, repo, path) => {
    try {
        if (!token) {
            token = getGitHubToken();
            if (!token) {
                return null;
            }
        }

        const response = await fetch(`https://api.github.com/repos/${owner}/${repo}/contents/${path}?ref=${BRANCH}`, {
            headers: {
                'Accept': 'application/vnd.github+json',
                'Authorization': `Bearer ${token}`,
                'X-GitHub-Api-Version': '2022-11-28'
            }
        });
        if (!response.ok) {
            console.error(`Failed to fetch file content: ${response.status} ${response.statusText}`);
            return null;
        }
        const data = await response.json();
        const content = atob(data.content);
        return { content, sha: data.sha };
    } catch (error) {
        console.error("Error fetching file content from GitHub:", error);
        return null;
    }
}

export const updateRepoContent = async (owner, repo, path, content, sha) => {
    try {
        if (!token) {
            token = getGitHubToken();
            if (!token) {
                return { success: false };
            }
        }

        const encodedContent = btoa(content);
        const response = await fetch(`https://api.github.com/repos/${owner}/${repo}/contents/${path}`, {
            method: 'PUT',
            headers: {
                'Accept': 'application/vnd.github+json',
                'Authorization': `Bearer ${token}`,
                'X-GitHub-Api-Version': '2022-11-28'
            },
            body: JSON.stringify({
                message: 'chore: update config via MY-GSOC-TOOL',
                committer: {
                    name: 'MY-GSOC-TOOL Bot',
                    email: EMAIL,
                },
                content: encodedContent,
                sha: sha,
                branch: BRANCH
            }),
        });

        if (!response.ok) {
            console.error(`Failed to update file: ${response.status} ${response.statusText}`);
            return { success: false };
        }

        const data = await response.json();
        return { success: true, data };
    } catch (error) {
        console.error("Error updating file content on GitHub:", error);
        return { success: false };
    }
}
