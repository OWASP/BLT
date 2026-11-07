// Build blog.owaspblt.org into dist/: public/ as it is, then one page per post, the home page,
// a page per tag, feed.xml, sitemap.xml and 404.html.
//
// Posts live in posts/ (any depth) as .md (Markdown) or .html (an HTML body, as the dev.to
// import writes). Each starts with a front matter block of `key: value` lines between `---`
// lines; a value is JSON ("text", ["a", "b"], 3, true) or plain text. Keys: title, date
// (YYYY-MM-DD), author, and optionally slug, updated, author_url, author_avatar, description,
// tags, cover, reading_time, canonical (when the post was first published elsewhere), source,
// draft (true leaves it out).
//
//   node scripts/build.mjs [--out dist]

import { cpSync, existsSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { marked } from "marked";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
export const SITE = {
  url: "https://blog.owaspblt.org",
  title: "OWASP BLT Blog",
  description: "News, release notes and contributor stories from OWASP BLT, the open-source bug logging and security community project.",
};

export function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

export function slugify(text) {
  return String(text).toLowerCase().normalize("NFKD").replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
}

export function parseFrontMatter(text) {
  const match = /^---\r?\n([\s\S]*?)\r?\n---\r?\n?/.exec(text);
  if (!match) return { data: {}, body: text };
  const data = {};
  for (const line of match[1].split(/\r?\n/)) {
    const pair = /^([A-Za-z_][\w-]*):\s*(.*)$/.exec(line);
    if (!pair) continue;
    const raw = pair[2].trim();
    try {
      data[pair[1]] = JSON.parse(raw);
    } catch {
      data[pair[1]] = raw;
    }
  }
  return { data, body: text.slice(match[0].length) };
}

function walk(dir) {
  if (!existsSync(dir)) return [];
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) return walk(path);
    return /\.(md|html)$/.test(entry.name) ? [path] : [];
  });
}

function readingTime(html) {
  const words = html.replace(/<[^>]+>/g, " ").split(/\s+/).filter(Boolean).length;
  return Math.max(1, Math.round(words / 220));
}

// An image alone in its paragraph becomes a figure, captioned with its alt text.
export function figures(html) {
  return html.replace(/<p>(<img src="([^"]*)" alt="([^"]*)"[^>]*>)<\/p>/g, (_, img, src, alt) =>
    `<figure><a href="${src}">${img.replace("<img ", '<img loading="lazy" ')}</a>${alt ? `<figcaption>${alt}</figcaption>` : ""}</figure>`);
}

export function loadPosts(dir = join(ROOT, "posts")) {
  const posts = [];
  const seen = new Map();
  for (const file of walk(dir)) {
    const { data, body } = parseFrontMatter(readFileSync(file, "utf8"));
    if (data.draft === true) continue;
    const name = relative(dir, file);
    for (const key of ["title", "date", "author"]) {
      if (!data[key]) throw new Error(`${name}: front matter needs ${key}`);
    }
    if (!/^\d{4}-\d{2}-\d{2}$/.test(String(data.date))) throw new Error(`${name}: date must be YYYY-MM-DD`);
    const slug = slugify(data.slug || data.title);
    if (seen.has(slug)) throw new Error(`${name}: slug "${slug}" is also used by ${seen.get(slug)}`);
    seen.set(slug, name);
    const html = file.endsWith(".md") ? figures(marked.parse(body)) : body;
    posts.push({
      ...data,
      slug,
      tags: Array.isArray(data.tags) ? data.tags.map(String) : [],
      html,
      reading_time: Number(data.reading_time) || readingTime(html),
      description: data.description || html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim().slice(0, 200),
      file: name,
    });
  }
  return posts.sort((a, b) => b.date.localeCompare(a.date) || a.title.localeCompare(b.title));
}

export function formatDate(date) {
  return new Date(`${date}T12:00:00Z`).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric", timeZone: "UTC" });
}

function absolute(url) {
  return /^https?:\/\//.test(url) ? url : `${SITE.url}${url}`;
}

