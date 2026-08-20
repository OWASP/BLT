# Bot setup

This page summarizes the Slack bot setup concepts that contributors may encounter in BLT-related repositories. Confirm the current implementation details in the owning repository before changing bot code or deployment settings.

!!! warning
    Never commit bot tokens, Slack tokens, API keys, generated credentials, or `.env` files. Store secrets only in the approved secret manager or deployment environment.

## Environment variables

Bot integrations commonly require environment variables for Slack app credentials and webhook configuration. Document variable names when needed, but do not include real values or realistic token examples in documentation.

Common variable names may include:

- `SLACK_BOT_TOKEN`
- `SLACK_SIGNING_SECRET`
- `SLACK_ID_CLIENT`
- `SLACK_WEBHOOK_URL`

Verify the required variables in the owning repository before deployment.

## Slack app configuration

Create and configure Slack apps through the official Slack API dashboard. The bot may require scopes such as:

```text
channels:read
chat:write
groups:read
channels:join
im:write
users:read
team:read
commands
```

Only request scopes that the current implementation actually needs. If a scope is no longer used, remove it from the app configuration and update the relevant repository documentation.

## Slash commands

The documented bot command set may include `/discover` for repository or issue discovery workflows. Confirm command names, request URLs, and handlers in the current code before publishing user-facing instructions.

## Integration setup

A typical Slack integration setup includes:

1. Create or update the Slack app.
2. Configure OAuth scopes and slash commands.
3. Install the app to the approved workspace.
4. Store credentials outside git.
5. Configure the BLT application or service that receives Slack events.
6. Test the command or event flow in a non-production workspace when possible.

## Operational notes

Bot integrations should include logging that helps maintainers diagnose command handling, event processing, and delivery failures. Logs must not include tokens, signing secrets, private messages, or other sensitive payloads.

When troubleshooting:

- Verify required environment variables are present in the runtime environment.
- Confirm the bot has been installed in the expected workspace.
- Confirm the bot has the scopes required for the failing action.
- Confirm slash command URLs point to the current deployment.
- Review application logs without exposing sensitive payloads in issues or merge requests.

## Related pages

- [Contributing](contributing.md)
- [Platform Architecture](platform-architecture.md)
- [Agentic Development](agentic-development.md)
