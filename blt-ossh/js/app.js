
// Dark mode toggle
const darkToggle = document.getElementById('dark-toggle');
const html = document.documentElement;

// Check for saved theme preference or default to light mode
const currentTheme = localStorage.getItem('theme') || 'light';
if (currentTheme === 'dark') {
    html.classList.add('dark');
}

darkToggle.addEventListener('click', () => {
    html.classList.toggle('dark');
    const theme = html.classList.contains('dark') ? 'dark' : 'light';
    localStorage.setItem('theme', theme);
});

// Form submission
const form = document.getElementById('ossh-form');
const submitBtn = document.getElementById('submit-btn');
const btnText = document.getElementById('btn-text');
const loadingSpinner = document.getElementById('loading-spinner');
const errorMessage = document.getElementById('error-message');
const errorText = document.getElementById('error-text');
const usernameInput = document.getElementById('github-username');

form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const username = usernameInput.value.trim();

    if (!username) {
        showError('Please enter a GitHub username');
        return;
    }

    // Validate username format
    if (username.length > 39 || !/^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$/.test(username)) {
        showError('Please enter a valid GitHub username');
        return;
    }

    // Reset error state
    hideError();

    // Show loading state: disables form and displays "Loading repositories..." while fetching.
    submitBtn.disabled = true;
    btnText.textContent = 'Analyzing...';
    loadingSpinner.classList.remove('hidden');
    const loadingEl = document.getElementById('loading');
    if (loadingEl) loadingEl.style.display = 'block';

    try {
        // Fetch user profile from GitHub API
        const userResponse = await fetch(
            `https://api.github.com/users/${encodeURIComponent(username)}`,
            { headers: { Accept: 'application/vnd.github+json' } }
        );

        if (userResponse.status === 404) {
            throw new Error('GitHub user not found. Please check the username and try again.');
        }
        if (userResponse.status === 403) {
            throw new Error('GitHub API rate limit exceeded. Please wait a few minutes and try again.');
        }
        if (!userResponse.ok) {
            throw new Error(`GitHub API error (${userResponse.status}). Please try again later.`);
        }

        const userData = await userResponse.json();

        // Fetch user repositories
        const reposResponse = await fetch(
            `https://api.github.com/users/${encodeURIComponent(username)}/repos?sort=updated&per_page=100`,
            { headers: { Accept: 'application/vnd.github+json' } }
        );
        const reposData = reposResponse.ok ? await reposResponse.json() : [];

        // Build and display results
        const data = buildRecommendations(userData, reposData);
        displayResults(data);

    } catch (error) {
        console.error('Error:', error);
        showError(error.message || 'Failed to analyze GitHub profile. Please try again.');
    } finally {
        // Reset button state and hide loading indicator (on success or error)
        submitBtn.disabled = false;
        btnText.textContent = 'Find My Projects';
        loadingSpinner.classList.add('hidden');
        if (loadingEl) loadingEl.style.display = 'none';
    }
});

function buildRecommendations(userData, repos) {
    // Extract languages from repos (weighted by frequency)
    const languageCounts = {};
    repos.forEach(repo => {
        if (repo.language) {
            languageCounts[repo.language] = (languageCounts[repo.language] || 0) + 1;
        }
    });
    const languages = Object.keys(languageCounts)
        .sort((a, b) => languageCounts[b] - languageCounts[a])
        .slice(0, 10);

    const github_stats = {
        username: userData.login,
        name: userData.name || userData.login,
        avatar_url: userData.avatar_url,
        bio: userData.bio,
        public_repos: userData.public_repos,
        followers: userData.followers,
        following: userData.following,
        languages
    };

    // Top non-fork repos sorted by stars
    const recommended_repos = repos
        .filter(r => !r.fork && r.description)
        .sort((a, b) => b.stargazers_count - a.stargazers_count)
        .slice(0, 6)
        .map(r => ({
            name: r.full_name,
            description: r.description,
            stars: r.stargazers_count,
            url: r.html_url
        }));

    const recommended_communities = [
        {
            name: 'OWASP BLT',
            description: 'Bug Logging Tool — an open source security platform',
            members: '1,000+',
            url: 'https://github.com/OWASP-BLT/BLT'
        },
        {
            name: 'OWASP Foundation',
            description: 'The Open Web Application Security Project',
            members: '50,000+',
            url: 'https://owasp.org/'
        }
    ];

    const recommended_articles = [
        {
            title: 'How to Contribute to Open Source',
            category: 'Open Source',
            url: 'https://opensource.guide/how-to-contribute/'
        },
        {
            title: 'GitHub Skills',
            category: 'GitHub',
            url: 'https://skills.github.com/'
        }
    ];

    const recommended_discussion_channels = [
        {
            name: 'BLT Discussions',
            platform: 'GitHub',
            icon: 'fa-brands fa-github',
            url: 'https://github.com/OWASP-BLT/BLT/discussions'
        },
        {
            name: 'OWASP Slack',
            platform: 'Slack',
            icon: 'fa-brands fa-slack',
            url: 'https://owasp.org/slack/invite'
        },
        {
            name: 'Dev Community',
            platform: 'DEV.to',
            icon: 'fa-brands fa-dev',
            url: 'https://dev.to/'
        },
        {
            name: 'Stack Overflow',
            platform: 'Stack Overflow',
            icon: 'fa-brands fa-stack-overflow',
            url: 'https://stackoverflow.com/'
        }
    ];

    return {
        github_stats,
        recommended_repos,
        recommended_communities,
        recommended_articles,
        recommended_discussion_channels
    };
}

