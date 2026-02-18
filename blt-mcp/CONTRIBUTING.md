# Contributing to BLT-MCP

Thank you for your interest in contributing to BLT-MCP! This guide will help you get started.

## Code of Conduct

This project follows the [OWASP Code of Conduct](https://owasp.org/www-policy/operational/code-of-conduct). By participating, you are expected to uphold this code.

## Getting Started

### Prerequisites

- Node.js 18 or higher
- npm or yarn
- Git
- A text editor or IDE (VS Code recommended)

### Development Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/YOUR_USERNAME/BLT-MCP.git
   cd BLT-MCP
   ```

2. **Install Dependencies**
   ```bash
   npm install
   ```

3. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your BLT API credentials
   ```

4. **Build the Project**
   ```bash
   npm run build
   ```

5. **Test Your Setup**
   ```bash
   node dist/index.js
   # Should start the server without errors
   ```

## Development Workflow

### Making Changes

1. **Create a Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Your Changes**
   - Edit files in the `src/` directory
   - Follow the existing code style
   - Add comments for complex logic

3. **Build and Test**
   ```bash
   npm run build
   # Test your changes
   ```

4. **Commit Your Changes**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

### Commit Message Guidelines

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

Examples:
```
feat: add support for GitHub webhooks
fix: handle null values in API responses
docs: update installation instructions
refactor: improve error handling in API client
```

## Code Style

### TypeScript Guidelines

- Use TypeScript strict mode
- Define proper types (avoid `any`)
- Use interfaces for complex types
- Document public APIs with JSDoc comments
- Follow existing naming conventions

Example:
```typescript
/**
 * Submit a new issue to the BLT system
 * @param title - The issue title
 * @param description - Detailed description
 * @returns Promise with the created issue
 */
async function submitIssue(
  title: string,
  description: string
): Promise<Issue> {
  // Implementation
}
```

### Project Structure

```
src/
  index.ts          # Main server implementation
  types.ts          # Type definitions (if needed)
  utils.ts          # Utility functions (if needed)
```

## Testing

### Manual Testing

1. **Start the Server**
   ```bash
   node dist/index.js
   ```

2. **Test with MCP Inspector**
   ```bash
   npx @modelcontextprotocol/inspector node dist/index.js
   ```

3. **Test with Claude Desktop**
   - Configure Claude Desktop with your local build
   - Test all resources, tools, and prompts

### Writing Tests

If adding test infrastructure:

```typescript
describe('BLT-MCP Server', () => {
  it('should list all resources', async () => {
    // Test implementation
  });
  
  it('should submit an issue', async () => {
    // Test implementation
  });
});
```

## Adding New Features

### Adding a New Resource

1. Update `ListResourcesRequestSchema` handler:
   ```typescript
   {
     uri: "blt://new-resource",
     name: "New Resource",
     description: "Description of the resource",
     mimeType: "application/json"
   }
   ```

2. Update `ReadResourceRequestSchema` handler:
   ```typescript
   case "new-resource":
     data = await makeApiRequest("/new-endpoint");
     break;
   ```

3. Update documentation in README.md

### Adding a New Tool

1. Update `ListToolsRequestSchema` handler:
   ```typescript
   {
     name: "new_tool",
     description: "Tool description",
     inputSchema: {
       type: "object",
       properties: {
         param1: { type: "string" }
       },
       required: ["param1"]
     }
   }
   ```

2. Update `CallToolRequestSchema` handler:
   ```typescript
   case "new_tool":
     const result = await makeApiRequest("/endpoint", "POST", args);
     return { content: [{ type: "text", text: JSON.stringify(result) }] };
   ```

3. Update documentation

### Adding a New Prompt

1. Update `ListPromptsRequestSchema` handler:
   ```typescript
   {
     name: "new_prompt",
     description: "Prompt description",
     arguments: [
       { name: "arg1", description: "Argument description", required: true }
     ]
   }
   ```

2. Update `GetPromptRequestSchema` handler:
   ```typescript
   case "new_prompt":
     return {
       messages: [{
         role: "user",
         content: { type: "text", text: "Prompt template..." }
       }]
     };
   ```

3. Update documentation

## Documentation

### Updating Documentation

When making changes, update relevant documentation:

- **README.md** - User-facing documentation
- **USAGE.md** - Usage examples
- **ARCHITECTURE.md** - Architecture details
- **Code comments** - Inline documentation

### Documentation Style

- Use clear, concise language
- Include code examples
- Explain why, not just what
- Keep examples up-to-date

## Pull Request Process

### Before Submitting

1. **Test Your Changes**
   - Build successfully
   - Manual testing completed
   - No TypeScript errors
   - No security vulnerabilities

2. **Update Documentation**
   - README updated if needed
   - Examples added if needed
   - Comments added for complex code

3. **Clean Commit History**
   - Meaningful commit messages
   - Squash work-in-progress commits if needed
   - Rebase on latest main if needed

### Submitting a PR

1. **Push to Your Fork**
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create Pull Request**
   - Go to the GitHub repository
   - Click "New Pull Request"
   - Select your branch
   - Fill in the PR template

3. **PR Description Should Include**
   - What changes were made
   - Why the changes were made
   - How to test the changes
   - Screenshots (if UI changes)
   - Related issues (if any)

### PR Review Process

1. Automated checks will run
2. Maintainers will review your code
3. Address any feedback
4. Once approved, PR will be merged

## Security

### Reporting Security Issues

**Do not open public issues for security vulnerabilities.**

Instead, email security@owasp.org with:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Security Best Practices

- Never commit API keys or secrets
- Validate all user inputs
- Use parameterized queries
- Follow OWASP security guidelines
- Keep dependencies updated

## Getting Help

### Resources

- [MCP Documentation](https://modelcontextprotocol.io/)
- [OWASP BLT Project](https://owasp.org/www-project-bug-logging-tool/)
- [TypeScript Documentation](https://www.typescriptlang.org/docs/)

### Communication

- **GitHub Issues** - Bug reports and feature requests
- **GitHub Discussions** - Questions and discussions
- **OWASP Slack** - Real-time chat (security channel)

## Recognition

Contributors are recognized in:
- GitHub contributors page
- Release notes
- Project documentation

Thank you for contributing to BLT-MCP and helping make security tools more accessible!
