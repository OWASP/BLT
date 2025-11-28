import { IS_EDITABLE } from "../libs/constants.js";

// Render project info

export function renderProjectInfo(config) {
  const editSection = document.getElementById("project-edit-section");
  if (IS_EDITABLE) {
    editSection.innerHTML = `
        <form id="projectForm" class="rounded-xl p-6 space-y-8">
        <h2 class="text-lg">Edit Project Details</h2>
        <label class="flex flex-col">
            <span class="text-md font-medium mb-1">Project Title</span>
            <input value="${config.project.title}" name="title" type="text" placeholder="Project Title" class="input-field" />
        </label>

        <label class="flex flex-col">
            <span class="text-md font-medium mb-1">Project Description</span>
            <input value="${config.project.description}" name="description" type="text" placeholder="Brief description of your project" class="input-field" />
        </label>

        <label class="flex flex-col">
            <span class="text-md font-medium mb-1">Organization</span>
            <input value="${config.project.organization}" name="organization" type="text" placeholder="Organization Name" class="input-field" />
        </label>

        <label class="flex flex-col">
            <span class="text-md font-medium mb-1">Timeline</span>
            <input  value="${config.project.timeline}" name="timeline" type="text" placeholder="e.g., May 20XX - August 20XX" class="input-field" />
        </label>
        </form>
    `;
  }
  document.getElementById("project-title").textContent = config.project.title;
  document.getElementById("project-description").textContent = config.project.description;
  document.getElementById("organization").innerHTML = `
        <i class="fas fa-building"></i> Organization: ${config.project.organization}
    `;
  document.getElementById("timeline").innerHTML = `
        <i class="fas fa-calendar"></i> Timeline: ${config.project.timeline}
    `;
}
