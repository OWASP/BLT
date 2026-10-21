# AI Policy for Contributors

OWASP BLT is a pro-AI project. We want you to use AI tools to contribute: coding agents, chat assistants, code review bots and local models all help good work reach the project faster. This policy explains how to use them so that BLT stays high-quality, honest and secure.

## TL;DR

- **Use AI.** Agents such as Claude Code, Codex, Copilot, Cursor or a local model are welcome and recommended for issues, pull requests, tests and docs.
- **Disclose it.** Every pull request fills in the **AI model** field with the model(s) and tool(s) you used, or `None`. Commits made with an agent carry a `Co-Authored-By:` trailer naming the model.
- **You own it.** You must understand and be able to explain every line, run the tests locally, and review the AI's output before you submit. No blind copy-paste.
- **Keep it small and real.** Focused PRs, tests for behaviour changes, no AI-generated noise. Maintainers may close low-effort AI spam.
- **Keep secrets out of AI tools.** No secrets, tokens or private vulnerability details in third-party AI services. Report vulnerabilities through the repository's Security tab.
- **Respect licences.** Everything you submit must be compatible with the project's licence, whoever or whatever wrote it.

## Why we encourage AI

BLT is a security project run largely by volunteers. AI agents let a contributor read an unfamiliar codebase quickly, write tests they would otherwise skip, and find bugs that humans miss. We'd rather you use them well than avoid them. Banning AI would not stop people using it. It would only stop them telling us.

What AI does not replace is your judgement. The AI helps you do the work; the decisions in the work are yours.

## Starting work: the "copy AI prompt"

Every BLT issue has a one-line **copy AI prompt**. It is the recommended way to start: copy it, paste it into your agent, and the agent gets the issue, the repository and the conventions it needs to begin.

The prompt gets you started. It doesn't finish the job. You still read the issue yourself, steer the agent, check its output and own the result.

## Disclosure (required)

**Pull requests.** Every pull request on git.owaspblt.org has a required **AI model** field. Put in it:

- the model(s) you used, and the tool or agent that ran them, for example `Claude Opus 4.5 via Claude Code`, `GPT-5 via Codex`, `Copilot (VS Code)`, or `Qwen2.5-Coder 32B via Ollama`;
- `None` if you didn't use AI. That's a perfectly good answer.

If AI played a significant part, add a sentence or two to the description saying what it did (for example "the agent wrote the tests; I wrote the migration by hand"). This helps reviewers know where to look harder. It doesn't count against you.

**Commits.** When an agent writes or substantially edits a commit, end the commit message with a trailer naming the model:

