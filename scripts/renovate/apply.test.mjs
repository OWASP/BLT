// node --test scripts/renovate/apply.test.mjs  (also run by scripts/ci/test.sh scripts)
import assert from "node:assert/strict";
import { createHash, createPublicKey, verify } from "node:crypto";
import test from "node:test";
import * as A from "./apply.mjs";
import * as P from "./forge-pulls.mjs";

const SEED = "11".repeat(32);
const sha256 = (text) => createHash("sha256").update(text, "utf8").digest("hex");
const publicKey = (author) => createPublicKey({ key: { kty: "OKP", crv: "Ed25519", x: author }, format: "jwk" });
// app/src/events.py: verify_pull_event and verify_pull_revision, v2 messages for owasp-blt/BLT.
const verifyPull = (pr) =>
  verify(
    null,
    Buffer.from(`forkmesh-pull-event-v2\nowasp-blt/blt\n${pr.author}\n${pr.ts}\n${sha256([pr.title, pr.base, pr.head, pr.patch, pr.commits].join("\u0000"))}`),
    publicKey(pr.author),
    Buffer.from(pr.sig, "base64url"),
  );
const verifyRevision = (number, ev) =>
  verifyPull(ev) &&
  verify(
    null,
    Buffer.from(`forkmesh-pull-revision-v2\nowasp-blt/blt\n${number}\n${ev.author}\n${ev.ts}\n${ev.sig}`),
    publicKey(ev.author),
    Buffer.from(ev.revisionSig, "base64url"),
  );

const fields = { title: "deps: update x", description: "d", base: "main", head: "renovate/npm-minor", patch: "diff --git a/x b/x\n", commits: "From abc\n", ts: 1800000000, baseOid: "a".repeat(40) };

test("pulls and revisions carry signatures the forge accepts", () => {
  const signer = P.makePullSigner(SEED);
  const pull = signer.pull(fields);
  assert.ok(verifyPull(pull));
  assert.equal(pull.authorName, "blt-renovate");
  assert.equal(pull.aiModel, "None");
  assert.equal(pull.creationBaseOid, "a".repeat(40));
  assert.ok(!verifyPull({ ...pull, patch: "tampered" }));
  const revision = signer.revision(12, { ...fields, ts: fields.ts + 60 });
  assert.ok(verifyRevision(12, revision));
  assert.ok(!verifyRevision(13, revision));
  assert.equal(revision.description, undefined);
  assert.equal(P.makePullSigner(SEED).author, signer.author);
});

test("readBotPulls keeps only the key's pull requests, with head and body", async () => {
  const signer = P.makePullSigner(SEED);
  const getJson = async (url) => {
    const u = new URL(url);
    if (u.pathname.endsWith("/tree")) return { status: 200, data: { entries: [{ name: "3", type: "tree" }, { name: "4", type: "tree" }] } };
    return {
      status: 200,
      data: {
        blobs: {
          ".forkmesh/pulls/3/pull.md": `---\nhead: renovate/npm-minor\nstatus: open\nauthor: ${signer.author}\n---\nbody <!-- m -->`,
          ".forkmesh/pulls/4/pull.md": "---\nhead: renovate/npm-minor\nstatus: open\nauthor: someone-else\n---\n",
        },
      },
    };
  };
  assert.deepEqual(await P.readBotPulls(getJson, signer.author), [{ number: 3, head: "renovate/npm-minor", status: "open", body: "body <!-- m -->" }]);
  assert.deepEqual(await P.readBotPulls(async () => ({ status: 404, data: null }), signer.author), []);
});

const report = {
  repositories: {
    local: {
      packageFiles: {
        npm: [
          {
            packageFile: "blt-a/package.json",
            lockFiles: ["blt-a/package-lock.json"],
            deps: [
              { depName: "left-pad", depType: "dependencies", currentValue: "^1.0.0", lockedVersion: "1.0.0", updates: [{ branchName: "renovate/npm-minor", newValue: "^1.0.0", newVersion: "1.3.0", updateType: "minor", isLockfileUpdate: true, newVersionAgeInDays: 30 }] },
              { depName: "vite", depType: "devDependencies", currentValue: "^5.4.0", updates: [{ branchName: "renovate/vite-8.x", newValue: "^8.0.0", newVersion: "8.3.5", updateType: "major", newVersionAgeInDays: 10 }] },
              { depName: "fresh", depType: "dependencies", currentValue: "1.0.0", updates: [{ branchName: "renovate/npm-minor", newValue: "1.1.0", newVersion: "1.1.0", updateType: "minor", newVersionAgeInDays: 1 }] },
            ],
          },
        ],
        pub: [{ packageFile: "app/pubspec.yaml", deps: [{ depName: "intl", currentValue: "^0.19.0", updates: [{ branchName: "renovate/pub-report", newValue: "^0.20.0", newVersion: "0.20.0", updateType: "minor" }] }] }],
      },
    },
  },
};

