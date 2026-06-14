# BLT-Newsletter Plans

This folder is the canonical place for BLT-Newsletter planning markdown so the implementation context lives with the repository.

## Current plans

- [`blt-newsletter-cloudflare-worker-plan.md`](./blt-newsletter-cloudflare-worker-plan.md) — Cloudflare Worker, D1, landing-page redesign, admin dashboard, and async SendGrid campaign engine plan.
- [`dashboard-ui-design-principles-and-v0-brief.md`](./dashboard-ui-design-principles-and-v0-brief.md) — Dashboard design principles, UX microfeatures, page inventory, interaction patterns, and questions before writing the final v0 prompt.
- [`dashboard-design-system-options.md`](./dashboard-design-system-options.md) — Comparison of Vercel, Stripe, Resend, Linear, and Mintlify references for the dashboard visual direction.
- [`dashboard-v0-master-prompt.md`](./dashboard-v0-master-prompt.md) — Final single v0 prompt for the complete HTML + Tailwind dashboard UI prototype.
- [`gitlab-workitems.md`](./gitlab-workitems.md) — Created GitLab parent/child work-item map for the GSoC 26 BLT-Newsletter plan.

## Current execution focus

Start with Slice 1 only:

1. Create `feat/cloudflare-newsletter-platform`.
2. Add `wrangler.toml`.
3. Add the Python Worker scaffold.
4. Add the D1 migration.
5. Add the landing redesign shell from the BLT inspiration page.
6. Implement `POST /api/subscribe` against D1.
7. Update the public form to use the Worker API.
8. Remove GitHub Issues subscription copy from the public UI.

Keep admin dashboard, issue CRUD/archive, SendGrid campaign delivery, and advanced backlog items in later slices unless maintainers explicitly expand Slice 1.
