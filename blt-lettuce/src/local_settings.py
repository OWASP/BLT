from dotenv import dotenv_values

secrets = dotenv_values(".secrets")

SLACK_APP_TOKEN = secrets.get("SLACK_APP_TOKEN")
SLACK_BOT_TOKEN = secrets.get("SLACK_BOT_TOKEN")
SLACK_SIGNING_TOKEN = secrets.get("SLACK_SIGNING_TOKEN")

PLUGINS = (
    "lettuce.plugins.project.ProjectPlugin",
    "lettuce.plugins.repo.RepoPlugin",
    "lettuce.plugins.handle_messages.HandleMessagesPlugin",
    "lettuce.plugins.startup_message.StartupMessagePlugin",
    "lettuce.plugins.update_server.UpdateServerPlugin",
    "lettuce.plugins.welcome.welcome.WelcomePlugin",
)

USE_REQUEST_URL = True
