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

test("browser provider points every link at git.owaspblt.org, never gitlab.com", () => {
  const { links, provider } = loadProvider("?repo=owasp-blt/blt-jobs");

  assert.equal(provider.id, "forge");
  assert.equal(provider.repositoryUrl, "https://git.owaspblt.org/BLT/tree/main/blt-jobs");
  assert.equal(links[0].href, provider.repositoryUrl);
  assert.equal(provider.issueUrl("job-posting"), "https://git.owaspblt.org/BLT/issues/new");
  assert.equal(
    provider.templateUrl("job-posting"),
    "https://git.owaspblt.org/BLT/blob/main/blt-jobs/issue-templates/job-posting.md"
  );
  assert.equal(
    provider.sourceFileUrl("jobs/job with spaces.md"),
    "https://git.owaspblt.org/BLT/blob/main/blt-jobs/jobs/job%20with%20spaces.md"
  );
});

test("no page or script sends users to gitlab.com/owasp-blt", () => {
  const publicDir = path.join(__dirname, "..", "public");
  const offenders = [];
  const walk = (dir) => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        if (entry.name !== "vendor" && entry.name !== "data") walk(full);
      } else if (/\.(html|js)$/.test(entry.name) && /gitlab\.com\/owasp-blt|BLT\/BLT-Jobs/i.test(fs.readFileSync(full, "utf8"))) {
        offenders.push(path.relative(publicDir, full));
      }
    }
  };
  walk(publicDir);
  assert.deepEqual(offenders, []);
});
