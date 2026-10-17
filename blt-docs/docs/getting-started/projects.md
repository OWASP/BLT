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
| OWASP BLT | [blt](https://git.owaspblt.org/BLT/BLT/tree/main/blt-core) | [owaspblt.org](https://owaspblt.org) | Main BLT public site. |
| BLT Docs | [blt-docs](https://git.owaspblt.org/BLT/BLT/tree/main/blt-docs) | [docs.owaspblt.org](https://docs.owaspblt.org) | MkDocs documentation served as Worker static assets. |
| BLT Next | [blt-next](https://git.owaspblt.org/BLT/BLT/tree/main/blt-next) | [next.owaspblt.org](https://next.owaspblt.org) | Static frontend with Python Worker application routes. |
| BLT API | [blt-api](https://git.owaspblt.org/BLT/BLT/tree/main/blt-api) | [api.owaspblt.org](https://api.owaspblt.org) | D1-backed Python Worker API and API dashboard. |
| BLT Jobs | [blt-jobs](https://git.owaspblt.org/BLT/BLT/tree/main/blt-jobs) | [jobs.owaspblt.org](https://jobs.owaspblt.org) | Git-native jobs content served by Worker static assets. |
| BLT Sizzle | [blt-sizzle](https://git.owaspblt.org/BLT/BLT/tree/main/blt-sizzle) | [sizzle.owaspblt.org](https://sizzle.owaspblt.org) | Organization check-ins with Python Workers, D1, and scheduled reminders. |
| BLT Toasty | [blt-toasty](https://git.owaspblt.org/BLT/BLT/tree/main/blt-toasty) | [toasty.owaspblt.org](https://toasty.owaspblt.org) | AI code review application. |
| BLT SafeCloak | [blt-safecloak](https://git.owaspblt.org/BLT/BLT/tree/main/blt-safecloak) | [safecloak.owaspblt.org](https://safecloak.owaspblt.org) | Secure communication and privacy application. |
| BLT Vanish | [blt-vanish](https://git.owaspblt.org/BLT/BLT/tree/main/blt-vanish) | [vanish.owaspblt.org](https://vanish.owaspblt.org) | Privacy data-removal application. |
| BLT Monitor | [blt-monitor](https://git.owaspblt.org/BLT/BLT/tree/main/blt-monitor) | [monitor.owaspblt.org](https://monitor.owaspblt.org) | BLT service monitoring dashboard. |
| BLT Design | [blt-design](https://git.owaspblt.org/BLT/BLT/tree/main/blt-design) | [design.owaspblt.org](https://design.owaspblt.org) | Design-system guidance. |
| BLT GSoC | [blt-gsoc](https://git.owaspblt.org/BLT/BLT/tree/main/blt-gsoc) | [gsoc.owaspblt.org](https://gsoc.owaspblt.org) | Google Summer of Code program hub. |
| BLT University | [blt-university](https://git.owaspblt.org/BLT/BLT/tree/main/blt-university) | [university.owaspblt.org](https://university.owaspblt.org) | Security learning platform. |
| BLT MCP | [blt-mcp](https://git.owaspblt.org/BLT/BLT/tree/main/blt-mcp) | [mcp.owaspblt.org](https://mcp.owaspblt.org) | AI-assisted BLT integration service. |
| BLT NetGuardian | [blt-netguardian](https://git.owaspblt.org/BLT/BLT/tree/main/blt-netguardian) | [netguardian.owaspblt.org](https://netguardian.owaspblt.org) | Autonomous security scanning service. |
| BLT Tomato | [blt-tomato](https://git.owaspblt.org/BLT/BLT/tree/main/blt-tomato) | [tomato.owaspblt.org](https://tomato.owaspblt.org) | OWASP project funding discovery service. |
| BLT OWASP Wich | [blt-owasp-wich](https://git.owaspblt.org/BLT/BLT/tree/main/blt-owasp-wich) | [wich.owaspblt.org](https://wich.owaspblt.org) | OWASP project compliance checker. |
| BLT OWASP Bumper | [blt-owasp-bumper](https://git.owaspblt.org/BLT/BLT/tree/main/blt-owasp-bumper) | [bumper.owaspblt.org](https://bumper.owaspblt.org) | OWASP repository dashboard. |
| BLT OWASP Metadata | [blt-owasp-metadata](https://git.owaspblt.org/BLT/BLT/tree/main/blt-owasp-metadata) | [metadata.owaspblt.org](https://metadata.owaspblt.org) | OWASP metadata explorer. |
| BLT OWASP Projects | [blt-owasp-projects](https://git.owaspblt.org/BLT/BLT/tree/main/blt-owasp-projects) | [projects.owaspblt.org](https://projects.owaspblt.org) | OWASP project matrix. |

## GitLab repository registry

The following entries are the verified OWASP BLT GitLab group project paths.
Projects without a public URL in the previous table must not be assigned a guessed `*.owaspblt.org` destination.

| Project | GitLab repository |
| ------- | ----------------- |
| BLT | [blt](https://git.owaspblt.org/BLT/BLT/tree/main/blt-core) |
| BLT Action | [blt-action](https://git.owaspblt.org/BLT/BLT/tree/main/blt-action) |
| BLT API | [blt-api](https://git.owaspblt.org/BLT/BLT/tree/main/blt-api) |
| BLT Autopatch | [blt-autopatch](https://git.owaspblt.org/BLT/BLT/tree/main/blt-autopatch) |
| BLT Byte | [blt-byte](https://git.owaspblt.org/BLT/BLT/tree/main/blt-byte) |
| blt-cli | [blt-cli](https://git.owaspblt.org/BLT/BLT/tree/main/blt-cli) |
| BLT CVE | [blt-cve](https://git.owaspblt.org/BLT/BLT/tree/main/blt-cve) |
| BLT Dash | [blt-dash](https://git.owaspblt.org/BLT/BLT/tree/main/blt-dash) |
| BLT Design | [blt-design](https://git.owaspblt.org/BLT/BLT/tree/main/blt-design) |
| BLT Contest | [blt-design-contest](https://git.owaspblt.org/BLT/BLT/tree/main/blt-design-contest) |
| BLT Docs | [blt-docs](https://git.owaspblt.org/BLT/BLT/tree/main/blt-docs) |
| BLT Enforcement | [blt-enforcement](https://git.owaspblt.org/BLT/BLT/tree/main/blt-enforcement) |
| BLT Extension | [blt-extension](https://git.owaspblt.org/BLT/BLT/tree/main/blt-extension) |
| BLT Flutter | [blt-flutter](https://git.owaspblt.org/BLT/BLT/tree/main/blt-flutter) |
| BLT GitCaster | [blt-gitcaster](https://git.owaspblt.org/BLT/BLT/tree/main/blt-gitcaster) |
| BLT GSoC | [blt-gsoc](https://git.owaspblt.org/BLT/BLT/tree/main/blt-gsoc) |
| BLT Hackathons | [blt-hackathons](https://git.owaspblt.org/BLT/BLT/tree/main/blt-hackathons) |
| BLT Hackerhouse | [blt-hackerhouse](https://git.owaspblt.org/BLT/BLT/tree/main/blt-hackerhouse) |
| BLT Ideas | [blt-ideas](https://git.owaspblt.org/BLT/BLT/tree/main/blt-ideas) |
| BLT Jobs | [blt-jobs](https://git.owaspblt.org/BLT/BLT/tree/main/blt-jobs) |
| BLT Ketchup | [blt-ketchup](https://git.owaspblt.org/BLT/BLT/tree/main/blt-ketchup) |
| BLT Leaf | [blt-leaf](https://git.owaspblt.org/BLT/BLT/tree/main/blt-leaf) |
| BLT Lettuce | [blt-lettuce](https://git.owaspblt.org/BLT/BLT/tree/main/blt-lettuce) |
| BLT Mayo | [blt-mayo](https://git.owaspblt.org/BLT/BLT/tree/main/blt-mayo) |
| BLT MCP | [blt-mcp](https://git.owaspblt.org/BLT/BLT/tree/main/blt-mcp) |
| BLT Monitor | [blt-monitor](https://git.owaspblt.org/BLT/BLT/tree/main/blt-monitor) |
| BLT NetGuardian | [blt-netguardian](https://git.owaspblt.org/BLT/BLT/tree/main/blt-netguardian) |
| BLT NetGuardian Client | [blt-netguardian-client](https://git.owaspblt.org/BLT/BLT/tree/main/blt-netguardian-client) |
| BLT Newsletter | [blt-newsletter](https://git.owaspblt.org/BLT/BLT/tree/main/blt-newsletter) |
| BLT Next | [blt-next](https://git.owaspblt.org/BLT/BLT/tree/main/blt-next) |
| BLT Nexus | [blt-nexus](https://git.owaspblt.org/BLT/BLT/tree/main/blt-nexus) |
| BLT OSSH | [blt-ossh](https://git.owaspblt.org/BLT/BLT/tree/main/blt-ossh) |
| BLT OWASP Bumper | [blt-owasp-bumper](https://git.owaspblt.org/BLT/BLT/tree/main/blt-owasp-bumper) |
| BLT OWASP Metadata | [blt-owasp-metadata](https://git.owaspblt.org/BLT/BLT/tree/main/blt-owasp-metadata) |
| BLT OWASP Projects | [blt-owasp-projects](https://git.owaspblt.org/BLT/BLT/tree/main/blt-owasp-projects) |
| BLT OWASP Wich | [blt-owasp-wich](https://git.owaspblt.org/BLT/BLT/tree/main/blt-owasp-wich) |
| BLT Pages | [blt-pages](https://git.owaspblt.org/BLT/BLT/tree/main/blt-pages) |
| BLT Panini | [blt-panini](https://git.owaspblt.org/BLT/BLT/tree/main/blt-panini) |
| BLT Pool | [blt-pool](https://git.owaspblt.org/BLT/BLT/tree/main/blt-pool) |
| BLT Preflight | [blt-preflight](https://git.owaspblt.org/BLT/BLT/tree/main/blt-preflight) |
| BLT Profiles | [blt-profiles](https://git.owaspblt.org/BLT/BLT/tree/main/blt-profiles) |
| BLT Rewards | [blt-rewards](https://git.owaspblt.org/BLT/BLT/tree/main/blt-rewards) |
| BLT SafeCloak | [blt-safecloak](https://git.owaspblt.org/BLT/BLT/tree/main/blt-safecloak) |
| BLT Sammich | [blt-sammich](https://git.owaspblt.org/BLT/BLT/tree/main/blt-sammich) |
| BLT Sizzle | [blt-sizzle](https://git.owaspblt.org/BLT/BLT/tree/main/blt-sizzle) |
| BLT Start | [blt-start](https://git.owaspblt.org/BLT/BLT/tree/main/blt-start) |
| BLT Timer Flutter | [blt-timer-flutter](https://git.owaspblt.org/BLT/BLT/tree/main/blt-timer-flutter) |
| BLT Timer Web | [blt-timer-web](https://git.owaspblt.org/BLT/BLT/tree/main/blt-timer-web) |
| BLT Toasty | [blt-toasty](https://git.owaspblt.org/BLT/BLT/tree/main/blt-toasty) |
| BLT Tomato | [blt-tomato](https://git.owaspblt.org/BLT/BLT/tree/main/blt-tomato) |
| BLT University | [blt-university](https://git.owaspblt.org/BLT/BLT/tree/main/blt-university) |
| BLT Vanish | [blt-vanish](https://git.owaspblt.org/BLT/BLT/tree/main/blt-vanish) |
| BLT Vanish Flutter | [blt-vanish-flutter](https://git.owaspblt.org/BLT/BLT/tree/main/blt-vanish-flutter) |
| BLT Waypoint | [blt-waypoint](https://git.owaspblt.org/BLT/BLT/tree/main/blt-waypoint) |
| BLT Zero | [blt-zero](https://git.owaspblt.org/BLT/BLT/tree/main/blt-zero) |
| coderabbit | [coderabbit](https://git.owaspblt.org/BLT/BLT/tree/main/coderabbit) |
| dot_github | [dot_github](https://git.owaspblt.org/BLT/BLT/tree/main/dot_github) |
| MY-GSOC-TOOL | [my-gsoc-tool](https://git.owaspblt.org/BLT/BLT/tree/main/my-gsoc-tool) |

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
