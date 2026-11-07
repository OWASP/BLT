import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { build, escapeHtml, loadPosts, parseFrontMatter, slugify } from "../scripts/build.mjs";

test("front matter takes JSON values and plain text", () => {
  const { data, body } = parseFrontMatter('---\ntitle: "A: b"\ntags: ["x", "y"]\nauthor: Plain Name\ndraft: true\n---\n# Hi\n');
  assert.deepEqual(data, { title: "A: b", tags: ["x", "y"], author: "Plain Name", draft: true });
  assert.equal(body, "# Hi\n");
});

test("slugify and escapeHtml", () => {
  assert.equal(slugify("Why OWASP BLT? 5 to 50+ PRs!"), "why-owasp-blt-5-to-50-prs");
  assert.equal(escapeHtml(`<a href="x">'&'</a>`), "&lt;a href=&quot;x&quot;&gt;&#39;&amp;&#39;&lt;/a&gt;");
});

test("every post in posts/ loads with a unique slug, a date and an author", () => {
  const posts = loadPosts();
  assert.ok(posts.length >= 33);
  for (const post of posts) {
    assert.match(post.date, /^\d{4}-\d{2}-\d{2}$/, post.file);
    assert.ok(post.author, post.file);
    assert.doesNotMatch(post.html, /<script\b/i, `${post.file} has a script tag`);
    assert.doesNotMatch(post.html, /\son[a-z]+\s*=/i, `${post.file} has an event handler`);
  }
  assert.deepEqual(posts.map((p) => p.date), [...posts.map((p) => p.date)].sort().reverse());
});

test("imported images are local files", () => {
  const root = new URL("..", import.meta.url).pathname;
  for (const post of loadPosts()) {
    const srcs = [...post.html.matchAll(/<img\b[^>]*\bsrc="([^"]+)"/g)].map((m) => m[1]);
    if (post.cover) srcs.push(post.cover);
    for (const src of srcs) {
      assert.ok(src.startsWith("/images/") || src.startsWith("https://assets.dev.to/"), `${post.file}: ${src}`);
      if (src.startsWith("/images/")) assert.ok(readFileSync(join(root, "public", src)).length > 0, src);
    }
  }
});

test("build writes pages, tags, feed and sitemap", () => {
  const posts = mkdtempSync(join(tmpdir(), "blt-blog-posts-"));
  mkdirSync(join(posts, "sub"));
  writeFileSync(join(posts, "a.md"), '---\ntitle: "First <post>"\ndate: "2026-01-02"\nauthor: "Ana"\ntags: ["news"]\n---\nHello **world**.\n');
  writeFileSync(join(posts, "sub", "b.html"), '---\ntitle: "Second"\ndate: "2026-02-03"\nauthor: "Bo"\ncanonical: "https://dev.to/x/second"\nsource: "https://dev.to/x/second"\n---\n<p>Body</p>\n');
  writeFileSync(join(posts, "c.md"), '---\ntitle: "Draft"\ndate: "2026-03-01"\nauthor: "Cy"\ndraft: true\n---\nNot yet.\n');
  const out = mkdtempSync(join(tmpdir(), "blt-blog-dist-"));
  const result = build(out, posts);

  assert.deepEqual(result.posts.map((p) => p.slug), ["second", "first-post"]);
  assert.ok(!readdirSync(out).includes("draft"));
  const first = readFileSync(join(out, "first-post", "index.html"), "utf8");
  assert.match(first, /<h1>First &lt;post&gt;<\/h1>/);
  assert.match(first, /<strong>world<\/strong>/);
  assert.match(first, /<link rel="canonical" href="https:\/\/blog\.owaspblt\.org\/first-post\/" \/>/);
  const second = readFileSync(join(out, "second", "index.html"), "utf8");
  assert.match(second, /<link rel="canonical" href="https:\/\/dev\.to\/x\/second" \/>/);
  assert.match(second, /First published on <a href="https:\/\/dev\.to\/x\/second">dev\.to<\/a>/);
  assert.match(readFileSync(join(out, "index.html"), "utf8"), /href="\/second\/"[\s\S]*href="\/first-post\/"/);
  assert.match(readFileSync(join(out, "tags", "news", "index.html"), "utf8"), /First &lt;post&gt;/);
  const feed = readFileSync(join(out, "feed.xml"), "utf8");
  assert.match(feed, /<link>https:\/\/blog\.owaspblt\.org\/second\/<\/link>/);
  assert.match(readFileSync(join(out, "sitemap.xml"), "utf8"), /blog\.owaspblt\.org\/tags\/news\//);
  assert.ok(readFileSync(join(out, "404.html"), "utf8").includes("Not found"));
  assert.ok(readFileSync(join(out, "style.css"), "utf8").length > 0);
});

test("a duplicate slug fails the build", () => {
  const posts = mkdtempSync(join(tmpdir(), "blt-blog-dupe-"));
  writeFileSync(join(posts, "a.md"), '---\ntitle: "Same"\ndate: "2026-01-02"\nauthor: "A"\n---\nx\n');
  writeFileSync(join(posts, "b.md"), '---\ntitle: "Same"\ndate: "2026-01-03"\nauthor: "B"\n---\ny\n');
  assert.throws(() => loadPosts(posts), /slug "same"/);
});