function showError(message) {
    errorText.textContent = message;
    errorMessage.classList.remove('hidden');
}

function hideError() {
    errorMessage.classList.add('hidden');
}

function displayResults(data) {
    const resultsSection = document.getElementById('results-section');
    const githubStats = data.github_stats;

    // Store data globally for profile creation
    window.currentUserData = data;

    // Populate GitHub Stats
    document.getElementById('user-avatar').src = githubStats.avatar_url || 'static/logo.png';
    document.getElementById('user-name').textContent = githubStats.name || githubStats.username;
    document.getElementById('user-bio').textContent = githubStats.bio || 'No bio available';
    document.getElementById('user-repos').textContent = githubStats.public_repos || 0;
    document.getElementById('user-followers').textContent = githubStats.followers || 0;
    document.getElementById('user-following').textContent = githubStats.following || 0;

    // Display languages
    const languagesContainer = document.getElementById('user-languages');
    languagesContainer.innerHTML = '';
    (githubStats.languages || []).forEach(lang => {
        const badge = document.createElement('span');
        badge.className = 'px-3 py-1 bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 rounded-full text-xs font-semibold';
        badge.textContent = lang;
        languagesContainer.appendChild(badge);
    });

    // Display recommended repositories
    const reposContainer = document.getElementById('recommended-repos');
    reposContainer.innerHTML = '';
    (data.recommended_repos || []).forEach(repo => {
        const repoCard = document.createElement('div');
        repoCard.className = 'surface-card rounded-xl p-5 hover:shadow-lg transition';
        repoCard.innerHTML = `
    <div class="flex items-start justify-between mb-3">
        <h4 class="font-bold text-gray-900 dark:text-white text-lg">${escapeHtml(repo.name)}</h4>
        <span class="text-xs bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400 px-2 py-1 rounded-full">
            <i class="fas fa-star"></i> ${repo.stars}
        </span>
    </div>
    <p class="text-sm text-gray-600 dark:text-gray-400 mb-4">${escapeHtml(repo.description)}</p>
    <a href="${escapeHtml(repo.url)}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-2 text-red-600 dark:text-red-400 font-semibold text-sm hover:underline">
        <i class="fab fa-github"></i> View Repository
    </a>
    `;
        reposContainer.appendChild(repoCard);
    });

    // Display recommended communities
    const communitiesContainer = document.getElementById('recommended-communities');
    communitiesContainer.innerHTML = '';
    (data.recommended_communities || []).forEach(community => {
        const communityCard = document.createElement('div');
        communityCard.className = 'surface-card rounded-xl p-5 hover:shadow-lg transition';
        communityCard.innerHTML = `
    <h4 class="font-bold text-gray-900 dark:text-white mb-2">${escapeHtml(community.name)}</h4>
    <p class="text-sm text-gray-600 dark:text-gray-400 mb-3">${escapeHtml(community.description)}</p>
    <div class="flex justify-between items-center">
        <span class="text-xs text-gray-500 dark:text-gray-400">
            <i class="fas fa-users"></i> ${escapeHtml(community.members)}
        </span>
        <a href="${escapeHtml(community.url)}" target="_blank" rel="noopener noreferrer" class="text-red-600 dark:text-red-400 font-semibold text-sm hover:underline">
            Visit <i class="fas fa-external-link-alt ml-1"></i>
        </a>
    </div>
    `;
        communitiesContainer.appendChild(communityCard);
    });

    // Display recommended articles
    const articlesContainer = document.getElementById('recommended-articles');
    articlesContainer.innerHTML = '';
    (data.recommended_articles || []).forEach(article => {
        const articleCard = document.createElement('div');
        articleCard.className = 'surface-card rounded-xl p-5 hover:shadow-lg transition';
        articleCard.innerHTML = `
    <div class="flex items-start gap-3">
        <div class="flex-shrink-0 w-10 h-10 bg-red-100 dark:bg-red-900/30 rounded-lg flex items-center justify-center">
            <i class="fas fa-file-alt text-red-600 dark:text-red-400"></i>
        </div>
        <div class="flex-1">
            <h4 class="font-semibold text-gray-900 dark:text-white mb-1">${escapeHtml(article.title)}</h4>
            <span class="text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 px-2 py-1 rounded">
                ${escapeHtml(article.category)}
            </span>
            <a href="${escapeHtml(article.url)}" target="_blank" rel="noopener noreferrer" class="block mt-2 text-red-600 dark:text-red-400 font-semibold text-sm hover:underline">
                Read More <i class="fas fa-arrow-right ml-1"></i>
            </a>
        </div>
    </div>
    `;
        articlesContainer.appendChild(articleCard);
    });

    // Display discussion channels
    const channelsContainer = document.getElementById('discussion-channels');
    channelsContainer.innerHTML = '';
    (data.recommended_discussion_channels || []).forEach(channel => {
        const channelCard = document.createElement('div');
        channelCard.className = 'surface-card rounded-xl p-5 text-center hover:shadow-lg transition';
        channelCard.innerHTML = `
    <div class="text-3xl mb-3">
        <i class="${escapeHtml(channel.icon)} text-red-600 dark:text-red-400"></i>
    </div>
    <h4 class="font-semibold text-gray-900 dark:text-white text-sm mb-1">${escapeHtml(channel.name)}</h4>
    <p class="text-xs text-gray-500 dark:text-gray-400 mb-3">${escapeHtml(channel.platform)}</p>
    <a href="${escapeHtml(channel.url)}" target="_blank" rel="noopener noreferrer" class="text-red-600 dark:text-red-400 font-semibold text-xs hover:underline">
        Join <i class="fas fa-arrow-right ml-1"></i>
    </a>
    `;
        channelsContainer.appendChild(channelCard);
    });

    // Update GitHub profile link (in stats area)
    const profileLink = document.getElementById('github-profile-link');
    if (profileLink) {
        profileLink.href = `https://github.com/${encodeURIComponent(githubStats.username)}`;
        const span = profileLink.querySelector('span');
        if (span) span.textContent = `View ${githubStats.username}'s GitHub profile`;
    }

    // Update GitHub profile link (in button row)
    const viewProfileBtn = document.getElementById('view-github-profile');
    if (viewProfileBtn) {
        viewProfileBtn.href = `https://github.com/${encodeURIComponent(githubStats.username)}`;
    }

    // Show results section and scroll to it
    resultsSection.classList.remove('hidden');
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

    // Hide features section
    document.querySelector('.grid.gap-6.md\\:grid-cols-3.mb-12').classList.add('hidden');
    document.querySelector('.surface-card.rounded-2xl.p-8.sm\\:p-10').classList.add('hidden');
}

