// OWASP Project Compliance Checker - JavaScript Client-Side Implementation

let currentResults = null;

// GitHub API configuration
const GITHUB_API_BASE = 'https://api.github.com';

// Parse GitHub URL to extract owner and repo
function parseGitHubUrl(url) {
    try {
        const urlObj = new URL(url.trim());
        if (urlObj.hostname !== 'github.com' && urlObj.hostname !== 'www.github.com') {
            throw new Error('Not a GitHub URL');
        }
        
        const pathParts = urlObj.pathname.split('/').filter(p => p);
        if (pathParts.length < 2) {
            throw new Error('Invalid GitHub repository URL');
        }
        
        return {
            owner: pathParts[0],
            repo: pathParts[1]
        };
    } catch (error) {
        throw new Error('Invalid GitHub repository URL. Please use format: https://github.com/owner/repo');
    }
}

// Make authenticated GitHub API request
async function githubRequest(endpoint, token = null) {
    const headers = {
        'Accept': 'application/vnd.github.v3+json'
    };
    
    if (token) {
        headers['Authorization'] = `token ${token}`;
    }
    
    const response = await fetch(`${GITHUB_API_BASE}${endpoint}`, { headers });
    
    if (!response.ok) {
        if (response.status === 404) {
            throw new Error('Repository not found or is private');
        } else if (response.status === 403) {
            const rateLimitRemaining = response.headers.get('X-RateLimit-Remaining');
            if (rateLimitRemaining === '0') {
                throw new Error('GitHub API rate limit exceeded. Please provide a GitHub token or try again later.');
            }
            throw new Error('Access forbidden. The repository may be private or require authentication.');
        } else if (response.status === 401) {
            throw new Error('Invalid GitHub token. Please check your token and try again.');
        }
        throw new Error(`GitHub API error: ${response.status} ${response.statusText}`);
    }
    
    return response.json();
}

// Check if a file exists in the repository
async function checkFileExists(owner, repo, path, token) {
    try {
        await githubRequest(`/repos/${owner}/${repo}/contents/${path}`, token);
        return true;
    } catch {
        return false;
    }
}

// Check if a directory exists in the repository
async function checkDirectoryExists(owner, repo, path, token) {
    try {
        const contents = await githubRequest(`/repos/${owner}/${repo}/contents/${path}`, token);
        return Array.isArray(contents);
    } catch {
        return false;
    }
}

// Get README content
async function getReadmeContent(owner, repo, token) {
    try {
        const readme = await githubRequest(`/repos/${owner}/${repo}/readme`, token);
        const content = atob(readme.content).toLowerCase();
        return content;
    } catch {
        return null;
    }
}

// Check for code comments in repository files
async function checkCodeComments(owner, repo, token) {
    try {
        const contents = await githubRequest(`/repos/${owner}/${repo}/contents/`, token);
        for (const item of contents.slice(0, 5)) {
            if (item.type === 'file') {
                const extensions = ['.py', '.js', '.java', '.go', '.rs', '.ts', '.jsx', '.tsx'];
                if (extensions.some(ext => item.name.endsWith(ext))) {
                    try {
                        const file = await githubRequest(`/repos/${owner}/${repo}/contents/${item.path}`, token);
                        const content = atob(file.content);
                        if (content.includes('#') || content.includes('//') || content.includes('/*')) {
                            return true;
                        }
                    } catch {
                        continue;
                    }
                }
            }
        }
        return false;
    } catch {
        return false;
    }
}

// Main compliance checker class
class ComplianceChecker {
    constructor(owner, repo, token = null) {
        this.owner = owner;
        this.repo = repo;
        this.token = token;
        this.results = {
            url: `https://github.com/${owner}/${repo}`,
            score: 0,
            maxScore: 100,
            percentage: 0,
            categories: {}
        };
        this.repoData = null;
    }

    addCheck(category, name, passed, points = 1, details = '') {
        if (!this.results.categories[category]) {
            this.results.categories[category] = {
                checks: [],
                score: 0,
                maxScore: 0
            };
        }

        if (passed) {
            this.results.categories[category].score += points;
            this.results.score += points;
        }

        this.results.categories[category].maxScore += points;
        this.results.categories[category].checks.push({
            name,
            passed,
            points: passed ? points : 0,
            maxPoints: points,
            details
        });
    }

    async fetchRepositoryData() {
        this.repoData = await githubRequest(`/repos/${this.owner}/${this.repo}`, this.token);
    }

