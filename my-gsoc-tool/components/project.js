import { getRepoContent, updateRepoContent } from "../libs/api.js";
import { IS_EDITABLE, OWNER, REPO } from "../libs/constants.js";
import { showAlert } from "../libs/utils.js";

// Render project info

export function renderProjectInfo(projectData) {
    const editSection = document.getElementById("project-edit-section");
    if (IS_EDITABLE) {
        const localConfig = {
            title: projectData.project.title,
            description: projectData.project.description,
            organization: projectData.project.organization,
            timeline: projectData.project.timeline,
            repository: projectData.project.repository || ""
        }
        editSection.innerHTML = `
        <form id="projectForm" class="rounded-xl p-6 space-y-8">
        <h2 class="text-lg">Edit Project Details</h2>
        <label class="flex flex-col">
            <span class="text-md font-medium mb-1">Project Title</span>
            <input value="${localConfig.title}" name="title" type="text" placeholder="Project Title" class="input-field" />
        </label>

        <label class="flex flex-col">
            <span class="text-md font-medium mb-1">Project Description</span>
            <input value="${localConfig.description}" name="description" type="text" placeholder="Brief description of your project" class="input-field" />
        </label>

        <label class="flex flex-col">
            <span class="text-md font-medium mb-1">Organization</span>
            <input value="${localConfig.organization}" name="organization" type="text" placeholder="Organization Name" class="input-field" />
        </label>

        <label class="flex flex-col">
            <span class="text-md font-medium mb-1">Timeline</span>
            <input  value="${localConfig.timeline}" name="timeline" type="text" placeholder="e.g., May 20XX - August 20XX" class="input-field" />
        </label>

        <button type="button" id="saveProjectBtn" class="btn btn-primary">Save Changes</button>
        </form>
    `;
        const projectForm = document.getElementById("projectForm");
        projectForm.addEventListener("input", (e) => {
            const field = e.target.name;
            const value = e.target.value;
            localConfig[field] = value;
        });

        const saveBtn = document.getElementById("saveProjectBtn");
        saveBtn.addEventListener("click", async () => {
            try {
                const jsonConfig = JSON.stringify({ project: localConfig }, null, 2);
                const contentResponse = await getRepoContent(OWNER, REPO, "data/project.json");
                if (!contentResponse) {
                    alert("Failed to fetch project details. Please try again later.");
                    return;
                }
                const res = await updateRepoContent(OWNER, REPO, "data/project.json", jsonConfig, contentResponse.sha);
                showAlert(res, "Project details updated successfully!");
            } catch (error) {
                console.error("Error updating project:", error);
                alert("Failed to update project details. Please try again.");
            }
        });
    }
    document.getElementById("project-title").textContent = projectData.project.title;
    document.getElementById("project-description").textContent = projectData.project.description;
    document.getElementById("organization").innerHTML = `
        <i class="fas fa-building"></i> Organization: ${projectData.project.organization}`;
    document.getElementById("timeline").innerHTML = `
        <i class="fas fa-calendar"></i> Timeline: ${projectData.project.timeline}`;
}
