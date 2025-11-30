import { formatDate, showAlert } from "../libs/utils.js";
import { IS_EDITABLE, OWNER, REPO } from "../libs/constants.js";
import { getRepoContent, updateRepoContent } from "../libs/api.js";

export function renderMentorInfo(config) {
    const mentorDetails = document.getElementById('mentor-details');
    const feedbackList = document.getElementById('feedback-list');
    const feedback = config.feedback || [];

    if (!feedback) feedback = [];

    const localConfig = {
        mentor: {
            avatar: config.mentor.avatar,
            name: config.mentor.name,
            role: config.mentor.role,
            email: config.mentor.email,
        },
        feedback: config.feedback || []
    }

    feedback.forEach((item) => {
        if (!item._id) {
            item._id = Date.now() + Math.random();
        }
    });

    if (!IS_EDITABLE) {
        mentorDetails.innerHTML = `
            <div class="mentor-card">
                <img src="${config.mentor.avatar}" alt="${config.mentor.name}" class="mentor-avatar">
                <div class="mentor-info">
                    <h3>${config.mentor.name}</h3>
                    <p>${config.mentor.role}</p>
                    ${config.mentor.email ? `<p><i class="fas fa-envelope"></i> ${config.mentor.email}</p>` : ''}
                </div>
            </div>
        `;

        if (feedback.length > 0) {
            feedbackList.innerHTML = feedback.map(item => `
                <div class="feedback-item">
                    <div class="feedback-header">
                        <strong>${item.from || config.mentor.name}</strong>
                        <span class="feedback-date">${formatDate(item.date)}</span>
                    </div>
                    <div class="feedback-content">${item.content}</div>
                </div>
            `).join('');
        } else {
            feedbackList.innerHTML = `<p class="text-secondary">No feedback yet.</p>`;
        }

        return;
    }

    mentorDetails.innerHTML = `
        <div class="mentor-card flex gap-4 items-start">
            <form id="mentorForm">
                <input 
                    type="text"
                    class="input-field"
                    value="${localConfig.mentor.avatar}"
                    data-field="avatar"
                    placeholder="Mentor Avatar URL"
                />

                <input 
                    type="text"
                    class="input-field mt-2"
                    value="${localConfig.mentor.name}"
                    data-field="name"
                    placeholder="Mentor Name"
                />

                <input 
                    type="text"
                    class="input-field mt-2"
                    value="${localConfig.mentor.role}"
                    data-field="role"
                    placeholder="Mentor Role"
                />

                <input 
                    type="text"
                    class="input-field mt-2"
                    value="${localConfig.mentor.email || ''}"
                    data-field="email"
                    placeholder="Mentor Email"
                />
            </form>
        </div>
    `;

    const mentorForm = document.getElementById("mentorForm");
    mentorForm.addEventListener("input", (e) => {
        const field = e.target.name;
        const value = e.target.value;
        localConfig.mentor[field] = value;
    });

    // Feedback editable UI
    feedbackList.innerHTML = localConfig.feedback.map((item) => `
        <div class="feedback-item">
            <div class="feedback-header">
                <input 
                    type="text"
                    class="input-field small"
                    data-id="${item._id}"
                    data-field="from"
                    value="${item.from || ''}"
                    placeholder="From"
                />

                <input 
                    type="date"
                    class="input-field small"
                    data-id="${item._id}"
                    data-field="date"
                    value="${item.date || ''}"
                />
            </div>

            <textarea 
                class="text-area-field"
                data-id="${item._id}"
                data-field="content"
                placeholder="Feedback content"
            >${item.content || ''}</textarea>

            <button class="btn-danger mt-2" data-remove="${item._id}">Remove</button>
        </div>
    `).join('');

    feedbackList.innerHTML += `
        <div class="flex gap-3">
            <button class="btn-secondary w-full mt-4" id="addFeedback">+ Add Feedback</button>
            <button id="save-mentor-content" class="btn-primary w-full mt-4">Save</button>
        </div>
    `;

    const newFeedbackList = feedbackList.cloneNode(true);
    feedbackList.parentNode.replaceChild(newFeedbackList, feedbackList);

    newFeedbackList.addEventListener("input", (e) => {
        const feedbackId = e.target.getAttribute("data-id");
        const field = e.target.getAttribute("data-field");

        if (feedbackId && field) {
            const feedbackItem = feedback.find(f => f._id == feedbackId);
            if (feedbackItem) {
                feedbackItem[field] = e.target.value;
            }
        }
    });

    newFeedbackList.addEventListener("click", (e) => {
        const removeId = e.target.getAttribute("data-remove");
        if (removeId) {
            const feedbackIndex = feedback.findIndex(f => f._id == removeId);
            if (feedbackIndex !== -1) {
                feedback.splice(feedbackIndex, 1);
                renderMentorInfo(config, feedback);
            }
        }

        if (e.target.id === "addFeedback") {
            feedback.push({
                _id: Date.now() + Math.random(),
                from: config.mentor.name,
                date: "",
                content: ""
            });
            renderMentorInfo(config, feedback);
        }
    });

    const saveMentorButton = document.getElementById("save-mentor-content");
    saveMentorButton.addEventListener("click", async () => {
        const mentorJson = JSON.stringify(localConfig, null, 2);
        const contentResponse = await getRepoContent(OWNER, REPO, "data/mentor.json");
        console.log("repo", contentResponse);

        if (!contentResponse || !contentResponse.sha) {
            alert("Failed to fetch mentor content from repository.");
            return;
        }
        const response = await updateRepoContent(OWNER, REPO, "data/mentor.json", mentorJson, contentResponse.sha);
        showAlert(response, "Mentor details updated successfully!");
    })
}
