const DEFAULT_PROVIDER_ID = "gitlab";
const DEFAULT_PROVIDER_NAME = "GitLab";
const DEFAULT_REPOSITORY_URL = "https://gitlab.com/owasp-blt/blt-jobs";
const DEFAULT_SOURCE_REF = "main";

function trimTrailingSlash(value) {
  return String(value || "").replace(/\/+$/, "");
}

function encodePath(relativePath) {
  return String(relativePath || "")
    .split("/")
    .map((part) => encodeURIComponent(part))
    .join("/");
}

function providerName(providerId) {
  if (providerId === "github") return "GitHub";
  if (providerId === "gitea") return "Gitea";
  if (providerId === "forgejo") return "Forgejo";
  if (providerId === "generic-git") return "Generic Git";
  if (providerId === "manual") return "Manual";
  return DEFAULT_PROVIDER_NAME;
}

function createProviderConfig(options = {}) {
  const id = options.providerId || process.env.BLT_PROVIDER_ID || DEFAULT_PROVIDER_ID;
  const name = options.providerName || process.env.BLT_PROVIDER_NAME || providerName(id);
  const repositoryUrl = trimTrailingSlash(
    options.repositoryUrl || process.env.BLT_REPOSITORY_URL || DEFAULT_REPOSITORY_URL
  );
  const sourceRef = options.sourceRef || process.env.BLT_SOURCE_REF || DEFAULT_SOURCE_REF;

  function sourceFileUrl(relativePath) {
    const encoded = encodePath(relativePath);
    if (!repositoryUrl || !encoded) return "";
    if (id === "github") return `${repositoryUrl}/blob/${encodeURIComponent(sourceRef)}/${encoded}`;
    if (id === "gitlab") return `${repositoryUrl}/-/blob/${encodeURIComponent(sourceRef)}/${encoded}`;
    return `${repositoryUrl}`;
  }

  function issueUrl(template) {
    if (!repositoryUrl) return "";
    if (id === "gitlab") {
      const query = template ? `?issuable_template=${encodeURIComponent(template)}` : "";
      return `${repositoryUrl}/-/issues/new${query}`;
    }
    if (id === "github") return `${repositoryUrl}/issues/new`;
    return repositoryUrl;
  }

  return {
    id,
    name,
    repositoryUrl,
    sourceRef,
    issueUrl,
    sourceFileUrl,
    summary() {
      return {
        source: {
          provider: {
            id,
            name,
            repository_url: repositoryUrl,
            source_ref: sourceRef,
          },
        },
      };
    },
  };
}

module.exports = {
  DEFAULT_PROVIDER_ID,
  DEFAULT_PROVIDER_NAME,
  DEFAULT_REPOSITORY_URL,
  DEFAULT_SOURCE_REF,
  createProviderConfig,
};
