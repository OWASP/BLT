import { formatDate } from "../libs/utils.js";
import { IS_EDITABLE } from "../libs/constants.js";

export function renderBlogPosts(posts, config) {
    const blogList = document.getElementById('blog-posts');
    const blogLink = document.getElementById('blog-link');

    if (!posts) posts = [];

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

        return; // stop here
    }


    blogList.innerHTML = posts.map((post, index) => `
        <div class="blog-post editable-blog-post">
            <input 
                type="text" 
                class="edit-input" 
                value="${post.title}" 
                data-index="${index}" 
                data-field="title"
                placeholder="Post Title"
            />

            <div class="edit-inline">
                <input 
                    type="date" 
                    class="edit-input small" 
                    value="${post.date}" 
                    data-index="${index}" 
                    data-field="date"
                />
                <input 
                    type="text" 
                    class="edit-input small" 
                    value="${post.readTime || ''}" 
                    data-index="${index}" 
                    data-field="readTime"
                    placeholder="Read Time"
                />
            </div>

            <input 
                type="text" 
                class="edit-input" 
                value="${post.url}" 
                data-index="${index}" 
                data-field="url"
                placeholder="Post URL"
            />

            <textarea 
                class="edit-textarea" 
                data-index="${index}" 
                data-field="excerpt"
                placeholder="Short excerpt"
            >${post.excerpt}</textarea>

            <button class="remove-btn" data-remove="${index}">Remove</button>
        </div>
    `).join('');

    // Add new post button
    blogList.innerHTML += `
        <button class="add-post-btn">+ Add New Blog Post</button>
    `;

    // Handle input changes
    blogList.addEventListener("input", (e) => {
        const index = e.target.getAttribute("data-index");
        const field = e.target.getAttribute("data-field");
        if (index !== null && field) {
            posts[index][field] = e.target.value;
        }
    });

    // Handle remove
    blogList.addEventListener("click", (e) => {
        const removeIndex = e.target.getAttribute("data-remove");
        if (removeIndex !== null) {
            posts.splice(removeIndex, 1);
            renderBlogPosts(posts, config); // re-render
        }
    });

    // Handle add post
    document.querySelector(".add-post-btn").addEventListener("click", () => {
        posts.push({
            title: "",
            date: "",
            excerpt: "",
            url: "",
            readTime: ""
        });
        renderBlogPosts(posts, config);
    });

    // Blog link as editable too
    if (config.student.blog) {
        blogLink.href = config.student.blog;
    }
}