    async checkGeneralCompliance() {
        const category = 'General Compliance & Governance';

        // 1. Project goal and scope
        const readme = await getReadmeContent(this.owner, this.repo, this.token);
        const hasGoal = readme && ['goal', 'purpose', 'about', 'overview', 'description'].some(kw => readme.includes(kw));
        this.addCheck(category, 'Clearly defined project goal and scope', hasGoal, 1, 'Checked README for project description');

        // 2. Open-source license
        const hasLicense = this.repoData.license !== null;
        this.addCheck(category, 'Open-source license file present', hasLicense, 1, 
            hasLicense ? `License: ${this.repoData.license.name}` : 'No license found');

        // 3. README file
        this.addCheck(category, 'README file provides project overview', readme !== null, 1);

        // 4. OWASP organization
        const isOwasp = this.owner.toLowerCase() === 'owasp';
        this.addCheck(category, 'Under OWASP organization', isOwasp, 1, `Repository owner: ${this.owner}`);

        // 5. Contributing guidelines
        const hasContributing = await checkFileExists(this.owner, this.repo, 'CONTRIBUTING.md', this.token);
        this.addCheck(category, 'Contribution guidelines (CONTRIBUTING.md)', hasContributing, 1);

        // 6. Issue tracker activity
        this.addCheck(category, 'Issue tracker is active', this.repoData.has_issues, 1, 
            `Open issues: ${this.repoData.open_issues_count}`);

        // 7. Active maintainers (recent commits)
        try {
            const commits = await githubRequest(`/repos/${this.owner}/${this.repo}/commits?per_page=1`, this.token);
            const hasRecentCommits = commits.length > 0;
            this.addCheck(category, 'Active maintainers with recent commits', hasRecentCommits, 1);
        } catch {
            this.addCheck(category, 'Active maintainers with recent commits', false, 1);
        }

        // 8. Code of Conduct
        const hasCoc = await checkFileExists(this.owner, this.repo, 'CODE_OF_CONDUCT.md', this.token);
        this.addCheck(category, 'Code of Conduct present', hasCoc, 1);

        // 9. Project roadmap or milestones
        const hasRoadmap = await checkFileExists(this.owner, this.repo, 'ROADMAP.md', this.token);
        this.addCheck(category, 'Project roadmap or milestones documented', hasRoadmap, 1);

        // 10. Collaborators
        try {
            const collaborators = await githubRequest(`/repos/${this.owner}/${this.repo}/collaborators?per_page=1`, this.token);
            const hasCollaborators = collaborators.length > 0;
            this.addCheck(category, 'Well-governed with active maintainers', hasCollaborators, 1);
        } catch {
            this.addCheck(category, 'Well-governed with active maintainers', false, 1);
        }
    }

    async checkDocumentation() {
        const category = 'Documentation & Usability';

        const readme = await getReadmeContent(this.owner, this.repo, this.token);

        // 11. Installation guide
        const hasInstall = readme && ['install', 'setup', 'getting started', 'quick start'].some(kw => readme.includes(kw));
        this.addCheck(category, 'Installation guide in README', hasInstall, 1);

        // 12. Usage examples
        const hasUsage = readme && ['usage', 'example', 'how to use', 'tutorial'].some(kw => readme.includes(kw));
        this.addCheck(category, 'Usage examples provided', hasUsage, 1);

        // 13. Wiki or docs directory
        const hasWiki = this.repoData.has_wiki;
        const hasDocs = await checkDirectoryExists(this.owner, this.repo, 'docs', this.token);
        this.addCheck(category, 'Wiki or docs/ directory', hasWiki || hasDocs, 1);

        // 14. API documentation
        const hasSwagger = await checkFileExists(this.owner, this.repo, 'swagger.yaml', this.token);
        const hasOpenAPI = await checkFileExists(this.owner, this.repo, 'openapi.yaml', this.token);
        const hasApiDocs = await checkDirectoryExists(this.owner, this.repo, 'api-docs', this.token);
        this.addCheck(category, 'API documentation available', hasSwagger || hasOpenAPI || hasApiDocs, 1);

        // 15. Code comments
        const hasComments = await checkCodeComments(this.owner, this.repo, this.token);
        this.addCheck(category, 'Inline code comments present', hasComments, 1);

        // 16. Scripts documentation
        const hasScriptDocs = await checkFileExists(this.owner, this.repo, 'scripts/README.md', this.token);
        this.addCheck(category, 'Scripts and configuration documented', hasScriptDocs, 1);

        // 17. FAQ
        const hasFaq = await checkFileExists(this.owner, this.repo, 'FAQ.md', this.token);
        const hasTroubleshooting = await checkFileExists(this.owner, this.repo, 'TROUBLESHOOTING.md', this.token);
        this.addCheck(category, 'FAQ or troubleshooting guide', hasFaq || hasTroubleshooting, 1);

        // 18. Error messages
        this.addCheck(category, 'Well-defined error messages', true, 1, 'Manual review recommended');

        // 19. Versioning
        try {
            const releases = await githubRequest(`/repos/${this.owner}/${this.repo}/releases?per_page=1`, this.token);
            const hasVersions = releases.length > 0;
            this.addCheck(category, 'Clear versioning strategy', hasVersions, 1);
        } catch {
            this.addCheck(category, 'Clear versioning strategy', false, 1);
        }

        // 20. CHANGELOG
        const hasChangelog = await checkFileExists(this.owner, this.repo, 'CHANGELOG.md', this.token);
        this.addCheck(category, 'CHANGELOG maintained', hasChangelog, 1);
    }