function layout({ title, description, path, body, image, canonical, type = "website", extraHead = "" }) {
  const pageTitle = title ? `${title} · ${SITE.title}` : SITE.title;
  const url = canonical || `${SITE.url}${path}`;
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>${escapeHtml(pageTitle)}</title>
  <meta name="description" content="${escapeHtml(description)}" />
  <link rel="canonical" href="${escapeHtml(url)}" />
  <link rel="icon" type="image/svg+xml" href="/logo.svg" />
  <link rel="alternate" type="application/rss+xml" title="${escapeHtml(SITE.title)}" href="/feed.xml" />
  <meta property="og:site_name" content="${escapeHtml(SITE.title)}" />
  <meta property="og:type" content="${type}" />
  <meta property="og:title" content="${escapeHtml(title || SITE.title)}" />
  <meta property="og:description" content="${escapeHtml(description)}" />
  <meta property="og:url" content="${escapeHtml(`${SITE.url}${path}`)}" />
${image ? `  <meta property="og:image" content="${escapeHtml(absolute(image))}" />\n` : ""}  <meta name="twitter:card" content="${image ? "summary_large_image" : "summary"}" />
  <meta name="twitter:site" content="@OWASP_BLT" />${extraHead}
  <script src="/theme-init.js"></script>
  <script src="https://owaspblt.org/_shared/blt-nav.js" defer></script>
  <link rel="stylesheet" href="/style.css" />
</head>
<body>
  <blt-nav project="blt-blog" name="Blog">
    <a href="/">Posts</a>
    <a href="/tags/">Tags</a>
    <a href="/feed.xml" slot="actions">RSS</a>
    <a href="https://git.owaspblt.org/BLT/BLT-Blog" slot="actions" data-primary>Write a post</a>
  </blt-nav>
  <main>
${body}
  </main>
  <footer class="site-footer">
    <p>OWASP BLT is an open-source <a href="https://owasp.org/www-project-bug-logging-tool/">OWASP project</a>. Posts are written by the BLT community; each post says who wrote it.</p>
    <p><a href="/feed.xml">RSS feed</a> · <a href="https://dev.to/owaspblt">dev.to/owaspblt</a> · <a href="https://git.owaspblt.org/BLT/BLT-Blog">Source</a></p>
  </footer>
</body>
</html>
`;
}

function tagLinks(tags) {
  if (!tags.length) return "";
  return `<ul class="tags">${tags.map((tag) => `<li><a href="/tags/${slugify(tag)}/">#${escapeHtml(tag)}</a></li>`).join("")}</ul>`;
}

function byline(post) {
  const avatar = post.author_avatar
    ? `<img class="avatar" src="${escapeHtml(post.author_avatar)}" alt="" width="36" height="36" loading="lazy" />`
    : "";
  const name = post.author_url
    ? `<a href="${escapeHtml(post.author_url)}" rel="author">${escapeHtml(post.author)}</a>`
    : escapeHtml(post.author);
  return `<div class="byline">${avatar}<span><span class="author">${name}</span><span class="meta"><time datetime="${post.date}">${formatDate(post.date)}</time> · ${post.reading_time} min read</span></span></div>`;
}

function card(post, featured = false) {
  const cover = post.cover
    ? `<img src="${escapeHtml(post.cover)}" alt="" loading="${featured ? "eager" : "lazy"}" />`
    : `<div class="cover-fallback" aria-hidden="true"><img src="/logo.svg" alt="" /></div>`;
  return `<article class="card${featured ? " featured" : ""}">
      <a class="cover" href="/${post.slug}/" tabindex="-1" aria-hidden="true">${cover}</a>
      <div class="card-body">
        ${tagLinks(post.tags.slice(0, 4))}
        <h${featured ? 2 : 3}><a href="/${post.slug}/">${escapeHtml(post.title)}</a></h${featured ? 2 : 3}>
        <p>${escapeHtml(post.description)}</p>
        ${byline(post)}
      </div>
    </article>`;
}

function listPage(posts, { title, intro, path }) {
  const [first, ...rest] = posts;
  const body = `    <header class="page-head">
      <h1>${escapeHtml(title)}</h1>
      <p>${intro}</p>
    </header>
    ${path === "/" && first ? card(first, true) : ""}
    <div class="grid">
    ${(path === "/" ? rest : posts).map((post) => card(post)).join("\n    ")}
    </div>`;
  return layout({ title: path === "/" ? "" : title, description: path === "/" ? SITE.description : `${title} on the ${SITE.title}.`, path, body });
}

function postPage(post, older, newer) {
  const source = post.source && post.canonical !== `${SITE.url}/${post.slug}/`
    ? `<p class="origin">First published on <a href="${escapeHtml(post.canonical || post.source)}">${escapeHtml(new URL(post.canonical || post.source).hostname)}</a>${post.source !== post.canonical ? ` and <a href="${escapeHtml(post.source)}">dev.to</a>` : ""}.</p>`
    : "";
  const nav = [
    newer ? `<a class="newer" href="/${newer.slug}/"><span>Newer</span>${escapeHtml(newer.title)}</a>` : "<span></span>",
    older ? `<a class="older" href="/${older.slug}/"><span>Older</span>${escapeHtml(older.title)}</a>` : "<span></span>",
  ].join("");
  const ld = {
    "@context": "https://schema.org",
    "@type": "BlogPosting",
    headline: post.title,
    datePublished: post.date,
    dateModified: post.updated || post.date,
    author: { "@type": "Person", name: post.author, ...(post.author_url ? { url: post.author_url } : {}) },
    publisher: { "@type": "Organization", name: "OWASP BLT", url: "https://owaspblt.org/" },
    mainEntityOfPage: `${SITE.url}/${post.slug}/`,
    ...(post.cover ? { image: absolute(post.cover) } : {}),
  };
  const body = `    <article class="post">
      <header>
        ${tagLinks(post.tags)}
        <h1>${escapeHtml(post.title)}</h1>
        ${byline(post)}
      </header>
      ${post.cover ? `<img class="post-cover" src="${escapeHtml(post.cover)}" alt="" />` : ""}
      <div class="prose">
${post.html}
      </div>
      ${source}
    </article>
    <nav class="post-nav" aria-label="More posts">${nav}</nav>`;
  return layout({
    title: post.title,
    description: post.description,
    path: `/${post.slug}/`,
    body,
    image: post.cover,
    canonical: post.canonical,
    type: "article",
    extraHead: `\n  <meta property="article:published_time" content="${post.date}" />\n  <script type="application/ld+json">${JSON.stringify(ld).replace(/</g, "\\u003c")}</script>`,
  });
}

function feed(posts) {
  const items = posts.slice(0, 30).map((post) => `    <item>
      <title>${escapeHtml(post.title)}</title>
      <link>${SITE.url}/${post.slug}/</link>
      <guid isPermaLink="true">${SITE.url}/${post.slug}/</guid>
      <pubDate>${new Date(`${post.date}T12:00:00Z`).toUTCString()}</pubDate>
      <dc:creator>${escapeHtml(post.author)}</dc:creator>
      ${post.tags.map((tag) => `<category>${escapeHtml(tag)}</category>`).join("")}
      <description>${escapeHtml(post.description)}</description>
    </item>`).join("\n");
  return `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel>
    <title>${escapeHtml(SITE.title)}</title>
    <link>${SITE.url}/</link>
    <atom:link href="${SITE.url}/feed.xml" rel="self" type="application/rss+xml" />
    <description>${escapeHtml(SITE.description)}</description>
    <language>en</language>
${items}
  </channel>
</rss>
`;
}

function sitemap(posts, tags) {
  const urls = ["/", "/tags/", ...posts.map((p) => `/${p.slug}/`), ...tags.map((t) => `/tags/${slugify(t)}/`)];
  return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls.map((u) => `  <url><loc>${SITE.url}${u}</loc></url>`).join("\n")}
</urlset>
`;
}

