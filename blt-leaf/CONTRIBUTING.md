# Contributing to BLT-Leaf

Thanks for helping improve **BLT-Leaf**, the OWASP BLT PR readiness checker.

## Before you start

- Read the [README](README.md) for features and architecture.
- Optional deep dives: [docs/OAUTH_SETUP.md](docs/OAUTH_SETUP.md), [docs/DATABASE.md](docs/DATABASE.md).

## Local development

1. **Node.js** — Use **Node 22+** where possible (matches [CI](.github/workflows/ci.yml)).
2. **Install dependencies:**
   ```bash
   npm ci
   ```
3. **Environment** — Copy `.env.example` to `.env` and configure secrets as documented in the README and OAuth guide.
4. **D1 database** — Create `pr_tracker` and apply migrations (see README **Setup** — bash or Windows PowerShell sections).
5. **Run the worker locally:**
   ```bash
   npm run dev
   ```
   Open [http://localhost:8787](http://localhost:8787).

## Python (worker) sanity check

Backend code lives under `src/`. Quick syntax check:

```bash
python -m compileall src
```

(Use Python 3.11+ to align with typical Cloudflare Python Workers tooling.)

## Tests

Same checks CI expects before opening a PR:

```bash
npm test
```

Additional script in the repo:

```bash
node test-sorting-security.js
```

## Pull request workflow

1. **Fork** [OWASP-BLT/BLT-Leaf](https://github.com/OWASP-BLT/BLT-Leaf) and **clone your fork**.
2. Create a branch, e.g. `docs/...`, `fix/...`, or `feat/...`.
3. Keep commits focused; update docs when behavior or setup changes.
4. Open a PR against **`main`**. CI runs `npm run lint`, `npm run format:check`, `npm test`, and `npm audit`.

## Getting help

- **OWASP Slack:** `#project-blt`
- **Issues:** [GitHub Issues](https://github.com/OWASP-BLT/BLT-Leaf/issues)

## License

By contributing, you agree your contributions are licensed under the same terms as this project (see [LICENSE](LICENSE)).
