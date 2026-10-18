// node --test 'scripts/actions/*.test.mjs'
import { test } from "node:test";
import assert from "node:assert/strict";
import { applyIssues, toProfile, extractCheckboxes } from "./update-profiles.mjs";

const body = [
  "### GitHub Username", "", "octo",
  "### Display Name", "", "_No response_",
  "### Areas of Interest", "", "- [x] Security", "- [ ] Web", "- [X] Rust",
  "### Skills & Technologies", "", "Python, Go ,",
].join("\n");
const issue = (extra = {}) => ({ number: 4, state: "open", body, labels: [{ name: "profile" }], ...extra });

test("profiles are parsed from the issue form", () => {
  const p = toProfile(issue());
  assert.equal(p.github_username, "octo");
  assert.equal(p.display_name, "octo");
  assert.deepEqual(p.interests, ["Security", "Rust"]);
  assert.deepEqual(p.skills, ["Python", "Go"]);
  assert.deepEqual(extractCheckboxes(body, "Missing"), []);
});

test("issues add, keep, update and remove profiles", () => {
  let { profiles, changed } = applyIssues([], new Map([[4, issue()]]));
  assert.equal(changed, true);
  assert.equal(profiles.length, 1);
  ({ changed } = applyIssues(profiles, new Map([[4, issue()]])));
  assert.equal(changed, false);
  ({ profiles, changed } = applyIssues(profiles, new Map([[4, issue({ state: "closed" })]])));
  assert.equal(changed, true);
  assert.equal(profiles.length, 0);
  ({ profiles } = applyIssues([], new Map([[4, issue({ labels: ["other"] })], [5, null]])));
  assert.equal(profiles.length, 0);
});
