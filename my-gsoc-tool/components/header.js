
import { getRepoContent, updateRepoContent } from "../libs/api.js";
import { IS_EDITABLE, OWNER, REPO } from "../libs/constants.js";
import { showAlert } from "../libs/utils.js";

// Render header
export function renderHeader(config) {
    document.getElementById('student-name').textContent = config.student.name;
    document.getElementById('student-bio').textContent = config.student.bio;
    document.getElementById('student-avatar').src = config.student.avatar;
    document.getElementById('student-avatar').alt = config.student.name;

    const socialLinks = document.getElementById('social-links');
    const socialEditSection = document.getElementById('social-edit-section');
    socialLinks.innerHTML = '';
    socialEditSection.innerHTML = '';

    const localConfig = {
        name: config.student.name,
        email: config.student.email,
        bio: config.student.bio,
        avatar: config.student.avatar,
        github: config.student.github,
        blog: config.student.blog,
        linkedin: config.student.linkedin
    }

    if (IS_EDITABLE) {
        socialEditSection.innerHTML += `
            <form id="studentForm" class="rounded-2xl p-6 space-y-7">
            <h2 class="text-2xl mb-10">Edit Details</h2>

            <div class="grid grid-cols-1 gap-5 sm:grid-cols-2">
                <label class="flex flex-col">
                <span class="text-md font-medium mb-1">Name</span>
                <input value="${localConfig.name}" name="name" type="text" placeholder="Your Name" class="input-field !text-white" />
                </label>

                <label class="flex flex-col">
                <span class="text-md font-medium mb-1">Email</span>
                <input value="${localConfig.email}" name="email" type="email" placeholder="your.email@example.com" required class="input-field !text-white" />
                </label>
            </div>

            <label class="flex flex-col">
                <span class="text-md font-medium mb-1">Bio</span>
                <input value="${localConfig.bio}" name="bio" type="text" placeholder="Google Summer of Code Contributor" class="input-field !text-white" />
            </label>

            <label class="flex flex-col">
                <span class="text-md font-medium mb-1">Avatar URL</span>
                <input value="${localConfig.avatar}" name="avatar" type="url" placeholder="https://github.com/YOUR-USERNAME.png" class="input-field !text-white" />
            </label>

            <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <label class="flex flex-col">
                <span class="text-md font-medium mb-1">GitHub</span>
                <input value="${localConfig.github}" name="github" type="url" placeholder="https://github.com/YOUR-USERNAME" class="input-field !text-white" />
                </label>

                <label class="flex flex-col">
                <span class="text-md font-medium mb-1">Blog</span>
                <input value="${localConfig.blog}" name="blog" type="url" placeholder="https://yourblog.dev" class="input-field !text-white" />
                </label>
            </div>

            <label class="flex flex-col">
                <span class="text-md font-medium mb-1">LinkedIn</span>
                <input value="${localConfig.linkedin}" name="linkedin" type="url" placeholder="https://linkedin.com/in/YOUR-PROFILE" class="input-field !text-white" />
            </label>


            <button id="saveProfileChangesBtn" type="button" class="btn-primary mt-4 w-full">Save Changes</button>
            </form>
        `;

        const studentForm = document.getElementById("studentForm");
        studentForm.addEventListener("input", (e) => {
            const field = e.target.name;
            const value = e.target.value;
            localConfig[field] = value;
        });

        const button = document.getElementById("saveProfileChangesBtn");
        button.addEventListener("click", async () => {
            const jsonString = JSON.stringify({ student: localConfig }, null, 2);
            console.log(jsonString);

            const repoContent = await getRepoContent(OWNER, REPO, "config.json");
            console.log("repo content", repoContent);

            const res = await updateRepoContent(OWNER, REPO, "config.json", jsonString, repoContent.sha);
            showAlert(res, "Profile details updated successfully!");
        });
    }

    if (config.student.github) {
        socialLinks.innerHTML += `
            <a href="${config.student.github}" target="_blank">
                <i class="fab fa-github"></i> GitHub
            </a>
        `;
    }

    if (config.student.linkedin) {
        socialLinks.innerHTML += `
            <a href="${config.student.linkedin}" target="_blank">
                <i class="fab fa-linkedin"></i> LinkedIn
            </a>
        `;
    }

    if (config.student.email) {
        socialLinks.innerHTML += `
            <a href="mailto:${config.student.email}">
                <i class="fas fa-envelope"></i> Email
            </a>
        `;
    }

    if (config.student.blog) {
        socialLinks.innerHTML += `
            <a href="${config.student.blog}" target="_blank">
                <i class="fas fa-blog"></i> Blog
            </a>
        `;
    }
}