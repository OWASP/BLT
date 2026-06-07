const DEFAULT_REPO_OWNER = "OWASP-BLT";
const DEFAULT_REPO_NAME = "BLT-Newsletter";
const EMAIL_REGEX = /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$/;

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
    },
  });
}

export async function onRequestPost({ request, env }) {
  const token = env.GITHUB_TOKEN || env.GH_TOKEN;
  if (!token) {
    return json({ error: "GitHub token is not configured." }, 500);
  }

  let payload;
  try {
    payload = await request.json();
  } catch (_error) {
    return json({ error: "Invalid JSON request." }, 400);
  }

  const name = String(payload.name || "").trim();
  const email = String(payload.email || "").trim();

  if (!EMAIL_REGEX.test(email)) {
    return json({ error: "Please provide a valid email address." }, 400);
  }

  const owner = env.GITHUB_REPO_OWNER || DEFAULT_REPO_OWNER;
  const repo = env.GITHUB_REPO_NAME || DEFAULT_REPO_NAME;
  const issueTitle = `Newsletter Subscription: ${email}`;
  const issueBody = [
    "New newsletter subscription request:",
    "",
    `- **Name:** ${name || "Not provided"}`,
    `- **Email:** ${email}`,
    `- **Subscribed:** ${new Date().toISOString()}`,
    "",
    "---",
    "*This issue was automatically created by the newsletter signup form.*",
  ].join("\n");

  const response = await fetch(`https://api.github.com/repos/${owner}/${repo}/issues`, {
    method: "POST",
    headers: {
      accept: "application/vnd.github+json",
      authorization: `Bearer ${token}`,
      "content-type": "application/json",
      "user-agent": "BLT-Newsletter-Cloudflare",
      "x-github-api-version": "2022-11-28",
    },
    body: JSON.stringify({
      title: issueTitle,
      body: issueBody,
      labels: ["newsletter-subscription"],
    }),
  });

  if (!response.ok) {
    const details = await response.text();
    return json(
      {
        error: "Unable to create subscription issue.",
        status: response.status,
        details,
      },
      502,
    );
  }

  const issue = await response.json();
  return json({ ok: true, issueUrl: issue.html_url });
}