function escapeHtml(str) {
    if (str == null) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// Analyze another profile button handler
document.addEventListener('DOMContentLoaded', () => {
    const analyzeAnotherBtn = document.getElementById('analyze-another');
    if (analyzeAnotherBtn) {
        analyzeAnotherBtn.addEventListener('click', () => {
            // Hide results
            document.getElementById('results-section').classList.add('hidden');

            // Show form and features
            document.querySelector('.grid.gap-6.md\\:grid-cols-3.mb-12').classList.remove('hidden');
            document.querySelector('.surface-card.rounded-2xl.p-8.sm\\:p-10').classList.remove('hidden');

            // Clear form
            usernameInput.value = '';

            // Scroll to top
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }

    // Create profile button handler
    const createProfileBtn = document.getElementById('create-profile-btn');
    if (createProfileBtn) {
        createProfileBtn.addEventListener('click', () => {
            if (window.currentUserData) {
                const profileUrl = buildProfileIssueUrl(window.currentUserData);
                window.open(profileUrl, '_blank');
            }
        });
    }
});

function buildProfileIssueUrl(data) {
    const githubStats = data.github_stats;

    // Build the issue URL with pre-filled data
    const baseUrl = 'https://github.com/OWASP-BLT/BLT-OSSH/issues/new';
    const template = 'user_profile.yml';

    // Create URL parameters
    const params = new URLSearchParams({
        template: template,
        title: `[PROFILE] ${githubStats.name || githubStats.username}`,
        'github_username': githubStats.username,
        'display_name': githubStats.name || githubStats.username,
        'bio': githubStats.bio || `Open source developer passionate about ${githubStats.languages.slice(0, 3).join(', ')}`,
        'skills': githubStats.languages.join(', '),
        'looking_for': 'Looking to contribute to open source projects and connect with other developers'
    });

    return `${baseUrl}?${params.toString()}`;
}

// Set footer year
document.getElementById('footer-year').textContent = new Date().getFullYear();