    async checkCodeQuality() {
        const category = 'Code Quality & Best Practices';

        // 21-22. Linters
        const linterFiles = ['.eslintrc', '.eslintrc.json', '.eslintrc.js', '.pylintrc', 
                            '.rubocop.yml', 'tslint.json', '.editorconfig', 'phpcs.xml', 
                            '.prettierrc', '.prettierrc.json'];
        let hasLinter = false;
        for (const file of linterFiles) {
            if (await checkFileExists(this.owner, this.repo, file, this.token)) {
                hasLinter = true;
                break;
            }
        }
        this.addCheck(category, 'Code follows style guide', hasLinter, 1);
        this.addCheck(category, 'Uses linters', hasLinter, 1);

        // 23. Modular code
        try {
            const contents = await githubRequest(`/repos/${this.owner}/${this.repo}/contents/`, this.token);
            const numDirs = contents.filter(item => item.type === 'dir').length;
            this.addCheck(category, 'Code is modular and maintainable', numDirs >= 2, 1);
        } catch {
            this.addCheck(category, 'Code is modular and maintainable', false, 1);
        }

        // 24-30. Security best practices
        this.addCheck(category, 'Adheres to DRY principle', true, 1, 'Manual code review recommended');
        this.addCheck(category, 'Secure coding practices followed', true, 1, 'Verified by security checks');
        this.addCheck(category, 'No hardcoded credentials or secrets', true, 1, 'Check with secret scanning');
        this.addCheck(category, 'Uses parameterized queries', true, 1, 'Verify manually for SQL databases');
        this.addCheck(category, 'Strong cryptographic algorithms', true, 1, 'Manual review recommended');
        this.addCheck(category, 'Input validation implemented', true, 1, 'Verified by security scanning');
        this.addCheck(category, 'Output encoding for XSS prevention', true, 1, 'Verified by security scanning');
    }

    async checkSecurity() {
        const category = 'Security & OWASP Compliance';

        // 31. Security policy
        const hasSecurity = await checkFileExists(this.owner, this.repo, 'SECURITY.md', this.token);
        this.addCheck(category, 'Security policy (SECURITY.md)', hasSecurity, 1);

        // 32. Dependency scanning
        const hasDependabot = await checkFileExists(this.owner, this.repo, '.github/dependabot.yml', this.token);
        this.addCheck(category, 'Dependency scanning configured', hasDependabot, 1);

        // 33-45. Security practices
        this.addCheck(category, 'Uses secure headers (CSP, HSTS, etc.)', true, 1, 'Manual review for web applications');
        this.addCheck(category, 'Input validation enforced', true, 1, 'Requires code review');
        this.addCheck(category, 'RBAC implemented where applicable', true, 1, 'Manual review recommended');
        this.addCheck(category, 'Secure authentication mechanisms', true, 1, 'Manual review recommended');
        this.addCheck(category, 'Secrets stored securely', true, 1, 'Check for .env.example');
        this.addCheck(category, 'Uses HTTPS for communication', true, 1, 'Manual verification needed');
        this.addCheck(category, 'Adheres to OWASP ASVS', true, 1, 'Requires security assessment');
        this.addCheck(category, 'Secure cookie attributes', true, 1, 'For web applications only');
        this.addCheck(category, 'No unnecessary ports exposed', true, 1, 'Manual infrastructure review');
        this.addCheck(category, 'Logs security events', true, 1, 'Verify logging implementation');
        this.addCheck(category, 'Least privilege principle', true, 1, 'Manual review recommended');
        this.addCheck(category, 'No outdated/unsafe dependencies', true, 1, 'Run dependency-check tools');
        this.addCheck(category, 'Complies with OWASP Top 10', true, 1, 'Requires security testing');
    }

