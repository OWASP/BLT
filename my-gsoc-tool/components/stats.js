
import { formatDate, showAlert, updateLastUpdated } from "../libs/utils.js";
import { IS_EDITABLE, OWNER, REPO } from "../libs/constants.js";
import { getRepoContent, updateRepoContent } from "../libs/api.js";

export function renderGitHubStats(data) {
    document.getElementById('total-commits').textContent = data.stats.commits || 0;
    document.getElementById('total-prs').textContent = data.stats.pullRequests || 0;
    document.getElementById('total-issues').textContent = data.stats.issues || 0;
    document.getElementById('total-reviews').textContent = data.stats.reviews || 0;

    const contributionList = document.getElementById('contribution-list');
    if (data.contributions && data.contributions.length > 0) {
        contributionList.innerHTML = data.contributions.map(contrib => `
            <div class="contribution-item">
                <h4>${contrib.title}</h4>
                <p>${contrib.description}</p>
                <div class="date">
                    <i class="fas fa-clock"></i> ${formatDate(contrib.date)}
                    ${contrib.url ? `| <a href="${contrib.url}" target="_blank">View on GitHub</a>` : ''}
                </div>
            </div>
        `).join('');
    } else {
        contributionList.innerHTML = '<p style="color: var(--text-secondary);">No contributions data available yet. The GitHub Actions workflow will populate this automatically.</p>';
    }
}

export function renderCommunityParticipation(communityData) {
    const communityChannels = document.getElementById('slack-channels');
    const communityLink = document.getElementById('slack-link');
    const editSection = document.getElementById('community-edit-section');

    const community = communityData.community || { platformUrl: "", channels: [] };

    // Add unique IDs to channels if they don't exist
    community.channels.forEach((channel, index) => {
        if (typeof channel === 'string') {
            community.channels[index] = { name: channel, _id: Date.now() + Math.random() + index };
        } else if (!channel._id) {
            channel._id = Date.now() + Math.random();
        }
    });

    if (IS_EDITABLE && editSection) {
        editSection.innerHTML = `
            <form id="communityForm" class="rounded-xl p-6 space-y-6">
                <h2 class="text-lg">Edit Community Participation</h2>
                
                <label class="flex flex-col">
                    <span class="text-md font-medium mb-1">Platform URL</span>
                    <input 
                        value="${community.platformUrl}" 
                        name="platformUrl" 
                        type="url" 
                        placeholder="https://example.com" 
                        class="input-field" 
                    />
                </label>
                
                <div class="channels-section">
                    <label class="text-md font-medium mb-2 block">Community Channels</label>
                    <div id="channels-list"></div>
                    <button type="button" id="addChannelBtn" class="btn-secondary mt-2">+ Add Channel</button>
                    <button type="button" id="saveChannelBtn" class="btn-primary mt-2">Save</button>
                </div>
            </form>
        `;

        renderChannelsList(community);

        // Handle platform URL changes
        const communityForm = document.getElementById("communityForm");
        communityForm.addEventListener("input", (e) => {
            if (e.target.name === "platformUrl") {
                community.platformUrl = e.target.value;
            }
        });

        // Handle adding new channels
        document.getElementById("addChannelBtn").addEventListener("click", () => {
            community.channels.push({
                name: "",
                _id: Date.now() + Math.random()
            });
            renderChannelsList(community);
        });

        const saveCommunityButton = document.getElementById("saveChannelBtn")
        saveCommunityButton.addEventListener("click", async () => {
            const communityJson = JSON.stringify(community, null, 2);
            const contentResponse = await getRepoContent(OWNER, REPO, "data/community.json");
            if (!contentResponse || !contentResponse.sha) alert("Failed to update, Please try again after refresh !");
            const response = await updateRepoContent(OWNER, REPO, "data/community.json", communityJson, contentResponse.sha);
            showAlert(response);
        })
    }

    // Render read-only view
    if (community.channels && community.channels.length > 0) {
        communityChannels.innerHTML = community.channels.map(channel => {
            const channelName = typeof channel === 'string' ? channel : channel.name;
            return `
                <div class="channel-item">
                    <i class="fas fa-hashtag"></i>
                    <span>${channelName}</span>
                </div>
            `;
        }).join('');
    } else {
        communityChannels.innerHTML = '<p style="color: var(--text-secondary);">Configure your community channels in the data files</p>';
    }

    if (community.platformUrl) {
        communityLink.href = community.platformUrl;
        communityLink.style.display = 'inline-block';
        communityLink.innerHTML = '<i class="fas fa-external-link-alt"></i> Join Community Platform';
    }
}

// Helper function to render channels list in edit mode
function renderChannelsList(community) {
    const channelsList = document.getElementById('channels-list');
    if (!channelsList) return;

    channelsList.innerHTML = community.channels.map((channel) => `
        <div class="channel-edit-item flex items-center gap-2 mb-2">
            <input 
                type="text"
                class="input-field flex-1"
                value="${channel.name || ''}"
                data-id="${channel._id}"
                placeholder="Channel name"
            />
            <button 
                type="button" 
                class="btn-danger" 
                data-remove="${channel._id}"
            >Remove</button>
        </div>
    `).join('');

    // Remove existing event listeners to avoid duplicates
    const newChannelsList = channelsList.cloneNode(true);
    channelsList.parentNode.replaceChild(newChannelsList, channelsList);

    newChannelsList.addEventListener("input", (e) => {
        const channelId = e.target.getAttribute("data-id");
        if (channelId) {
            const channel = community.channels.find(c => c._id == channelId);
            if (channel) {
                channel.name = e.target.value;
            }
        }
    });

    newChannelsList.addEventListener("click", (e) => {
        const removeId = e.target.getAttribute("data-remove");
        if (removeId) {
            const channelIndex = community.channels.findIndex(c => c._id == removeId);
            if (channelIndex !== -1) {
                community.channels.splice(channelIndex, 1);
                renderChannelsList(community);
            }
        }
    });
}
