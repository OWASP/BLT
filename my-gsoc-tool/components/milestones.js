import { formatDate } from "../libs/utils.js";
import { IS_EDITABLE } from "../libs/constants.js";

export function renderMilestones(milestones) {
    const milestoneList = document.getElementById('milestones');
    if (!milestones) milestones = [];

    milestones.forEach((milestone) => {
        if (!milestone._id) {
            milestone._id = Date.now() + Math.random();
        }
    });

    if (!IS_EDITABLE) {
        if (milestones.length > 0) {
            milestoneList.innerHTML = milestones.map(milestone => `
                <div class="milestone-item">
                    <div class="milestone-icon">
                        <i class="fas fa-${milestone.icon || 'trophy'}"></i>
                    </div>
                    <div class="milestone-content">
                        <h4>${milestone.title}</h4>
                        <p>${milestone.description}</p>
                        <div class="milestone-date">
                            <i class="fas fa-calendar"></i> ${formatDate(milestone.date)}
                        </div>
                    </div>
                </div>
            `).join('');
        } else {
            milestoneList.innerHTML = `<p class="text-secondary">No milestones yet.</p>`;
        }

        return;
    }

    milestoneList.innerHTML = milestones.map((milestone) => `
        <div class="milestone-item blog-post editable-blog-post flex flex-col">

            <input 
                type="text"
                class="input-field mt-2"
                data-id="${milestone._id}"
                data-field="title"
                value="${milestone.title || ''}"
                placeholder="Milestone Title"
            />

            <textarea
                class="text-area-field mt-2"
                data-id="${milestone._id}"
                data-field="description"
                placeholder="Description"
            >${milestone.description || ''}</textarea>

            <button class="btn-danger mt-3" data-remove="${milestone._id}">Remove</button>
        </div>
    `).join('');

    milestoneList.innerHTML += `
        <button class="btn-primary w-full mt-4" id="addMilestone">
            + Add Milestone
        </button>
    `;

    const newMilestoneList = milestoneList.cloneNode(true);
    milestoneList.parentNode.replaceChild(newMilestoneList, milestoneList);

    newMilestoneList.addEventListener("input", (e) => {
        const milestoneId = e.target.getAttribute("data-id");
        const field = e.target.getAttribute("data-field");

        if (milestoneId && field) {
            const milestone = milestones.find(m => m._id == milestoneId);
            if (milestone) {
                milestone[field] = e.target.value;
            }
        }
    });

    newMilestoneList.addEventListener("click", (e) => {
        const removeId = e.target.getAttribute("data-remove");
        if (removeId) {
            const milestoneIndex = milestones.findIndex(m => m._id == removeId);
            if (milestoneIndex !== -1) {
                milestones.splice(milestoneIndex, 1);
                renderMilestones(milestones);
            }
        }

        if (e.target.id === "addMilestone") {
            milestones.push({
                _id: Date.now() + Math.random(),
                title: "",
                description: "",
                date: "",
                icon: "trophy",
            });
            renderMilestones(milestones);
        }
    });
}
