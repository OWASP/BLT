// Where the job board's source, issues and submissions live: the BLT monorepo on git.owaspblt.org
// (single organization; this project is the blt-jobs folder). The old GitLab group is closed.
(function () {
  const forgeUrl = "https://git.owaspblt.org/BLT";
  const folder = "blt-jobs";
  const repositoryUrl = forgeUrl + "/tree/main/" + folder;
  const sourceRef = "main";
  const iconClass = "fa-solid fa-code-branch";

  function encodePath(relativePath) {
    return String(relativePath || "")
      .split("/")
      .map((part) => encodeURIComponent(part))
      .join("/");
  }

  // The forge has no issue templates: new issues start empty, and templateUrl() links to the
  // Markdown template to copy into the issue body (scripts/actions/process-submission.mjs reads
  // its headings).
  function issueUrl() {
    return forgeUrl + "/issues/new";
  }

  function templateUrl(template) {
    return template ? sourceFileUrl("issue-templates/" + template + ".md") : "";
  }

  function sourceFileUrl(relativePath) {
    return forgeUrl + "/blob/" + sourceRef + "/" + folder + "/" + encodePath(relativePath);
  }

  window.BLTProvider = {
    id: "forge",
    name: "git.owaspblt.org",
    iconClass,
    repositoryUrl,
    sourceRef,
    issueUrl,
    templateUrl,
    sourceFileUrl,
  };

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-provider-repository]").forEach(function (link) {
      link.href = repositoryUrl;
    });
  });
})();
