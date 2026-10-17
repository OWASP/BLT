# BLT project map

## How to use this page

Use this page to choose the GitLab repository and public service that own a BLT change.
The registry is curated from the OWASP BLT GitLab group and verified project remotes.
It is intentionally a documentation record, not a runtime dependency on the GitLab API.

Use the GitLab repository for source code, issues, merge requests, and repository-specific instructions.
Use the public service only when you need to use or verify the deployed application.
The owning repository remains the source of truth for setup commands, Worker configuration, secrets, database migrations, and production operations.

## Verified public services

Each public URL below was verified against a responding service with a matching product identity.
The absence of a public URL in this table does not mean a project is inactive.
It means BLT-docs does not currently have enough evidence to publish a canonical deployment destination.

| Service | GitLab repository | Public URL | Deployment role |
| ------- | ----------------- | ---------- | --------------- |
| OWASP BLT | [blt](https://gitlab.com/owasp-blt/blt) | [owaspblt.org](https://owaspblt.org) | Main BLT public site. |
| BLT Docs | [blt-docs](https://gitlab.com/owasp-blt/blt-docs) | [docs.owaspblt.org](https://docs.owaspblt.org) | MkDocs documentation served as Worker static assets. |
| BLT Next | [blt-next](https://gitlab.com/owasp-blt/blt-next) | [next.owaspblt.org](https://next.owaspblt.org) | Static frontend with Python Worker application routes. |
| BLT API | [blt-api](https://gitlab.com/owasp-blt/blt-api) | [api.owaspblt.org](https://api.owaspblt.org) | D1-backed Python Worker API and API dashboard. |
| BLT Jobs | [blt-jobs](https://gitlab.com/owasp-blt/blt-jobs) | [jobs.owaspblt.org](https://jobs.owaspblt.org) | Git-native jobs content served by Worker static assets. |
| BLT Sizzle | [blt-sizzle](https://gitlab.com/owasp-blt/blt-sizzle) | [sizzle.owaspblt.org](https://sizzle.owaspblt.org) | Organization check-ins with Python Workers, D1, and scheduled reminders. |
| BLT Toasty | [blt-toasty](https://gitlab.com/owasp-blt/blt-toasty) | [toasty.owaspblt.org](https://toasty.owaspblt.org) | AI code review application. |
| BLT SafeCloak | [blt-safecloak](https://gitlab.com/owasp-blt/blt-safecloak) | [safecloak.owaspblt.org](https://safecloak.owaspblt.org) | Secure communication and privacy application. |
| BLT Vanish | [blt-vanish](https://gitlab.com/owasp-blt/blt-vanish) | [vanish.owaspblt.org](https://vanish.owaspblt.org) | Privacy data-removal application. |
| BLT Monitor | [blt-monitor](https://gitlab.com/owasp-blt/blt-monitor) | [monitor.owaspblt.org](https://monitor.owaspblt.org) | BLT service monitoring dashboard. |
| BLT Design | [blt-design](https://gitlab.com/owasp-blt/blt-design) | [design.owaspblt.org](https://design.owaspblt.org) | Design-system guidance. |
| BLT GSoC | [blt-gsoc](https://gitlab.com/owasp-blt/blt-gsoc) | [gsoc.owaspblt.org](https://gsoc.owaspblt.org) | Google Summer of Code program hub. |
| BLT University | [blt-university](https://gitlab.com/owasp-blt/blt-university) | [university.owaspblt.org](https://university.owaspblt.org) | Security learning platform. |
| BLT MCP | [blt-mcp](https://gitlab.com/owasp-blt/blt-mcp) | [mcp.owaspblt.org](https://mcp.owaspblt.org) | AI-assisted BLT integration service. |
| BLT NetGuardian | [blt-netguardian](https://gitlab.com/owasp-blt/blt-netguardian) | [netguardian.owaspblt.org](https://netguardian.owaspblt.org) | Autonomous security scanning service. |
| BLT Tomato | [blt-tomato](https://gitlab.com/owasp-blt/blt-tomato) | [tomato.owaspblt.org](https://tomato.owaspblt.org) | OWASP project funding discovery service. |
| BLT OWASP Wich | [blt-owasp-wich](https://gitlab.com/owasp-blt/blt-owasp-wich) | [wich.owaspblt.org](https://wich.owaspblt.org) | OWASP project compliance checker. |
| BLT OWASP Bumper | [blt-owasp-bumper](https://gitlab.com/owasp-blt/blt-owasp-bumper) | [bumper.owaspblt.org](https://bumper.owaspblt.org) | OWASP repository dashboard. |
| BLT OWASP Metadata | [blt-owasp-metadata](https://gitlab.com/owasp-blt/blt-owasp-metadata) | [metadata.owaspblt.org](https://metadata.owaspblt.org) | OWASP metadata explorer. |
| BLT OWASP Projects | [blt-owasp-projects](https://gitlab.com/owasp-blt/blt-owasp-projects) | [projects.owaspblt.org](https://projects.owaspblt.org) | OWASP project matrix. |

## GitLab repository registry

The following entries are the verified OWASP BLT GitLab group project paths.
Projects without a public URL in the previous table must not be assigned a guessed `*.owaspblt.org` destination.

| Project | GitLab repository |
| ------- | ----------------- |
| BLT | [blt](https://gitlab.com/owasp-blt/blt) |
| BLT Action | [blt-action](https://gitlab.com/owasp-blt/blt-action) |
| BLT API | [blt-api](https://gitlab.com/owasp-blt/blt-api) |
| BLT Autopatch | [blt-autopatch](https://gitlab.com/owasp-blt/blt-autopatch) |
| BLT Byte | [blt-byte](https://gitlab.com/owasp-blt/blt-byte) |
| blt-cli | [blt-cli](https://gitlab.com/owasp-blt/blt-cli) |
| BLT CVE | [blt-cve](https://gitlab.com/owasp-blt/blt-cve) |
| BLT Dash | [blt-dash](https://gitlab.com/owasp-blt/blt-dash) |
| BLT Design | [blt-design](https://gitlab.com/owasp-blt/blt-design) |
| BLT Contest | [blt-design-contest](https://gitlab.com/owasp-blt/blt-design-contest) |
| BLT Docs | [blt-docs](https://gitlab.com/owasp-blt/blt-docs) |
| BLT Enforcement | [blt-enforcement](https://gitlab.com/owasp-blt/blt-enforcement) |
| BLT Extension | [blt-extension](https://gitlab.com/owasp-blt/blt-extension) |
| BLT Flutter | [blt-flutter](https://gitlab.com/owasp-blt/blt-flutter) |
| BLT GitCaster | [blt-gitcaster](https://gitlab.com/owasp-blt/blt-gitcaster) |
| BLT GSoC | [blt-gsoc](https://gitlab.com/owasp-blt/blt-gsoc) |
| BLT Hackathons | [blt-hackathons](https://gitlab.com/owasp-blt/blt-hackathons) |
| BLT Hackerhouse | [blt-hackerhouse](https://gitlab.com/owasp-blt/blt-hackerhouse) |
| BLT Ideas | [blt-ideas](https://gitlab.com/owasp-blt/blt-ideas) |
| BLT Jobs | [blt-jobs](https://gitlab.com/owasp-blt/blt-jobs) |
| BLT Ketchup | [blt-ketchup](https://gitlab.com/owasp-blt/blt-ketchup) |
| BLT Leaf | [blt-leaf](https://gitlab.com/owasp-blt/blt-leaf) |
| BLT Lettuce | [blt-lettuce](https://gitlab.com/owasp-blt/blt-lettuce) |
| BLT Mayo | [blt-mayo](https://gitlab.com/owasp-blt/blt-mayo) |
| BLT MCP | [blt-mcp](https://gitlab.com/owasp-blt/blt-mcp) |
| BLT Monitor | [blt-monitor](https://gitlab.com/owasp-blt/blt-monitor) |
| BLT NetGuardian | [blt-netguardian](https://gitlab.com/owasp-blt/blt-netguardian) |
| BLT NetGuardian Client | [blt-netguardian-client](https://gitlab.com/owasp-blt/blt-netguardian-client) |
| BLT Newsletter | [blt-newsletter](https://gitlab.com/owasp-blt/blt-newsletter) |
| BLT Next | [blt-next](https://gitlab.com/owasp-blt/blt-next) |
| BLT Nexus | [blt-nexus](https://gitlab.com/owasp-blt/blt-nexus) |
| BLT OSSH | [blt-ossh](https://gitlab.com/owasp-blt/blt-ossh) |
| BLT OWASP Bumper | [blt-owasp-bumper](https://gitlab.com/owasp-blt/blt-owasp-bumper) |
| BLT OWASP Metadata | [blt-owasp-metadata](https://gitlab.com/owasp-blt/blt-owasp-metadata) |
| BLT OWASP Projects | [blt-owasp-projects](https://gitlab.com/owasp-blt/blt-owasp-projects) |
| BLT OWASP Wich | [blt-owasp-wich](https://gitlab.com/owasp-blt/blt-owasp-wich) |
| BLT Pages | [blt-pages](https://gitlab.com/owasp-blt/blt-pages) |
| BLT Panini | [blt-panini](https://gitlab.com/owasp-blt/blt-panini) |
| BLT Pool | [blt-pool](https://gitlab.com/owasp-blt/blt-pool) |
| BLT Preflight | [blt-preflight](https://gitlab.com/owasp-blt/blt-preflight) |
| BLT Profiles | [blt-profiles](https://gitlab.com/owasp-blt/blt-profiles) |
| BLT Rewards | [blt-rewards](https://gitlab.com/owasp-blt/blt-rewards) |
| BLT SafeCloak | [blt-safecloak](https://gitlab.com/owasp-blt/blt-safecloak) |
| BLT Sammich | [blt-sammich](https://gitlab.com/owasp-blt/blt-sammich) |
| BLT Sizzle | [blt-sizzle](https://gitlab.com/owasp-blt/blt-sizzle) |
| BLT Start | [blt-start](https://gitlab.com/owasp-blt/blt-start) |
| BLT Timer Flutter | [blt-timer-flutter](https://gitlab.com/owasp-blt/blt-timer-flutter) |
| BLT Timer Web | [blt-timer-web](https://gitlab.com/owasp-blt/blt-timer-web) |
| BLT Toasty | [blt-toasty](https://gitlab.com/owasp-blt/blt-toasty) |
| BLT Tomato | [blt-tomato](https://gitlab.com/owasp-blt/blt-tomato) |
| BLT University | [blt-university](https://gitlab.com/owasp-blt/blt-university) |
| BLT Vanish | [blt-vanish](https://gitlab.com/owasp-blt/blt-vanish) |
| BLT Vanish Flutter | [blt-vanish-flutter](https://gitlab.com/owasp-blt/blt-vanish-flutter) |
| BLT Waypoint | [blt-waypoint](https://gitlab.com/owasp-blt/blt-waypoint) |
| BLT Zero | [blt-zero](https://gitlab.com/owasp-blt/blt-zero) |
| coderabbit | [coderabbit](https://gitlab.com/owasp-blt/coderabbit) |
| dot_github | [dot_github](https://gitlab.com/owasp-blt/dot_github) |
| MY-GSOC-TOOL | [my-gsoc-tool](https://gitlab.com/owasp-blt/my-gsoc-tool) |

## Link maintenance policy

Use the GitLab registry above when adding an OWASP BLT repository link.
Verify the project path against the GitLab group or the local repository's upstream remote before changing a link.
Verify a public service with an HTTP response and matching product identity before adding it to the public-services table.
Do not infer a public domain from a repository name.

Historical GitHub links may be retained only when they describe historical context.
Label them as historical and do not present them as the current contribution destination.

## Choosing where to contribute

| Contributor interest | Suggested starting repository |
| -------------------- | ----------------------------- |
| Documentation, site navigation, and cross-project architecture | BLT Docs |
| User-facing BLT product workflows and frontend experience | BLT Next |
| API contracts, integrations, D1-backed data, and API tests | BLT API |
| Jobs and public profile content workflows | BLT Jobs |
| Organization check-ins and daily contributor activity | BLT Sizzle |
| Repository metadata and OWASP project discovery | BLT OWASP Metadata, BLT OWASP Projects, or BLT OWASP Bumper |
| Security scanning and network posture | BLT NetGuardian or the project that owns the scanner workflow |
| GSoC activities and student coordination | BLT GSoC or MY-GSOC-TOOL |

## Before starting work

Read the issue or work item in the owning GitLab repository.
Confirm the current branch and relevant deployment environment.
Keep changes limited to the repository that owns the behavior.
Run the repository-specific verification before opening a merge request.
