import { formatDate } from "../libs/utils.js";
import { IS_EDITABLE } from "../libs/constants.js";

export function renderMilestones(milestones) {
    const milestoneList = document.getElementById('milestones');
    if (!milestones) milestones = [];

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

    milestoneList.innerHTML = milestones.map((milestone, index) => `
        <div class="milestone-item bg-[var(--bg-color)] p-4 rounded-xl shadow-sm border border-[var(--border-color)]">

            <div class="edit-inline">
                <input 
                    type="text"
                    class="input-field small"
                    data-index="${index}"
                    data-field="icon"
                    value="${milestone.icon || ''}"
                    placeholder="Icon (e.g. trophy)"
                />

                <input 
                    type="date"
                    class="input-field small"
                    data-index="${index}"
                    data-field="date"
                    value="${milestone.date}"
                />
            </div>

            <input 
                type="text"
                class="input-field mt-2"
                data-index="${index}"
                data-field="title"
                value="${milestone.title}"
                placeholder="Milestone Title"
            />

            <textarea
                class="text-area-field mt-2"
                data-index="${index}"
                data-field="description"
                placeholder="Description"
            >${milestone.description}</textarea>

            <button class="btn-danger mt-3" data-remove="${index}">Remove</button>
        </div>
    `).join('');

    milestoneList.innerHTML += `
        <button class="btn-primary w-full mt-4" id="addMilestone">
            + Add Milestone
        </button>
    `;

    milestoneList.addEventListener("input", (e) => {
        const index = e.target.getAttribute("data-index");
        const field = e.target.getAttribute("data-field");

        if (index !== null && field) {
            milestones[index][field] = e.target.value;
        }
    });

    milestoneList.addEventListener("click", (e) => {
        const removeIndex = e.target.getAttribute("data-remove");
        if (removeIndex !== null) {
            milestones.splice(removeIndex, 1);
            renderMilestones(milestones);
        }
    });

    document.getElementById("addMilestone").addEventListener("click", () => {
        milestones.push({
            title: "",
            description: "",
            date: "",
            icon: "trophy",
        });
        renderMilestones(milestones);
    });
}
