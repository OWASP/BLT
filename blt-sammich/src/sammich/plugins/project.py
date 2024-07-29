import json

PROJECTS_PER_PAGE = 100
with open("data/projects.json") as f:
    project_data = json.load(f)


def show_project_page(channel_id, say):
    projects = list(project_data.keys())

    if not projects:
        say(channel=channel_id, text="No projects available.")
        return

    # Calculate the number of dropdowns needed
    num_dropdowns = (len(projects) + PROJECTS_PER_PAGE - 1) // PROJECTS_PER_PAGE

    blocks = []
    for i in range(num_dropdowns):
        start_index = i * PROJECTS_PER_PAGE
        end_index = start_index + PROJECTS_PER_PAGE
        project_slice = projects[start_index:end_index]

        options = [
            {"text": {"type": "plain_text", "text": project[:75]}, "value": project}
            for project in project_slice
        ]

        blocks.append(
            {
                "type": "section",
                "block_id": f"project_select_block_{i}",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Select a project (Page {i + 1}):",
                },
                "accessory": {
                    "type": "static_select",
                    "placeholder": {
                        "type": "plain_text",
                        "text": f"Select a project (Page {i + 1})",
                    },
                    "options": options,
                    "action_id": f"project_select_action_{i}",
                },
            }
        )

    say(channel=channel_id, blocks=blocks, text="Available Projects")
