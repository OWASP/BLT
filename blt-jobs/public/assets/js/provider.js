(function () {
  const defaultRepo = "owasp-blt/blt-jobs";
  const params = new URLSearchParams(window.location.search);
  const repoParam = params.get("repo");
  const repo =
    typeof repoParam === "string" && /^[A-Za-z0-9._-]+\/[A-Za-z0-9._-]+$/.test(repoParam)
      ? repoParam
      : defaultRepo;
  const repositoryUrl = "https://gitlab.com/" + repo;
  const sourceRef = "main";
  const iconClass = "fa-brands fa-gitlab";

  function encodePath(relativePath) {
    return String(relativePath || "")
      .split("/")
      .map((part) => encodeURIComponent(part))
      .join("/");
  }

  function issueUrl(template) {
    const query = template ? "?issuable_template=" + encodeURIComponent(template) : "";
    return repositoryUrl + "/-/issues/new" + query;
  }

  function sourceFileUrl(relativePath) {
    return repositoryUrl + "/-/blob/" + sourceRef + "/" + encodePath(relativePath);
  }

  window.BLTProvider = {
    id: "gitlab",
    name: "GitLab",
    iconClass,
    repositoryUrl,
    sourceRef,
    issueUrl,
    sourceFileUrl,
  };

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-provider-repository]").forEach(function (link) {
      link.href = repositoryUrl;
    });
  });
})();
