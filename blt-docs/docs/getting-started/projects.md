# BLT project map

## How to use this page

Use this page to choose the project folder and public service that own a BLT change.
Every BLT project lives in one repository, [git.owaspblt.org/BLT](https://git.owaspblt.org/BLT), each in its own folder.
This page is a documentation record, not a runtime dependency on the hosting platform's API.

Use the project's folder in the BLT repository for source code and project-specific instructions. Issues, pull requests and discussions happen on [git.owaspblt.org/BLT](https://git.owaspblt.org/BLT).
Use the public service only when you need to use or verify the deployed application.
The owning repository remains the source of truth for setup commands, Worker configuration, secrets, database migrations, and production operations.

## Verified public services

Each public URL below was verified against a responding service with a matching product identity.
The absence of a public URL in this table does not mean a project is inactive.
It means BLT-docs does not currently have enough evidence to publish a canonical deployment destination.

| Service | Project folder | Public URL | Deployment role |
| ------- | ----------------- | ---------- | --------------- |
| BLT Legacy | [blt-legacy](https://git.owaspblt.org/BLT/BLT-Legacy) | [legacy.owaspblt.org](https://legacy.owaspblt.org) | The original Django app (formerly blt-core), being replaced feature by feature. Offline while its data is migrated. |
| BLT Docs | [blt-docs](https://git.owaspblt.org/BLT/BLT-Docs) | [docs.owaspblt.org](https://docs.owaspblt.org) | MkDocs documentation served as Worker static assets. |
| BLT Next | [blt-next](https://git.owaspblt.org/BLT/BLT-Next) | [next.owaspblt.org](https://next.owaspblt.org) | Static frontend with Python Worker application routes. |
| BLT API | [blt-api](https://git.owaspblt.org/BLT/BLT-API) | [api.owaspblt.org](https://api.owaspblt.org) | D1-backed Python Worker API and API dashboard. |
| BLT Jobs | [blt-jobs](https://git.owaspblt.org/BLT/BLT-Jobs) | [jobs.owaspblt.org](https://jobs.owaspblt.org) | Git-native jobs content served by Worker static assets. |
| BLT Sizzle | [blt-sizzle](https://git.owaspblt.org/BLT/BLT-Sizzle) | [sizzle.owaspblt.org](https://sizzle.owaspblt.org) | Organization check-ins with Python Workers, D1, and scheduled reminders. |
| BLT Toasty | [blt-toasty](https://git.owaspblt.org/BLT/BLT-Toasty) | [toasty.owaspblt.org](https://toasty.owaspblt.org) | AI code review application. |
| BLT SafeCloak | [blt-safecloak](https://git.owaspblt.org/BLT/BLT-SafeCloak) | [safecloak.owaspblt.org](https://safecloak.owaspblt.org) | Secure communication and privacy application. |
| BLT Vanish | [blt-vanish](https://git.owaspblt.org/BLT/BLT-Vanish) | [vanish.owaspblt.org](https://vanish.owaspblt.org) | Privacy data-removal application. |
| BLT Monitor | [blt-monitor](https://git.owaspblt.org/BLT/BLT-Monitor) | [monitor.owaspblt.org](https://monitor.owaspblt.org) | BLT service monitoring dashboard. |
| BLT Design | [blt-design](https://git.owaspblt.org/BLT/BLT-Design) | [design.owaspblt.org](https://design.owaspblt.org) | Design-system guidance. |
| BLT GSoC | [blt-gsoc](https://git.owaspblt.org/BLT/BLT-GSOC) | [gsoc.owaspblt.org](https://gsoc.owaspblt.org) | Google Summer of Code program hub. |
| BLT University | [blt-university](https://git.owaspblt.org/BLT/BLT-University) | [university.owaspblt.org](https://university.owaspblt.org) | Security learning platform. |
| BLT MCP | [blt-mcp](https://git.owaspblt.org/BLT/BLT-MCP) | [mcp.owaspblt.org](https://mcp.owaspblt.org) | AI-assisted BLT integration service. |
| BLT NetGuardian | [blt-netguardian](https://git.owaspblt.org/BLT/BLT-NetGuardian) | [netguardian.owaspblt.org](https://netguardian.owaspblt.org) | Autonomous security scanning service. |
| BLT Tomato | [blt-tomato](https://git.owaspblt.org/BLT/BLT-Tomato) | [tomato.owaspblt.org](https://tomato.owaspblt.org) | OWASP project funding discovery service. |
| BLT OWASP Wich | [blt-owasp-wich](https://git.owaspblt.org/BLT/BLT-OWASP-Wich) | [wich.owaspblt.org](https://wich.owaspblt.org) | OWASP project compliance checker. |
| BLT OWASP Bumper | [blt-owasp-bumper](https://git.owaspblt.org/BLT/BLT-OWASP-Bumper) | [bumper.owaspblt.org](https://bumper.owaspblt.org) | OWASP repository dashboard. |
| BLT OWASP Metadata | [blt-owasp-metadata](https://git.owaspblt.org/BLT/BLT-OWASP-Metadata) | [metadata.owaspblt.org](https://metadata.owaspblt.org) | OWASP metadata explorer. |
| BLT OWASP Projects | [blt-owasp-projects](https://git.owaspblt.org/BLT/BLT-OWASP-Projects) | [projects.owaspblt.org](https://projects.owaspblt.org) | OWASP project matrix. |

## Project registry

The following entries are the project folders in the BLT repository.
Projects without a public URL in the previous table must not be assigned a guessed `*.owaspblt.org` destination.

| Project | Folder |
| ------- | ----------------- |
| BLT Legacy | [blt-legacy](https://git.owaspblt.org/BLT/BLT-Legacy) |
| BLT Action | [blt-action](https://git.owaspblt.org/BLT/BLT-Action) |
| BLT API | [blt-api](https://git.owaspblt.org/BLT/BLT-API) |
| BLT Autopatch | [blt-autopatch](https://git.owaspblt.org/BLT/BLT-Autopatch) |
| BLT Byte | [blt-byte](https://git.owaspblt.org/BLT/BLT-Byte) |
| blt-cli | [blt-cli](https://git.owaspblt.org/BLT/BLT-CLI) |
| BLT Cron | [blt-cron](https://git.owaspblt.org/BLT/BLT-Cron) |
| BLT CVE | [blt-cve](https://git.owaspblt.org/BLT/BLT-CVE) |
| BLT Dash | [blt-dash](https://git.owaspblt.org/BLT/BLT-Dash) |
| BLT Design | [blt-design](https://git.owaspblt.org/BLT/BLT-Design) |
| BLT Contest | [blt-design-contest](https://git.owaspblt.org/BLT/BLT-Design-Contest) |
| BLT Docs | [blt-docs](https://git.owaspblt.org/BLT/BLT-Docs) |
| BLT Enforcement | [blt-enforcement](https://git.owaspblt.org/BLT/BLT-Enforcement) |
| BLT Extension | [blt-extension](https://git.owaspblt.org/BLT/BLT-Extension) |
| BLT Flutter | [blt-flutter](https://git.owaspblt.org/BLT/BLT-Flutter) |
| BLT GitCaster | [blt-gitcaster](https://git.owaspblt.org/BLT/BLT-Gitcaster) |
| BLT GSoC | [blt-gsoc](https://git.owaspblt.org/BLT/BLT-GSOC) |
| BLT Hackathons | [blt-hackathons](https://git.owaspblt.org/BLT/BLT-Hackathons) |
| BLT Hackerhouse | [blt-hackerhouse](https://git.owaspblt.org/BLT/BLT-HackerHouse) |
| BLT Ideas | [blt-ideas](https://git.owaspblt.org/BLT/BLT-Ideas) |
| BLT Jobs | [blt-jobs](https://git.owaspblt.org/BLT/BLT-Jobs) |
| BLT Ketchup | [blt-ketchup](https://git.owaspblt.org/BLT/BLT-Ketchup) |
| BLT Leaf | [blt-leaf](https://git.owaspblt.org/BLT/BLT-Leaf) |
| BLT Lettuce | [blt-lettuce](https://git.owaspblt.org/BLT/BLT-Lettuce) |
| BLT Mayo | [blt-mayo](https://git.owaspblt.org/BLT/BLT-Mayo) |
| BLT MCP | [blt-mcp](https://git.owaspblt.org/BLT/BLT-MCP) |
| BLT Monitor | [blt-monitor](https://git.owaspblt.org/BLT/BLT-Monitor) |
| BLT NetGuardian | [blt-netguardian](https://git.owaspblt.org/BLT/BLT-NetGuardian) |
| BLT NetGuardian Client | [blt-netguardian-client](https://git.owaspblt.org/BLT/BLT-NetGuardian-Client) |
| BLT Newsletter | [blt-newsletter](https://git.owaspblt.org/BLT/BLT-Newsletter) |
| BLT Next | [blt-next](https://git.owaspblt.org/BLT/BLT-Next) |
| BLT Nexus | [blt-nexus](https://git.owaspblt.org/BLT/BLT-Nexus) |
| BLT OSSH | [blt-ossh](https://git.owaspblt.org/BLT/BLT-OSSH) |
| BLT OWASP Bumper | [blt-owasp-bumper](https://git.owaspblt.org/BLT/BLT-OWASP-Bumper) |
| BLT OWASP Metadata | [blt-owasp-metadata](https://git.owaspblt.org/BLT/BLT-OWASP-Metadata) |
| BLT OWASP Projects | [blt-owasp-projects](https://git.owaspblt.org/BLT/BLT-OWASP-Projects) |
| BLT OWASP Wich | [blt-owasp-wich](https://git.owaspblt.org/BLT/BLT-OWASP-Wich) |
| BLT Pages | [blt-pages](https://git.owaspblt.org/BLT/BLT-Pages) |
| BLT Panini | [blt-panini](https://git.owaspblt.org/BLT/BLT-Panini) |
| BLT Pool | [blt-pool](https://git.owaspblt.org/BLT/BLT-Pool) |
| BLT Preflight | [blt-preflight](https://git.owaspblt.org/BLT/BLT-Preflight) |
| BLT Profiles | [blt-profiles](https://git.owaspblt.org/BLT/BLT-Profiles) |
| BLT Rewards | [blt-rewards](https://git.owaspblt.org/BLT/BLT-Rewards) |
| BLT SafeCloak | [blt-safecloak](https://git.owaspblt.org/BLT/BLT-SafeCloak) |
| BLT Sammich | [blt-sammich](https://git.owaspblt.org/BLT/BLT-Sammich) |
| BLT Sizzle | [blt-sizzle](https://git.owaspblt.org/BLT/BLT-Sizzle) |
| BLT Start | [blt-start](https://git.owaspblt.org/BLT/BLT-Start) |
| BLT Timer Flutter | [blt-timer-flutter](https://git.owaspblt.org/BLT/BLT-Timer-Flutter) |
| BLT Timer Web | [blt-timer-web](https://git.owaspblt.org/BLT/BLT-Timer-Web) |
| BLT Toasty | [blt-toasty](https://git.owaspblt.org/BLT/BLT-Toasty) |
| BLT Tomato | [blt-tomato](https://git.owaspblt.org/BLT/BLT-Tomato) |
| BLT University | [blt-university](https://git.owaspblt.org/BLT/BLT-University) |
| BLT Vanish | [blt-vanish](https://git.owaspblt.org/BLT/BLT-Vanish) |
| BLT Vanish Flutter | [blt-vanish-flutter](https://git.owaspblt.org/BLT/BLT-Vanish-Flutter) |
| BLT Waypoint | [blt-waypoint](https://git.owaspblt.org/BLT/BLT-Waypoint) |
| BLT Zero | [blt-zero](https://git.owaspblt.org/BLT/BLT-Zero) |
| coderabbit | [coderabbit](https://git.owaspblt.org/BLT/coderabbit) |
| dot_github | [dot_github](https://git.owaspblt.org/BLT/dot_github) |
| MY-GSOC-TOOL | [my-gsoc-tool](https://git.owaspblt.org/BLT/MY-GSOC-TOOL) |

## Link maintenance policy

Use the registry above when adding an OWASP BLT project link, in the form `https://git.owaspblt.org/BLT/<Project>`.
The project names come from `scripts/routing/projects.tsv` in the BLT repository.
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

Read the issue on [git.owaspblt.org/BLT](https://git.owaspblt.org/BLT/issues) and check which project it belongs to.
Confirm the current branch and relevant deployment environment.
Keep changes limited to the repository that owns the behavior.
Run the repository-specific verification before opening a pull request.
