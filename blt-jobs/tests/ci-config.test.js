const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const yaml = require("js-yaml");

function isScriptStringList(value) {
  if (typeof value === "string") return true;
  if (!Array.isArray(value)) return false;
  return value.every(isScriptStringList);
}

test("GitLab CI script entries parse as strings", () => {
  const ciPath = path.join(__dirname, "..", ".gitlab-ci.yml");
  const config = yaml.load(fs.readFileSync(ciPath, "utf8"));

  for (const [jobName, job] of Object.entries(config)) {
    if (!job || typeof job !== "object" || Array.isArray(job)) continue;
    if (job.script) {
      assert.equal(isScriptStringList(job.script), true, `${jobName}.script must contain only strings`);
    }
    if (job.before_script) {
      assert.equal(isScriptStringList(job.before_script), true, `${jobName}.before_script must contain only strings`);
    }
  }
});
