const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const providerScript = fs.readFileSync(path.join(__dirname, "..", "public", "assets", "js", "provider.js"), "utf8");

function loadProvider(search = "") {
  const links = [{ href: "" }];
  const window = { location: { search } };
  const document = {
    addEventListener(event, callback) {
      if (event === "DOMContentLoaded") callback();
    },
    querySelectorAll(selector) {
      return selector === "[data-provider-repository]" ? links : [];
    },
  };

  vm.runInNewContext(providerScript, {
    document,
    URLSearchParams,
    window,
  });

  return { links, provider: window.BLTProvider };
}

test("browser provider accepts only GitLab namespace/project repo overrides", () => {
  assert.equal(
    loadProvider("?repo=owasp-blt/blt-jobs").provider.repositoryUrl,
    "https://gitlab.com/owasp-blt/blt-jobs"
  );

  assert.equal(
    loadProvider("?repo=attacker.example/owasp-blt/blt-jobs").provider.repositoryUrl,
    "https://gitlab.com/owasp-blt/blt-jobs"
  );
});

test("browser provider builds GitLab issue template and source URLs", () => {
  const { links, provider } = loadProvider("?repo=owasp-blt/blt-jobs");

  assert.equal(provider.issueUrl("job posting"), "https://gitlab.com/owasp-blt/blt-jobs/-/issues/new?issuable_template=job%20posting");
  assert.equal(
    provider.sourceFileUrl("jobs/job with spaces.md"),
    "https://gitlab.com/owasp-blt/blt-jobs/-/blob/main/jobs/job%20with%20spaces.md"
  );
  assert.equal(links[0].href, provider.repositoryUrl);
});