test("readUpdates flattens the report and drops versions younger than the minimum age", () => {
  const updates = A.readUpdates(report);
  assert.deepEqual(updates.map((u) => [u.depName, u.group, u.lockOnly]), [["left-pad", "npm-minor", true], ["vite", "vite-8.x", false], ["intl", "pub-report", false]]);
});

test("groups: non-major first, pub/cargo never applied", () => {
  const groups = A.groupUpdates(A.readUpdates(report));
  assert.deepEqual(groups.map((g) => [g.head, g.applicable]), [["renovate/npm-minor", true], ["renovate/pub-report", false], ["renovate/vite-8.x", true]]);
  assert.equal(A.pullTitle(groups[0]), "deps: update npm non-major dependencies");
  assert.equal(A.pullTitle(groups[2]), "deps: update vite to 8.3.5");
});

test("plan: keeps open pull requests, opens up to the cap, revises changed ones", () => {
  const groups = A.groupUpdates(A.readUpdates(report));
  const [npm, pub, vite] = groups;
  const open = [{ number: 7, head: "renovate/npm-minor", status: "open", body: `x ${A.pullMarker(npm)}` }];
  assert.deepEqual(A.plan(groups, open).map((s) => s.action), ["current", "report", "open"]);
  assert.deepEqual(A.plan(groups, [{ ...open[0], body: "old" }], { max: 1 }).map((s) => s.action), ["update", "report", "wait"]);
  assert.equal(A.plan([vite], [], { max: 0 })[0].action, "wait");
  const closed = [{ number: 8, head: "renovate/vite-8.x", status: "closed", body: A.pullMarker(vite) }];
  assert.equal(A.plan([vite], closed)[0].action, "declined");
  assert.equal(A.plan([vite], [{ ...closed[0], body: "older versions" }])[0].action, "open");
  assert.notEqual(A.groupKey(npm), A.groupKey(vite));
  assert.equal(pub.applicable, false);
});

test("package.json: only the named dependency's exact value changes", () => {
  const text = '{\n  "dependencies": {\n    "a": "^1.0.0"\n  },\n  "devDependencies": {\n    "vite": "^5.4.0"\n  }\n}\n';
  assert.equal(
    A.updatePackageJson(text, { depType: "devDependencies", depName: "vite", currentValue: "^5.4.0", newValue: "^8.0.0" }),
    text.replace("^5.4.0", "^8.0.0"),
  );
  assert.equal(A.updatePackageJson(text, { depType: "dependencies", depName: "vite", currentValue: "^5.4.0", newValue: "^8.0.0" }), null);
});

test("Python requirements: names match per PEP 503, extras and markers stay", () => {
  const u = { depName: "Django-Filter", currentValue: ">=25.2,<26", newValue: ">=26.2,<27" };
  assert.equal(A.updateRequirement('django_filter[x] >=25.2,<26 ; python_version>"3"', u), 'django_filter[x] >=26.2,<27 ; python_version>"3"');
  assert.equal(A.updateRequirement("django-filters>=25.2,<26", u), null);
  const toml = '[project]\ndependencies = [\n  "django-filter>=25.2,<26",\n  "django>=5.2,<6",\n]\n';
  assert.equal(A.updatePyproject(toml, u), toml.replace(">=25.2,<26", ">=26.2,<27"));
  const req = "# pinned\nrequests==2.32.4\nPyYAML==6.0.1  # yaml\n";
  assert.equal(A.updateRequirementsTxt(req, { depName: "pyyaml", currentValue: "==6.0.1", newValue: "==6.0.3" }), req.replace("6.0.1", "6.0.3"));
  assert.equal(A.updateRequirementsTxt(req, { depName: "flask", currentValue: "==1", newValue: "==2" }), null);
});

test("descriptions and the dashboard keep manifest text inert", () => {
  const groups = A.groupUpdates(A.readUpdates(report));
  const body = A.pullDescription(groups[0]);
  assert.match(body, /AI model: None/);
  assert.match(body, /<!-- blt-renovate:renovate\/npm-minor:[0-9a-f]{16} -->$/);
  assert.match(body, /`1\.0\.0` → `1\.3\.0` \(lockfile\)/);
  const steps = A.plan(groups, []);
  steps[0].number = 9;
  const dash = A.dashboardBody(steps, { problems: ["x"], url: "https://forge.test" });
  assert.match(dash, /\[#9\]\(https:\/\/forge\.test\/BLT\/pulls\/9\)/);
  assert.match(dash, /Listed only/);
  assert.equal(A.dashboardMarker(dash), A.dashboardMarker(dash));
  const evil = A.groupUpdates([{ ...A.readUpdates(report)[1], depName: "<img src=x>", group: "x" }]);
  assert.doesNotMatch(A.pullDescription(evil[0]), /<img/);
});
