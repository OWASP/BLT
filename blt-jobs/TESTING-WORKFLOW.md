# Full workflow testing (no labels, with/without https)

Use this to test the **job-from-URL** flow from the website, without applying any label, and with both URL formats.

---

## Prerequisites

- Your fork has the latest workflow: [Pritz395/BLT-Jobs](https://github.com/Pritz395/BLT-Jobs) (branch `main`).
- You need an HTTP server to open the site (e.g. `python3 -m http.server 8000` from the repo root).

---

## 1. Open the Contribute page for your fork

So that “Open issue” creates issues on **your fork** (where the no-label workflow runs):

- **Local:**  
  `http://localhost:8000/add.html?repo=Pritz395/BLT-Jobs`
- **Fork Pages (if enabled):**  
  `https://pritz395.github.io/BLT-Jobs/add.html?repo=Pritz395/BLT-Jobs`

Confirm the red button says “Open issue: Post job from URL” and that it points to  
`https://github.com/Pritz395/BLT-Jobs/issues/new?template=job-posting-from-link.yml`.

---

## 2. Test A — With `https` (no label)

1. On the Contribute page, click **“Open issue: Post job from URL”**.
2. In the issue:
   - **Title:** e.g. `Test job (with https, no label)`.
   - In **Job URL**, paste a full URL, e.g.  
     `https://boards.greenhouse.io/cloudflare/jobs/7411392`
   - Leave optional fields empty. **Do not add any label.**
3. Click **Submit new issue**.
4. Check:
   - **Actions:** [Pritz395/BLT-Jobs/actions](https://github.com/Pritz395/BLT-Jobs/actions) — “Process issue submissions” run should complete successfully.
   - **Issue:** A comment like “Job added from URL…” and the issue closed.
   - **Jobs:** On `jobs.html` (local or fork Pages), the new job appears.

---

## 3. Test B — Without `https` (no label)

1. Again open the Contribute page with `?repo=Pritz395/BLT-Jobs` and click **“Open issue: Post job from URL”**.
2. In the issue:
   - **Title:** e.g. `Test job (no https, no label)`.
   - In **Job URL**, paste the **same URL without** `https://`, e.g.  
     `boards.greenhouse.io/cloudflare/jobs/7411392`
   - **Do not add any label.**
3. Click **Submit new issue**.
4. Check:
   - **Actions:** “Process issue submissions” runs and succeeds (workflow adds `https://`).
   - **Issue:** Comment and closed as in Test A.
   - **Jobs:** A second listing appears (or the same job if the scraper dedupes by URL).

---

## 4. Optional — Test “edited” (no label)

1. Open **New issue** (no template):  
   `https://github.com/Pritz395/BLT-Jobs/issues/new`
2. **Title:** e.g. `Test job (edited, no label)`  
   **Body:** leave empty. Submit.
3. **Edit** the issue and add only:
   ```text
   ### Job URL
   https://boards.greenhouse.io/cloudflare/jobs/7411392
   ```
   Save.
4. Check Actions and the job board as above; the workflow should run on **edited** and close the issue.

---

## 5. Success criteria

- Both tests run **without** adding the `job-posting-from-link` label.
- Test A works with a full `https://` URL.
- Test B works with a URL that has no scheme (workflow normalizes to `https://`).
- Optional: “Edited” issue also triggers the workflow and adds the job.

After testing, you can open a PR from your fork to [OWASP-BLT/BLT-Jobs](https://github.com/OWASP-BLT/BLT-Jobs) with the workflow (and optional `add.html?repo=` and this doc) changes.
