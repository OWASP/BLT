import { formatDate } from "../libs/utils.js";
import { IS_EDITABLE } from "../libs/constants.js";

export function renderWeeklyUpdates(updates) {
    const timeline = document.getElementById('weekly-updates');
    if (!updates) updates = [];

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

    timeline.innerHTML = updates.map((update, index) => `
        <div class="timeline-item blog-post editable-blog-post">
            
            <input 
                type="text"
                class="input-field"
                data-index="${index}"
                data-field="title"
                value="${update.title}"
                placeholder="Week Title"
            />

            <textarea
                class="text-area-field"
                data-index="${index}"
                data-field="summary"
                placeholder="Summary"
            >${update.summary}</textarea>

            <div class="edit-inline">
                <input 
                    type="date"
                    class="input-field small"
                    data-index="${index}"
                    data-field="date"
                    value="${update.date}"
                />
            </div>

            <button class="btn-danger mt-2" data-remove="${index}">Remove</button>
        </div>
    `).join('');

    timeline.innerHTML += `
        <button class="btn-primary w-full mt-4" id="addWeeklyUpdate">
            + Add Weekly Update
        </button>
    `;

    timeline.addEventListener("input", (e) => {
        const index = e.target.getAttribute("data-index");
        const field = e.target.getAttribute("data-field");

        if (index !== null && field) {
            updates[index][field] = e.target.value;
        }
    });

    timeline.addEventListener("click", (e) => {
        const removeIndex = e.target.getAttribute("data-remove");
        if (removeIndex !== null) {
            updates.splice(removeIndex, 1);
            renderWeeklyUpdates(updates);
        }
    });

    document.getElementById("addWeeklyUpdate").addEventListener("click", () => {
        updates.push({
            title: "",
            summary: "",
            date: ""
        });
        renderWeeklyUpdates(updates);
    });
}
