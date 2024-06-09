from machine.plugins.base import MachineBasePlugin
from machine.plugins.decorators import process


class WelcomePlugin(MachineBasePlugin):
    @process("member_joined_channel")
    async def welcome(self, event):
        user_id = event['user']
        channel_id = event['channel']

        welcome_message = f"""
:tada: *Welcome to the OWASP Slack Community, <@{user_id}>!* :tada:

We're thrilled to have you here! Whether you're new to OWASP or a long-time contributor, this Slack workspace is the perfect place to connect, collaborate, and stay informed about all things OWASP.

:small_blue_diamond: *Get Involved:*
• Check out the *#contribute* channel to find ways to get involved with OWASP projects and initiatives.
• Explore individual project channels, which are named *#project-name*, to dive into specific projects that interest you.
• Join our chapter channels, named *#chapter-name*, to connect with local OWASP members in your area.

:small_blue_diamond: *Stay Updated:*
• Visit *#newsroom* for the latest updates and announcements.
• Follow *#external-activities* for news about OWASP's engagement with the wider security community.

:small_blue_diamond: *Connect and Learn:*
• *#jobs*: Looking for new opportunities? Check out the latest job postings here.
• *#leaders*: Connect with OWASP leaders and stay informed about leadership activities.
• *#project-committee*: Engage with the committee overseeing OWASP projects.
• *#gsoc*: Stay updated on Google Summer of Code initiatives.
• *#github-admins*: Get support and discuss issues related to OWASP's GitHub repositories.
• *#learning*: Share and find resources to expand your knowledge in the field of application security.

We're excited to see the amazing contributions you'll make. If you have any questions or need assistance, don't hesitate to ask. Let's work together to make software security visible and improve the security of the software we all rely on.

Welcome aboard! :rocket:
        """

        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": welcome_message.strip()
                }
            }
        ]

        await self.say(channel=channel_id, text="Welcome to the OWASP Slack Community!", blocks=blocks)