function write(out, path, content) {
  const file = join(out, path);
  mkdirSync(dirname(file), { recursive: true });
  writeFileSync(file, content);
}

export function build(out = join(ROOT, "dist"), postsDir = join(ROOT, "posts")) {
  const posts = loadPosts(postsDir);
  rmSync(out, { recursive: true, force: true });
  cpSync(join(ROOT, "public"), out, { recursive: true });

  write(out, "index.html", listPage(posts, {
    title: "OWASP BLT Blog",
    intro: "News, release notes and stories from the people who build OWASP BLT. Want to write one? <a href=\"https://git.owaspblt.org/BLT/BLT-Blog\">Add a Markdown file</a> and open a pull request.",
    path: "/",
  }));
  posts.forEach((post, i) => write(out, `${post.slug}/index.html`, postPage(post, posts[i + 1], posts[i - 1])));

  const tagCounts = new Map();
  for (const post of posts) for (const tag of post.tags) tagCounts.set(tag, (tagCounts.get(tag) || 0) + 1);
  const tags = [...tagCounts.keys()].sort((a, b) => tagCounts.get(b) - tagCounts.get(a) || a.localeCompare(b));
  for (const tag of tags) {
    const tagged = posts.filter((post) => post.tags.includes(tag));
    write(out, `tags/${slugify(tag)}/index.html`, listPage(tagged, {
      title: `#${tag}`,
      intro: `${tagged.length} post${tagged.length === 1 ? "" : "s"} tagged #${escapeHtml(tag)}. <a href="/tags/">All tags</a>`,
      path: `/tags/${slugify(tag)}/`,
    }));
  }
  write(out, "tags/index.html", layout({
    title: "Tags",
    description: `Every tag on the ${SITE.title}.`,
    path: "/tags/",
    body: `    <header class="page-head"><h1>Tags</h1><p>${posts.length} posts, ${tags.length} tags.</p></header>
    <ul class="tag-cloud">${tags.map((tag) => `<li><a href="/tags/${slugify(tag)}/">#${escapeHtml(tag)} <span>${tagCounts.get(tag)}</span></a></li>`).join("")}</ul>`,
  }));
  write(out, "feed.xml", feed(posts));
  write(out, "sitemap.xml", sitemap(posts, tags));
  write(out, "robots.txt", `User-agent: *\nAllow: /\nSitemap: ${SITE.url}/sitemap.xml\n`);
  write(out, "404.html", layout({
    title: "Not found",
    description: "That page isn't on the blog.",
    path: "/404.html",
    body: `    <header class="page-head"><h1>Not found</h1><p>That page isn't on the blog. Try <a href="/">the latest posts</a>.</p></header>`,
  }));
  return { posts, tags };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const i = process.argv.indexOf("--out");
  const { posts, tags } = build(i > 0 ? resolve(process.argv[i + 1]) : undefined);
  console.log(`built ${posts.length} posts and ${tags.length} tags`);
}