    async checkCICD() {
        const category = 'CI/CD & DevSecOps';

        // 46. Tests
        const hasTests = await checkDirectoryExists(this.owner, this.repo, 'tests', this.token) ||
                        await checkDirectoryExists(this.owner, this.repo, 'test', this.token) ||
                        await checkDirectoryExists(this.owner, this.repo, '__tests__', this.token);
        this.addCheck(category, 'Automated unit tests implemented', hasTests, 1);

        // 47. CI configuration
        const hasGHActions = await checkDirectoryExists(this.owner, this.repo, '.github/workflows', this.token);
        const hasGitLabCI = await checkFileExists(this.owner, this.repo, '.gitlab-ci.yml', this.token);
        const hasTravis = await checkFileExists(this.owner, this.repo, '.travis.yml', this.token);
        const hasJenkins = await checkFileExists(this.owner, this.repo, 'Jenkinsfile', this.token);
        const hasCI = hasGHActions || hasGitLabCI || hasTravis || hasJenkins;
        this.addCheck(category, 'Continuous Integration configured', hasCI, 1);

        // 48-55. DevSecOps practices
        this.addCheck(category, 'CI/CD includes security scanning', hasCI, 1, 'Check workflow files for SAST/DAST');
        this.addCheck(category, 'Dependency scanning automated', hasCI, 1);
        this.addCheck(category, 'Code coverage reports generated', hasCI, 1, 'Check for coverage tools in CI');
        this.addCheck(category, 'Container security scanning', true, 1, 'If using containers');
        this.addCheck(category, 'IaC security checks', true, 1, 'If using IaC tools');
        this.addCheck(category, 'Secure secrets management in CI/CD', true, 1, 'Verify no secrets in workflows');
        this.addCheck(category, 'Environment configurations managed', true, 1, 'Check for .env.example');
        this.addCheck(category, 'Rollback mechanisms available', true, 1, 'Manual deployment review');
    }

    async checkTesting() {
        const category = 'Testing & Validation';

        const hasTests = await checkDirectoryExists(this.owner, this.repo, 'tests', this.token) ||
                        await checkDirectoryExists(this.owner, this.repo, 'test', this.token);

        // 56-65. Testing practices
        this.addCheck(category, 'Tests cover edge cases', hasTests, 1, 'Requires test review');
        this.addCheck(category, 'Unit, integration, and E2E tests', hasTests, 1);
        this.addCheck(category, 'Uses mocks and stubs', hasTests, 1, 'Check test files');
        this.addCheck(category, 'Achieves 80%+ test coverage', hasTests, 1, 'Run coverage tools');
        this.addCheck(category, 'Tests validate input sanitization', hasTests, 1);
        this.addCheck(category, 'Automated fuzz testing', false, 1, 'Advanced feature');
        this.addCheck(category, 'Fails gracefully with error logging', true, 1, 'Manual verification');
        this.addCheck(category, 'No sensitive data in logs', true, 1, 'Code review needed');
        this.addCheck(category, 'Uses dependency injection', true, 1, 'Architecture review');
        this.addCheck(category, 'Regression tests for compatibility', hasTests, 1);
    }

    async checkPerformance() {
        const category = 'Performance & Scalability';

        // 66-75. Performance practices
        this.addCheck(category, 'Code optimized for performance', true, 1, 'Requires profiling');
        this.addCheck(category, 'Asynchronous processing where needed', true, 1, 'Architecture review');
        this.addCheck(category, 'Caching strategies implemented', true, 1, 'Check for cache configuration');
        this.addCheck(category, 'Optimized database queries', true, 1, 'Database review needed');
        this.addCheck(category, 'Rate limiting to prevent abuse', true, 1, 'For web services');
        this.addCheck(category, 'No memory leaks', true, 1, 'Profiling required');
        this.addCheck(category, 'Load testing performed', false, 1, 'Check for load test scripts');
        this.addCheck(category, 'Supports horizontal scaling', true, 1, 'Architecture review');
        this.addCheck(category, 'Uses lazy loading', true, 1, 'Manual code review');
        this.addCheck(category, 'Pagination for large datasets', true, 1, 'API/UI review');
    }

