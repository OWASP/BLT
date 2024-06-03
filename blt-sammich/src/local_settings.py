from dotenv import dotenv_values

secrets = dotenv_values(".secrets")

SLACK_APP_TOKEN = secrets["SLACK_APP_TOKEN"]
SLACK_BOT_TOKEN = secrets["SLACK_BOT_TOKEN"]

PLUGINS = ("sammich.plugins.demo.DemoPlugin","sammich.plugins.contributer.ContributorPlugin")
