// doc ref: https://docs.github.com/en/rest/repos/contents?apiVersion=2022-11-28#create-or-update-file-contents

let token = null;
import { IS_EDITABLE } from "./constants.js";

export function getGitHubToken() {
    console.log("IS_EDITABLE", IS_EDITABLE);
    console.log("token", token);
    if (!IS_EDITABLE || token) return;
    token = prompt("Please enter your GitHub Personal Access Token (with repo scope) to enable saving changes:");
}

export const getRepoContent = async (owner, repo, path) => {
    try {
        if (!token) {
            alert("GitHub token not provided.");
            getGitHubToken();
            return null;
        }

        const response = await fetch(`https://api.github.com/repos/${owner}/${repo}/contents/${path}`, {
            headers: {
                'Accept': 'application/vnd.github+json',
                'Authorization': `Bearer ${token}`,
                'X-GitHub-Api-Version': '2022-11-28'
            }
        });
        if (!response.ok) {
            alert("Failed to fetch file content from GitHub:", response.statusText);
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
            alert("GitHub token not provided.");
            getGitHubToken();
            return { success: false }
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
                    email: 'my-gsoc-tool-bot@example.com',
                },
                content: encodedContent,
                sha: sha,
            }),
        });

        if (!response.ok) {
            alert("Failed to update file content on GitHub:", response.statusText);
            return { success: false };
        }

        const data = await response.json();
        return { success: true, data };
    } catch (error) {
        console.error("Error updating file content on GitHub:", error);
        return { success: false };
    }
}
