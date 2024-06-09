from dotenv import dotenv_values

secrets = dotenv_values(".secrets")

SLACK_APP_TOKEN = secrets.get("SLACK_APP_TOKEN")
SLACK_BOT_TOKEN = secrets.get("SLACK_BOT_TOKEN")

PLUGINS = (
    "lettuce.plugins.project.ProjectPlugin",
    "lettuce.plugins.repo.RepoPlugin",
    "lettuce.plugins.demo.DemoPlugin",
    "lettuce.plugins.welcome.WelcomePlugin",
)