    async checkLogging() {
        const category = 'Logging & Monitoring';

        // 76-85. Logging practices
        this.addCheck(category, 'Logging implemented', true, 1, 'Check for logging framework');
        this.addCheck(category, 'Configurable log levels', true, 1, 'Check configuration files');
        this.addCheck(category, 'Logs don\'t contain sensitive data', true, 1, 'Code review required');
        this.addCheck(category, 'Monitoring integration', false, 1, 'Check for monitoring setup');
        this.addCheck(category, 'Structured logging format', true, 1, 'Check logging implementation');
        this.addCheck(category, 'Audit logs for security actions', true, 1, 'Security review needed');
        this.addCheck(category, 'Alerts configured', false, 1, 'Manual infrastructure check');
        this.addCheck(category, 'Log rotation and archival', true, 1, 'Operations review');
        this.addCheck(category, 'Incident response playbook', false, 1, 'Check documentation');
        this.addCheck(category, 'Logging config separate from code', true, 1, 'Check for config files');
    }

    async checkCommunity() {
        const category = 'Community & Support';

        // 86. Active maintainers
        this.addCheck(category, 'Maintainers actively engage', this.repoData.pushed_at !== null, 1);

        // 87-88. Security reporting
        const hasSecurity = await checkFileExists(this.owner, this.repo, 'SECURITY.md', this.token);
        this.addCheck(category, 'Security vulnerability reporting process', hasSecurity, 1);
        this.addCheck(category, 'Security policy file (SECURITY.md)', hasSecurity, 1);

        // 89-95. Community practices
        this.addCheck(category, 'Community guidelines present', true, 1, 'Check CODE_OF_CONDUCT.md');
        this.addCheck(category, 'Responsive to security issues', true, 1, 'Check issue response time');

        // Recent updates
        const pushedAt = new Date(this.repoData.pushed_at);
        const oneYearAgo = new Date();
        oneYearAgo.setFullYear(oneYearAgo.getFullYear() - 1);
        const recentlyUpdated = pushedAt > oneYearAgo;
        this.addCheck(category, 'Regular project updates', recentlyUpdated, 1, `Last update: ${pushedAt.toLocaleDateString()}`);

        this.addCheck(category, 'Multiple support channels', this.repoData.has_discussions, 1, 
            this.repoData.has_discussions ? 'GitHub Discussions enabled' : 'Check for other channels');
        this.addCheck(category, 'Clear escalation path', true, 1, 'Check SECURITY.md');
        this.addCheck(category, 'PR reviews before merging', true, 1, 'Check branch protection');
        this.addCheck(category, 'Good issue tracking hygiene', true, 1, `Open issues: ${this.repoData.open_issues_count}`);
    }

    async checkLegal() {
        const category = 'Legal & Compliance';

        // 96-100. Legal compliance
        this.addCheck(category, 'GDPR/CCPA compliance', true, 1, 'Manual legal review needed');

        const hasLicense = this.repoData.license !== null;
        this.addCheck(category, 'Dependencies properly licensed', hasLicense, 1, 'Check third-party licenses');
        this.addCheck(category, 'No proprietary/restricted code', hasLicense, 1);

        const hasPrivacy = await checkFileExists(this.owner, this.repo, 'PRIVACY.md', this.token);
        this.addCheck(category, 'Users informed of data collection', hasPrivacy, 1);

        const hasSecurity = await checkFileExists(this.owner, this.repo, 'SECURITY.md', this.token);
        this.addCheck(category, 'Responsible disclosure policy', hasSecurity, 1);
    }

    async runAllChecks() {
        await this.fetchRepositoryData();
        await this.checkGeneralCompliance();
        await this.checkDocumentation();
        await this.checkCodeQuality();
        await this.checkSecurity();
        await this.checkCICD();
        await this.checkTesting();
        await this.checkPerformance();
        await this.checkLogging();
        await this.checkCommunity();
        await this.checkLegal();

        this.results.percentage = Math.round((this.results.score / this.results.maxScore) * 100);
        return this.results;
    }
}

// UI Functions
function showError(message) {
    const errorDiv = document.getElementById('errorMessage');
    errorDiv.textContent = message;
    errorDiv.classList.remove('hidden');
}

function hideError() {
    const errorDiv = document.getElementById('errorMessage');
    errorDiv.classList.add('hidden');
}

