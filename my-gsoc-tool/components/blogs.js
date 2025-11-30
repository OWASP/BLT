import { formatDate, showAlert } from "../libs/utils.js";
import { IS_EDITABLE, OWNER, REPO } from "../libs/constants.js";
import { getRepoContent, updateRepoContent } from "../libs/api.js";

export function renderBlogPosts(posts, config) {
    const blogList = document.getElementById('blog-posts');
    const blogLink = document.getElementById('blog-link');

    if (!posts) posts = [];

    // Add unique IDs to posts if they don't exist
    posts.forEach((post, index) => {
        if (!post._id) {
            post._id = Date.now() + Math.random();
        }
    });

    if (!IS_EDITABLE) {
        if (posts.length > 0) {
            blogList.innerHTML = posts.map(post => `
                <div class="blog-post">
                    <h3 onclick="window.open('${post.url}', '_blank')">${post.title}</h3>
                    <div class="post-meta">
                        <i class="fas fa-calendar"></i> ${formatDate(post.date)}
                        ${post.readTime ? `| <i class="fas fa-clock"></i> ${post.readTime}` : ''}
                    </div>
                    <p>${post.excerpt}</p>
                </div>
            `).join('');
        } else {
            blogList.innerHTML = '<p style="color: var(--text-secondary);">No blog posts yet.</p>';
        }

        if (config.student.blog) {
            blogLink.href = config.student.blog;
            blogLink.style.display = 'inline-block';
        }

        return;
    }

    blogList.innerHTML = posts.map((post) => `
        <div class="blog-post editable-blog-post">
            <input 
                type="text" 
                class="input-field" 
                value="${post.title || ''}" 
                data-id="${post._id}" 
                data-field="title"
                placeholder="Post Title"
            />

            <div class="edit-inline">
                <input 
                    type="date" 
                    class="input-field small" 
                    value="${post.date || ''}" 
                    data-id="${post._id}" 
                    data-field="date"
                />
                <input 
                    type="text" 
                    class="input-field small" 
                    value="${post.readTime || ''}" 
                    data-id="${post._id}" 
                    data-field="readTime"
                    placeholder="Read Time"
                />
            </div>

            <input 
                type="text" 
                class="input-field" 
                value="${post.url || ''}" 
                data-id="${post._id}" 
                data-field="url"
                placeholder="Post URL"
            />

            <textarea 
                class="text-area-field" 
                data-id="${post._id}" 
                data-field="excerpt"
                placeholder="Short excerpt"
            >${post.excerpt || ''}</textarea>

            <button class="btn btn-danger" data-remove="${post._id}">Remove</button>
        </div>
    `).join('');

    blogList.innerHTML += `
        <button class="btn-secondary add-post-btn">+ Add New Blog Post</button>
    `;

    blogList.innerHTML += `
        <button id="save-posts-btn" class="btn-primary">Save</button>
    `;

    const savePostsBtn = document.getElementById('save-posts-btn');
    const blogJson = JSON.stringify(posts, null, 2);

    savePostsBtn.addEventListener('click', () => {
        const contentResponse = getRepoContent(OWNER, REPO, 'data/blog-posts.json');
        if (!contentResponse) {
            alert("Failed to fetch existing blog posts from GitHub.");
            return;
        }
        const response = updateRepoContent(OWNER, REPO, 'data/blog-posts.json', blogJson, contentResponse.sha);
        showAlert(response, "Blog posts updated successfully!");
    });

    // Remove existing event listeners to avoid duplicates
    const newBlogList = blogList.cloneNode(true);
    blogList.parentNode.replaceChild(newBlogList, blogList);

    // Add input event listener
    newBlogList.addEventListener("input", (e) => {
        const postId = e.target.getAttribute("data-id");
        const field = e.target.getAttribute("data-field");
        if (postId && field) {
            const post = posts.find(p => p._id == postId);
            if (post) {
                post[field] = e.target.value;
            }
        }
    });

    // Add click event listener for remove buttons
    newBlogList.addEventListener("click", (e) => {
        const removeId = e.target.getAttribute("data-remove");
        if (removeId) {
            const postIndex = posts.findIndex(p => p._id == removeId);
            if (postIndex !== -1) {
                posts.splice(postIndex, 1);
                renderBlogPosts(posts, config); // re-render
            }
        }

        // Handle add button
        if (e.target.classList.contains("add-post-btn")) {
            posts.push({
                _id: Date.now() + Math.random(),
                title: "",
                date: "",
                excerpt: "",
                url: "",
                readTime: ""
            });
            renderBlogPosts(posts, config);
        }
    });

    // Blog link as editable too
    if (config.student.blog) {
        blogLink.href = config.student.blog;
    }
}