```
Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

Use whatever name and address your tool emits. If it emits none, the model name alone is enough.

**Issues, comments and reviews.** You can use AI to draft issues, comments and code reviews. Say so briefly (for example "drafted with Claude, checked by me"), and check every fact, file path, line number and link before posting. A review that just restates the diff adds nothing. A good review adds your own analysis.

Hiding AI use, or claiming `None` when that isn't true, is treated as a conduct issue, not a formatting mistake.

## You are responsible for your pull request

The human who opens a pull request owns it, whatever tools produced it. Before you submit:

1. **Read the whole diff.** Understand every change and be able to explain it in review. If you can't explain a line, remove it or learn what it does.
2. **Run the tests locally:** `scripts/ci/test.sh <project>` (for example `scripts/ci/test.sh blt-leaf`). Don't rely on CI to find out whether your change works.
3. **Check what the AI invented.** Agents can produce APIs, functions, config keys, command flags, packages and links that do not exist. Verify each one against the real code or docs.
4. **Write the PR description so it is accurate.** It should say what changed and why, and how you tested it. Don't paste in a generic AI summary.

If you are new to programming or to BLT, use AI to learn rather than to skip the learning. Mentors will ask you about your changes, and "the AI did it" doesn't answer their questions.

## Quality bar

- **Small, focused pull requests.** One issue, one concern. Agents make big diffs easy to produce and hard to review, so split large changes up.
- **Tests for behaviour changes.** If behaviour changes, a test should show it. AI is good at writing tests, so use it for that.
- **Follow the project's conventions** and its issue and pull request templates.
- **No AI noise.** Don't submit:
  - many trivial PRs (typo sweeps, rewording or reformatting) opened to collect contributions;
  - docs that are reworded without adding anything, or wordy text with no substance;
  - code that calls APIs that don't exist, or text that cites links, issues or CVEs that don't exist;
  - changes nobody asked for, outside the issue's scope.

Maintainers' time is the scarcest resource in the project. They may close, without detailed review, PRs and issues that look like unreviewed or low-effort AI output, and repeated spam can lead to a block.

## Security

BLT is a security project, so we hold AI-assisted work to the same security standard as everything else.

- **Never paste secrets into third-party AI services.** That includes API keys, tokens, passwords, `.env` files, production data, private vulnerability details and unpublished advisories. Agents read files too, so keep secrets out of your working tree or out of the agent's reach. Use a local model if you need help with something sensitive.
- **Report vulnerabilities privately** through the **Security** tab of the repository on git.owaspblt.org (private security advisories). Never report them in a public issue, pull request, chat or AI conversation.
- **AI-found vulnerabilities are welcome.** If an AI scanner or agent finds a security issue in BLT, report it privately as above. Before you report, confirm it's real: include a reproducer or proof of concept, state the severity honestly, and remove anything the tool made up (stack traces, endpoints, versions). Reports we can't reproduce will be closed.
- **Be careful with AI-suggested dependencies.** Models suggest packages that don't exist or that are typosquats of real ones. Before adding a dependency, check that it is the real, maintained package: look at its source repository, publisher, download history and licence. Prefer no new dependency when the standard library or an existing one will do.
- **Review generated code for security bugs** (injection, missing authorization checks, unsafe deserialization, secrets in code or logs) just as you would review a human's code.

## Licensing and attribution

Each BLT project has its own licence in its folder. Most are **AGPL-3.0**; a few use another licence (for example MIT or GPL-3.0), so check the `LICENSE` file of the project you're changing.

- Everything you submit must be compatible with that project's licence. AI-generated code is no exception.
- Don't paste in code under an incompatible licence, even if an AI handed it to you. If AI output looks like a recognisable copy of existing code, find the original, then check its licence and attribute it, or rewrite the code yourself.
- Credit third-party code, datasets and content as their licences require.
- Don't put copyrighted, confidential or proprietary material into prompts.

## Google Summer of Code

GSoC applicants and contributors must also follow the [OWASP GSoC AI and LLM Usage Guidelines](https://community.owasp.org/initiatives/gsoc/gsoc_ai_usage_guidelines). Among other things, they require an **"LLM Usage Considerations"** section in any proposal or report where you used an LLM. If the two documents differ, follow the stricter rule. Talk to your mentor early about how you plan to use AI.

## Questions

If you're unsure whether something is OK, ask in the issue, in a discussion on git.owaspblt.org, or in the OWASP Slack `#project-blt` channel before you submit. This policy will change as the tools do.

## Sources and credits

This policy builds on ideas from other OWASP projects and the wider open source community:

- [OWASP GSoC: AI and LLM Usage Guidelines](https://community.owasp.org/initiatives/gsoc/gsoc_ai_usage_guidelines)
- [OWASP Cheat Sheet Series: Use of AI](https://github.com/OWASP/CheatSheetSeries/blob/master/CONTRIBUTING.md#use-of-ai)
- [OWASP AISVS: AI-assisted contributions](https://github.com/OWASP/AISVS/blob/main/CONTRIBUTING.md#ai-assisted-contributions)
- Michael Catanzaro, [The Era of Software Quality, or the Era of Ostriches?](https://blogs.gnome.org/mcatanzaro/2026/10/02/the-era-of-software-quality-or-the-era-of-ostriches/) (on accepting AI-found vulnerability reports)
