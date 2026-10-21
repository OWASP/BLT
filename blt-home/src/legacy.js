// Paths that belonged to the legacy Django app (blt-core, possibly renamed
// blt-legacy). That app is off until its data is migrated, so old blt.owasp.org
// and owaspblt.org deep links such as /issue/123/ or /profile/alice/ go to
// blt-next's "this page moved" route: /legacy?from=<original path + query>.
//
// Built from the first path segment of every route in blt-core/blt/urls.py.
// test/legacy.test.mjs re-reads urls.py and fails if a route segment is
// neither listed here nor in LEGACY_EXCLUDED, so the two cannot drift apart.

export const LEGACY_PAGE = "https://next.owaspblt.org/legacy";

export function legacyTarget(pathname, search = "") {
  return LEGACY_PAGE + "?from=" + encodeURIComponent(pathname + search);
}

// First path segment -> legacy. Matching is exact on the segment, so
// /issue/1/ matches "issue" but /issues-new does not.
export const LEGACY_SEGMENTS = new Set([
  ".well-known", "Submitpr", "about", "accounts", "activity", "add-sizzle-checkin",
  "add_domain_to_organization", "add_repo", "adventures", "all_activity", "apps",
  "assign-badge", "auth", "authenticate", "bacon", "bacon-requests", "badges",
  "batch-send-bacon-tokens", "bidding", "blt-tomato", "bounties", "bounty_payout", "captcha",
  "change_bid_status", "check-in", "check_domain_security_txt", "check_owasp_compliance",
  "comment", "content", "contribute", "contributor-stats", "contributors", "create",
  "create_github_issue", "dashboard", "delete_issue", "delete_time_entry", "deletions",
  "discussion-rooms", "dislike_issue", "distribute_bacon", "domain", "domains", "donate",
  "duplicate-check-example", "education", "extension", "features", "feed", "fetch-current-bid",
  "flag_issue", "follow", "generate_bid_image", "get-github-data", "get-recommended-articles",
  "get-recommended-communities", "get-recommended-discussion-channels", "get-recommended-repos",
  "get_unique_issues", "github-issues", "github-webhook", "googleplayapp", "gsoc", "hackathons",
  "hunt", "i18n", "initiate-transaction", "invite", "invite-friend", "issue", "issues", "jobs",
  "join", "label_activity", "leaderboard", "like_issue", "map", "messaging", "notifications",
  "oauth", "open-source-sorting-hat", "organization", "organizations", "owasp", "page-vote",
  "pending-transactions", "privacypolicy", "profile", "project", "projects", "queue", "ratings",
  "redoc", "referral", "reminder-settings", "remove_user_from_issue", "repo_list", "report",
  "report-ip", "reported-ips", "repos", "repository", "resolve", "rest-auth", "review", "roadmap",
  "save_issue", "scoreboard", "search", "security", "select_bid", "select_contribution",
  "send-test-reminder", "sendgrid_webhook", "set-theme", "similarity_scan", "simulation",
  "sitemap", "sizzle", "sizzle-daily-log", "sizzle-docs", "slack", "social", "socialaccounts",
  "sponsor", "staking", "start", "stats", "stats-dashboard", "status", "status_page",
  "style-guide", "submit-roadmap-pr", "swagger", "teams", "template_list", "terms",
  "time-logs", "trademarks", "tz_detect", "update-submission-status", "update_bch_address",
  "upload", "user-sizzle-report", "user_challenges", "users", "video_call", "view-pr-analysis",
  "vote_count", "website_stats", "weekly-report",
  // Django's STATIC_URL and MEDIA_URL (settings.py), for old hot-linked images and files.
  "static", "media",
]);

// Second segment under /api/ -> legacy. blt-next owns its own /api/* routes
// (stats, auth, bugs, leaderboard, projects), so "api" is not matched as a whole.
export const LEGACY_API_SEGMENTS = new Set([
  "bacon", "debug", "get-wallet-balance", "load-more-issues", "messaging", "organization", "ossh",
  "room-messages", "send-message", "timelogsreport", "trademarks", "v1", "v2",
]);

// urls.py segments deliberately not redirected to legacy: the site root,
// files blt-home serves itself, and debug-only routes.
export const LEGACY_EXCLUDED = new Set(["", "api", "favicon", "robots", "500", "__debug__", "test-sentry"]);

export function isLegacyPath(pathname) {
  const parts = pathname.split("/");
  const first = parts[1] || "";
  if (first === "api") return LEGACY_API_SEGMENTS.has(parts[2] || "");
  return LEGACY_SEGMENTS.has(first);
}
