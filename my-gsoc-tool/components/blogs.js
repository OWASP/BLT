import { formatDate } from "../libs/utils.js";

export function renderBlogPosts(posts, config) {
    const blogList = document.getElementById('blog-posts');
    const blogLink = document.getElementById('blog-link');

    if (posts && posts.length > 0) {
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
        blogList.innerHTML = '<p style="color: var(--text-secondary);">No blog posts yet. Add your posts to data/blog-posts.json</p>';
    }

    if (config.student.blog) {
        blogLink.href = config.student.blog;
        blogLink.style.display = 'inline-block';
    }
}