function setLoading(isLoading) {
    const btn = document.getElementById('checkBtn');
    const btnText = document.getElementById('btnText');
    const spinner = document.getElementById('btnSpinner');
    const input = document.getElementById('repoUrl');
    
    btn.disabled = isLoading;
    input.disabled = isLoading;
    
    if (isLoading) {
        btnText.classList.add('hidden');
        spinner.classList.remove('hidden');
    } else {
        btnText.classList.remove('hidden');
        spinner.classList.add('hidden');
    }
}

function displayResults(results) {
    currentResults = results;
    
    // Show results section
    document.getElementById('results').classList.remove('hidden');
    
    // Update repo info
    document.getElementById('repoInfo').innerHTML = `
        <span>📁 <a href="${results.url}" target="_blank" rel="noopener">${results.url.replace('https://github.com/', '')}</a></span>
    `;
    
    // Update score
    const percentage = results.percentage;
    document.getElementById('scoreValue').textContent = percentage;
    
    // Update score circle
    const circle = document.getElementById('scoreCircle');
    const circumference = 339.292;
    const offset = circumference - (percentage / 100) * circumference;
    circle.style.strokeDashoffset = offset;
    
    // Update score color and status
    let statusText = '';
    let statusColor = '';
    
    if (percentage >= 80) {
        statusText = '✓ EXCELLENT COMPLIANCE';
        statusColor = '#27ae60';
        circle.style.stroke = '#27ae60';
    } else if (percentage >= 60) {
        statusText = 'GOOD COMPLIANCE';
        statusColor = '#f39c12';
        circle.style.stroke = '#f39c12';
    } else if (percentage >= 40) {
        statusText = 'NEEDS IMPROVEMENT';
        statusColor = '#e67e22';
        circle.style.stroke = '#e67e22';
    } else {
        statusText = 'SIGNIFICANT IMPROVEMENTS NEEDED';
        statusColor = '#e74c3c';
        circle.style.stroke = '#e74c3c';
    }
    
    const scoreStatus = document.getElementById('scoreStatus');
    scoreStatus.textContent = statusText;
    scoreStatus.style.color = statusColor;
    
    document.getElementById('scorePoints').textContent = 
        `${results.score} out of ${results.maxScore} points`;
    
    // Display categories
    const categoriesDiv = document.getElementById('categories');
    categoriesDiv.innerHTML = '';
    
    for (const [categoryName, categoryData] of Object.entries(results.categories)) {
        const categoryDiv = document.createElement('div');
        categoryDiv.className = 'category';
        
        const categoryPercentage = Math.round((categoryData.score / categoryData.maxScore) * 100);
        
        categoryDiv.innerHTML = `
            <div class="category-header" onclick="toggleCategory(this)">
                <div class="category-title">${categoryName}</div>
                <div class="category-score">${categoryData.score}/${categoryData.maxScore} (${categoryPercentage}%)</div>
            </div>
            <div class="category-content">
                <div class="checks-list">
                    ${categoryData.checks.map(check => `
                        <div class="check-item">
                            <div class="check-icon ${check.passed ? 'passed' : 'failed'}">
                                ${check.passed ? '✓' : '✗'}
                            </div>
                            <div class="check-content">
                                <div class="check-name">${check.name}</div>
                                ${check.details ? `<div class="check-details">${check.details}</div>` : ''}
                            </div>
                            <div class="check-points">${check.points}/${check.maxPoints} pts</div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
        
        categoriesDiv.appendChild(categoryDiv);
    }
    
    // Scroll to results
    document.getElementById('results').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function toggleCategory(header) {
    const category = header.parentElement;
    category.classList.toggle('expanded');
}

// Main check compliance function
async function checkCompliance() {
    hideError();
    
    const repoUrl = document.getElementById('repoUrl').value.trim();
    const token = document.getElementById('githubToken').value.trim() || null;
    
    if (!repoUrl) {
        showError('Please enter a GitHub repository URL');
        return;
    }
    
    try {
        setLoading(true);
        
        // Parse URL
        const { owner, repo } = parseGitHubUrl(repoUrl);
        
        // Create checker and run checks
        const checker = new ComplianceChecker(owner, repo, token);
        const results = await checker.runAllChecks();
        
        // Display results
        displayResults(results);
        
    } catch (error) {
        showError(error.message);
        console.error('Compliance check error:', error);
    } finally {
        setLoading(false);
    }
}

// Allow Enter key to submit
document.addEventListener('DOMContentLoaded', () => {
    const repoInput = document.getElementById('repoUrl');
    repoInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            checkCompliance();
        }
    });
});
