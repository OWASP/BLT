import { formatDate, showAlert } from "../libs/utils.js";
import { IS_EDITABLE, OWNER, REPO } from "../libs/constants.js";
import { getRepoContent, updateRepoContent } from "../libs/api.js";

export function renderWeeklyUpdates(updates) {
    const timeline = document.getElementById('weekly-updates');
    if (!updates) updates = [];

    updates.forEach((update) => {
        if (!update._id) {
            update._id = Date.now() + Math.random();
        }
    });

    if (!IS_EDITABLE) {
        if (updates.length > 0) {
            timeline.innerHTML = updates.map(update => `
                <div class="timeline-item">
                    <h4>${update.title}</h4>
                    <p>${update.summary}</p>
                    <div class="timeline-date">
                        <i class="fas fa-calendar"></i> ${formatDate(update.date)}
                    </div>
                </div>
            `).join('');
        } else {
            timeline.innerHTML = `<p class="text-secondary">No weekly updates yet.</p>`;
        }
        return;
    }

    timeline.innerHTML = updates.map((update) => `
        <div class="timeline-item blog-post editable-blog-post">
            
            <input 
                type="text"
                class="input-field"
                data-id="${update._id}"
                data-field="title"
                value="${update.title || ''}"
                placeholder="Week Title"
            />

            <textarea
                class="text-area-field"
                data-id="${update._id}"
                data-field="summary"
                placeholder="Summary"
            >${update.summary || ''}</textarea>

            <div class="edit-inline">
                <input 
                    type="date"
                    class="input-field small"
                    data-id="${update._id}"
                    data-field="date"
                    value="${update.date || ''}"
                />
            </div>

            <button class="btn-danger mt-2" data-remove="${update._id}">Remove</button>
        </div>
    `).join('');

    timeline.innerHTML += `
    <div class="flex gap-3">
        <button class="btn-secondary w-full mt-4" id="addWeeklyUpdate">
            + Add Weekly Update
        </button>
        <button id="save-weekly-updates" class="btn-primary w-full mt-4" id="addWeeklyUpdate">Save</button>
    </div>
    `;

    const newTimeline = timeline.cloneNode(true);
    timeline.parentNode.replaceChild(newTimeline, timeline);

    newTimeline.addEventListener("input", (e) => {
        const updateId = e.target.getAttribute("data-id");
        const field = e.target.getAttribute("data-field");

        if (updateId && field) {
            const update = updates.find(u => u._id == updateId);
            if (update) {
                update[field] = e.target.value;
            }
        }
    });

    newTimeline.addEventListener("click", (e) => {
        const removeId = e.target.getAttribute("data-remove");
        if (removeId) {
            const updateIndex = updates.findIndex(u => u._id == removeId);
            if (updateIndex !== -1) {
                updates.splice(updateIndex, 1);
                renderWeeklyUpdates(updates);
            }
        }


        if (e.target.id === "addWeeklyUpdate") {
            updates.push({
                _id: Date.now() + Math.random(),
                title: "",
                summary: "",
                date: ""
            });
            renderWeeklyUpdates(updates);
        }
    });

    const saveUpdatesButton = document.getElementById("save-weekly-updates")
    const blogJson = JSON.stringify(updates, null, 2);
    saveUpdatesButton.addEventListener("click", () => {
        const contentResponse = getRepoContent(OWNER, REPO, "data/blog-posts.json");
        if (!contentResponse || !contentResponse.sha) alert("Something went wrong, Cannot find the SHA for the file");
        const response = updateRepoContent(OWNER, REPO, "data/blog-posts.json", blogJson, contentResponse.sha);
        showAlert(response, "Updated blog content.")
    })
}
