from dotenv import dotenv_values

secrets = dotenv_values(".secrets")

SLACK_APP_TOKEN = secrets["SLACK_APP_TOKEN"]
SLACK_BOT_TOKEN = secrets["SLACK_BOT_TOKEN"]

PLUGINS = (
    "sammich.plugins.demo.DemoPlugin",
    "sammich.plugins.contributors.ContributorPlugin",
    "sammich.plugins.project.ProjectPlugin",
    "sammich.plugins.repo.RepoPlugin",
    "sammich.plugins.create_issue.CreateIssuePlugin",
)
