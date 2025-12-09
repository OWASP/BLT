import { formatDate, showAlert } from "../libs/utils.js";
import { IS_EDITABLE, OWNER, REPO } from "../libs/constants.js";
import { getRepoContent, updateRepoContent } from "../libs/api.js";

export function renderMentorInfo(config) {
    const mentorDetails = document.getElementById('mentor-details');
    const feedbackList = document.getElementById('feedback-list');
    const feedback = config.feedback || [];

    if (!feedback) feedback = [];

    // Support both old single mentor format and new mentors array format
    const mentors = config.mentors || (config.mentor ? [config.mentor] : []);
    
    const localConfig = {
        mentors: mentors.map(mentor => ({
            avatar: mentor.avatar,
            name: mentor.name,
            role: mentor.role,
            email: mentor.email,
        })),
        feedback: config.feedback || []
    }

    // Helper function to get default mentor name
    const getDefaultMentorName = () => {
        return (localConfig.mentors[0] && localConfig.mentors[0].name) || '';
    };

    feedback.forEach((item) => {
        if (!item._id) {
            item._id = Date.now() + Math.random();
        }
    });

    if (!IS_EDITABLE) {
        mentorDetails.innerHTML = localConfig.mentors.map((mentor, index) => `
            <div class="mentor-card">
                <img src="${mentor.avatar}" alt="${mentor.name}" class="mentor-avatar">
                <div class="mentor-info">
                    <h3>${mentor.name}</h3>
                    <p>${mentor.role}</p>
                    ${mentor.email ? `<p><i class="fas fa-envelope"></i> ${mentor.email}</p>` : ''}
                </div>
            </div>
        `).join('');

        if (feedback.length > 0) {
            feedbackList.innerHTML = feedback.map(item => `
                <div class="feedback-item">
                    <div class="feedback-header">
                        <strong>${item.from || getDefaultMentorName()}</strong>
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

    mentorDetails.innerHTML = localConfig.mentors.map((mentor, index) => `
        <div class="mentor-card flex gap-4 items-start mb-4">
            <form id="mentorForm${index}" class="w-full">
                <h4 class="text-lg font-semibold mb-2">Mentor ${index + 1}</h4>
                <input 
                    type="text"
                    class="input-field"
                    value="${mentor.avatar}"
                    data-mentor-index="${index}"
                    data-field="avatar"
                    placeholder="Mentor Avatar URL"
                />

                <input 
                    type="text"
                    class="input-field mt-2"
                    value="${mentor.name}"
                    data-mentor-index="${index}"
                    data-field="name"
                    placeholder="Mentor Name"
                />

                <input 
                    type="text"
                    class="input-field mt-2"
                    value="${mentor.role}"
                    data-mentor-index="${index}"
                    data-field="role"
                    placeholder="Mentor Role"
                />

                <input 
                    type="text"
                    class="input-field mt-2"
                    value="${mentor.email || ''}"
                    data-mentor-index="${index}"
                    data-field="email"
                    placeholder="Mentor Email"
                />
            </form>
        </div>
    `).join('');

    // Add event listeners to all mentor forms
    localConfig.mentors.forEach((mentor, index) => {
        const mentorForm = document.getElementById(`mentorForm${index}`);
        if (mentorForm) {
            mentorForm.addEventListener("input", (e) => {
                const mentorIndex = e.target.getAttribute("data-mentor-index");
                const field = e.target.getAttribute("data-field");
                if (mentorIndex && field) {
                    const index = parseInt(mentorIndex, 10);
                    if (!isNaN(index) && index >= 0 && index < localConfig.mentors.length) {
                        localConfig.mentors[index][field] = e.target.value;
                    }
                }
            });
        }
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
                from: getDefaultMentorName(),
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

        if (!contentResponse || !contentResponse.sha) {
            alert("Failed to fetch mentor content from repository.");
            return;
        }
        const response = await updateRepoContent(OWNER, REPO, "data/mentor.json", mentorJson, contentResponse.sha);
        showAlert(response, "Mentor details updated successfully!");
    })
}
