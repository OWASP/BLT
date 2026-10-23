/**
 * OWASP BLT – Configuration
 *
 * Fork-friendly configuration file.
 *
 * License: AGPLv3
 */

const BLT_CONFIG = {
  /* ── Brand ── */
  ORG_NAME: "OWASP BLT",
  LOGO_URL:
    "static/blt-logo.svg",

  /* ── Source: the BLT monorepo on git.owaspblt.org (single organization), folder blt-pages ── */
  PROJECT_PATH: "owasp-blt/blt-pages",
  FORGE_URL: "https://git.owaspblt.org/BLT",
  PROJECT_URL: "https://git.owaspblt.org/BLT/tree/main/blt-pages",
  // The forge's issue list takes one ?label= filter. Bug reports carry the labels bug and blt-pages.
  ISSUES_URL: "https://git.owaspblt.org/BLT/issues?label=blt-pages",
  NEW_ISSUE_URL: "https://git.owaspblt.org/BLT/issues/new",
  ISSUE_TEMPLATE: "Bug",

  /* ── External services ── */
  BLT_ZERO_URL: "https://zero.owaspblt.org",
  BLT_API_URL: "https://api.owaspblt.org",
};
