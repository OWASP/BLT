const DEFAULT_PROVIDER_ID = "forge";
const DEFAULT_PROVIDER_NAME = "git.owaspblt.org";
// The BLT monorepo on git.owaspblt.org (single organization); this project is its blt-jobs folder.
const DEFAULT_FORGE_URL = "https://git.owaspblt.org/BLT";
const DEFAULT_FOLDER = "blt-jobs";
const DEFAULT_REPOSITORY_URL = `${DEFAULT_FORGE_URL}/tree/main/${DEFAULT_FOLDER}`;
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

function inferProviderId(repositoryUrl) {
  let host = "";
  try {
    host = new URL(repositoryUrl).hostname.toLowerCase();
  } catch {
    return "forge";
  }
  if (host === "gitlab.com" || host.startsWith("gitlab.")) return "gitlab";
  if (host === "github.com") return "github";
  return "forge";
}

function providerName(providerId) {
  if (providerId === "github") return "GitHub";
  if (providerId === "gitlab") return "GitLab";
  if (providerId === "gitea") return "Gitea";
  if (providerId === "forgejo") return "Forgejo";
  if (providerId === "generic-git") return "Generic Git";
  if (providerId === "manual") return "Manual";
  return DEFAULT_PROVIDER_NAME;
}

function providerIconClass(providerId) {
  if (providerId === "github") return "fa-brands fa-github";
  if (providerId === "gitlab") return "fa-brands fa-gitlab";
  if (providerId === "gitea" || providerId === "forgejo" || providerId === "generic-git") {
    return "fa-solid fa-code-branch";
  }
  return "fa-solid fa-code-branch";
}

function createProviderConfig(options = {}) {
  const repositoryUrl = trimTrailingSlash(
    options.repositoryUrl || process.env.BLT_REPOSITORY_URL || DEFAULT_REPOSITORY_URL
  );
  const id = options.providerId || process.env.BLT_PROVIDER_ID || inferProviderId(repositoryUrl);
  const name = options.providerName || process.env.BLT_PROVIDER_NAME || providerName(id);
  const iconClass = options.iconClass || process.env.BLT_PROVIDER_ICON_CLASS || providerIconClass(id);
  const sourceRef = options.sourceRef || process.env.BLT_SOURCE_REF || DEFAULT_SOURCE_REF;
  // A forge monorepo: files are <forgeUrl>/blob/<ref>/<folder>/<path>, issues <forgeUrl>/issues.
  const forgeUrl = trimTrailingSlash(options.forgeUrl || process.env.BLT_FORGE_URL || DEFAULT_FORGE_URL);
  const folder = options.folder ?? process.env.BLT_FOLDER ?? DEFAULT_FOLDER;

  function sourceFileUrl(relativePath) {
    const encoded = encodePath(relativePath);
    if (!repositoryUrl || !encoded) return "";
    if (id === "forge") return `${forgeUrl}/blob/${sourceRef}/${folder ? `${encodePath(folder)}/` : ""}${encoded}`;
    if (id === "github") return `${repositoryUrl}/blob/${sourceRef}/${encoded}`;
    if (id === "gitlab") return `${repositoryUrl}/-/blob/${sourceRef}/${encoded}`;
    return `${repositoryUrl}`;
  }

  function issueUrl(template) {
    if (!repositoryUrl) return "";
    if (id === "gitlab") {
      const query = template ? `?issuable_template=${encodeURIComponent(template)}` : "";
      return `${repositoryUrl}/-/issues/new${query}`;
    }
    if (id === "github") return `${repositoryUrl}/issues/new`;
    if (id === "forge") return `${forgeUrl}/issues/new`;
    return repositoryUrl;
  }

  return {
    id,
    name,
    iconClass,
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
            icon_class: iconClass,
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
  DEFAULT_FORGE_URL,
  DEFAULT_REPOSITORY_URL,
  DEFAULT_SOURCE_REF,
  createProviderConfig,
};
