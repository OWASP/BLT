# Design contest issue bodies

git.owaspblt.org has no issue templates, so the showcase links here. To enter a contest:

1. Open a [new issue](https://git.owaspblt.org/BLT/issues/new) on git.owaspblt.org (sign in first).
2. Title it `[blt-design-contest] <contest prefix> <your design name>`, for example
   `[blt-design-contest] [Logo] Shield mark`.
3. Paste the body of the contest's file below and fill in each section.

| Contest | Title prefix | Body | Label (added by a maintainer) |
| --- | --- | --- | --- |
| BLT T-Shirt Design Contest | `[Design]` | [design-submission.md](design-submission.md) | `design-submission` |
| BLT Logo Contest | `[Logo]` | [logo-submission.md](logo-submission.md) | `logo-submission` |
| BLT Homepage Design | `[Homepage]` | [homepage-submission.md](homepage-submission.md) | `homepage-submission` |
| BLT Video Meme | `[Video Meme]` | [video-meme-submission.md](video-meme-submission.md) | `video-meme-submission` |
| BLT Welcome Video | `[Welcome Video]` | [welcome-video-submission.md](welcome-video-submission.md) | `welcome-video-submission` |
| AppSecIL 2026 T-Shirt Design Contest | `[AppSecIL]` | [appsecil-tshirt-submission.md](appsecil-tshirt-submission.md) | `appsecil-tshirt-submission` |
| Propose a winner | `Declare winner:` | [declare-winner.md](declare-winner.md) | `winner-announcement` |

## Body format

`scripts/build_showcase.py` reads the issue body as sections. Each section starts with a
`### Heading` line (`##` also works) and its answer is the text below it. `<!-- ... -->` comments
are hints and are ignored. The headings it reads:

| Heading | Used for |
| --- | --- |
| `Preview Image` | The card image: the first Markdown image `![..](url)`, `<img src>` or image URL in it (else the first image anywhere in the body, or an image attached to the issue). |
| `Design / Prototype Link`, `Design / Source File Link` or `Design URL` | The "View Design" link (first `http(s)` URL). |
| `Design Category` or `<Something> Category` | The category badge (first non-empty line, list markers removed). |
| `Description` | The card text (first 200 characters). |

Other sections (such as `Submission Agreement`) are kept on the issue but not shown.

## Which issues count

An open issue is a submission when it belongs to blt-design-contest (label `blt-design-contest` or
`project:blt-design-contest`, or the title prefix `[blt-design-contest]`) or carries a contest
label, and its contest is known from the contest label or, failing that, from the contest title
prefix after `[blt-design-contest]`. Closing an issue removes it from the showcase.

## Votes and winners

Signed-in users vote by pressing **Vote** on the submission's issue. A comment that is just `+1`
also counts once per account (not the author's own, and not twice for someone who also pressed
Vote). A maintainer marks a winner by adding the `winner` label to the submission issue.
