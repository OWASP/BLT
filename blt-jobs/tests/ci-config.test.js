const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const yaml = require("js-yaml");

const projectDir = path.join(__dirname, "..");
const workflowDir = path.join(projectDir, "..", ".forkmesh");

test("blt-jobs workflows run steps that exist in this project", () => {
  const files = fs.readdirSync(workflowDir).filter((f) => f.startsWith("blt-jobs--") && f.endsWith(".yml"));
  assert.ok(files.length >= 2, "expected the blt-jobs workflows in .forkmesh/");
  for (const file of files) {
    const workflow = yaml.load(fs.readFileSync(path.join(workflowDir, file), "utf8"));
    for (const [jobName, job] of Object.entries(workflow.jobs)) {
      assert.equal(job.defaults.run["working-directory"], "blt-jobs", `${file} ${jobName}`);
      for (const step of job.steps) {
        assert.equal(typeof step.run, "string", `${file} ${jobName}: every step is a run step`);
        for (const [, script] of step.run.matchAll(/node (scripts\/\S+)/g)) {
          assert.ok(fs.existsSync(path.join(projectDir, script)), `${file}: ${script} exists`);
        }
      }
    }
  }
});

test("process-submission maps platform issues to the GitLab shape createFromIssue expects", async () => {
  const { toGitlabIssue } = await import("../scripts/actions/process-submission.mjs");
  process.env.FORKMESH_API_URL = "https://git.example.org";
  process.env.GITHUB_REPOSITORY = "BLT/BLT";
  const issue = toGitlabIssue({
    number: 12,
    title: "[FLAG] job",
    body: "### Job ID\n\nabc",
    state: "open",
    labels: [{ name: "flag-job-posting" }],
    user: { login: "alice" },
  });
  assert.deepEqual(issue, {
    iid: 12,
    title: "[FLAG] job",
    description: "### Job ID\n\nabc",
    labels: ["flag-job-posting"],
    author: { username: "alice", web_url: "https://git.example.org/alice" },
    web_url: "https://git.example.org/BLT/BLT/issues/12",
    state: "open",
  });
});
