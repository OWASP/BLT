# GitHub action that auto-assigns issues to users

## Inputs

| Parameter    | Required | Description                                                                |
| ------------ | -------- | -------------------------------------------------------------------------- |
| `repo-token` | true     | The GITHUB_TOKEN, needed to update the Issue.                              |


## Example usage

Here's an example flow that auto-assigns all new issues to the `octocat` user:

```yml
name: Issue assignment

on:
    issues:
        types: [opened]

jobs:
    auto-assign:
        runs-on: ubuntu-latest
        steps:
            - name: 'Auto-assign issue'
              uses: Bugheist/assign-issues-action@main
              with:
                  repo-token: ${{ secrets.GITHUB_TOKEN }}

```


