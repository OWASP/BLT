/**
 * OWASP BLT – Configuration
 *
 * Fork-friendly configuration file. Commercial forks may set
 * SHOW_PRICING = true and customise the PRICING_PLANS array.
 * The OWASP-hosted instance always keeps SHOW_PRICING = false.
 *
 * License: AGPLv3
 */

// Revenue share percentage (referenced both in the config object and in pricing plans)
const _REVENUE_SHARE_PERCENT = 10;

const BLT_CONFIG = {
  /* ── Brand ── */
  ORG_NAME: "OWASP BLT",
  LOGO_URL:
    "https://github.com/OWASP-BLT/BLT/raw/main/website/static/img/logos/logo.png",

  /* ── Repository ── */
  REPO_OWNER: "OWASP-BLT",
  REPO_NAME: "BLT-Pages",

  /* ── External services ── */
  BLT_ZERO_URL: "https://zero.owaspblt.org",
  BLT_API_URL: "https://blt.owasp.org/api",

  /* ── Pricing (set to true in commercial forks) ── */
  SHOW_PRICING: false,

  /* ── Revenue sharing (commercial only) ── */
  REVENUE_SHARE_PERCENT: _REVENUE_SHARE_PERCENT,

  PRICING_PLANS: [
    {
      id: "free",
      name: "Free",
      price: 0,
      period: "forever",
      description: "For open-source projects and individuals.",
      features: [
        "Unlimited public bug reports",
        "Community leaderboard",
        "GitHub Issues integration",
        "Anonymous reporting via BLT-API",
      ],
      cta: "Get Started",
      cta_href: "https://github.com/OWASP-BLT/BLT-Pages/issues/new?template=bug_report.yml",
      highlighted: false,
    },
    {
      id: "pro",
      name: "Pro",
      price: 6,
      period: "/ month",
      description: "For companies that want managed bug intake.",
      features: [
        "Everything in Free",
        "Private bug reports dashboard",
        "Priority triage support",
        "Custom branding",
        `${_REVENUE_SHARE_PERCENT}% revenue share with top reporters`,
      ],
      cta: "Start Free Trial",
      cta_href: "#",
      highlighted: true,
    },
    {
      id: "enterprise",
      name: "Enterprise",
      price: null,
      period: "custom",
      description: "For large organizations with advanced needs.",
      features: [
        "Everything in Pro",
        "SSO / SAML support",
        "SLA guarantees",
        "Dedicated support",
        "Custom revenue share",
      ],
      cta: "Contact Us",
      cta_href: "mailto:contact@commercial-company-with-fork.org",
      highlighted: false,
    },
  ],
};
