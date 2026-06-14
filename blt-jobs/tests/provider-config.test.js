const assert = require("node:assert/strict");
const test = require("node:test");

const { createProviderConfig } = require("../scripts/provider-config");

test("GitLab source file URLs preserve slashes in source refs", () => {
  const provider = createProviderConfig({
    providerId: "gitlab",
    repositoryUrl: "https://gitlab.com/owasp-blt/blt-jobs",
    sourceRef: "feature/my-branch",
  });

  assert.equal(
    provider.sourceFileUrl("jobs/example.md"),
    "https://gitlab.com/owasp-blt/blt-jobs/-/blob/feature/my-branch/jobs/example.md"
  );
});

test("provider summary includes icon class for dynamic frontends", () => {
  const provider = createProviderConfig({ providerId: "github" });

  assert.equal(provider.iconClass, "fa-brands fa-github");
  assert.equal(provider.summary().source.provider.icon_class, "fa-brands fa-github");
});

test("GitLab issue URLs use supported issue template query parameter", () => {
  const provider = createProviderConfig({
    providerId: "gitlab",
    repositoryUrl: "https://gitlab.com/owasp-blt/blt-jobs",
  });

  assert.equal(provider.issueUrl(), "https://gitlab.com/owasp-blt/blt-jobs/-/issues/new");
  assert.equal(
    provider.issueUrl("job posting"),
    "https://gitlab.com/owasp-blt/blt-jobs/-/issues/new?issuable_template=job%20posting"
  );
});
