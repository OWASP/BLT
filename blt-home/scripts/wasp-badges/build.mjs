// Builds every BLT project logo as one family: the OWASP BLT wasp on a red badge, with the
// project's own symbol in a small round sub-badge at the bottom right.
//
//   node blt-home/scripts/wasp-badges/build.mjs            write all logos
//   node blt-home/scripts/wasp-badges/build.mjs --check    exit 1 if any written file is stale
//   node blt-home/scripts/wasp-badges/build.mjs --variant=red-on-white   alternative main badge
//   node blt-home/scripts/wasp-badges/build.mjs --out=/tmp/x             preview into a folder only
//
// Inputs (all in this folder):
//   symbols/<project>.svg  the project's own symbol: a round badge with its glyph (the project
//                          logo before the wasp family). Edit these to change a project's symbol.
//   targets.json           extra files per project that show the product logo on its site
//                          (header/sub-nav images, SVG favicons). Always written with the badge.
//   ../../public/_home/blt-logo.svg   the wasp (single path).
// Outputs, per project P: P/logo.svg, blt-home/public/_home/logos/P.svg (when the project is on
// the homepage) and every path in targets.json[P]. PNGs (P/logo.png, 512 px) are rendered from
// P/logo.svg separately; see README.md here.
import { readFileSync, writeFileSync, readdirSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const repo = join(here, "..", "..", "..");
const homeLogos = join(repo, "blt-home", "public", "_home", "logos");
const args = new Set(process.argv.slice(2));
const check = args.has("--check");
const outDir = [...args].find((a) => a.startsWith("--out="))?.split("=")[1];
const variant = [...args].find((a) => a.startsWith("--variant="))?.split("=")[1] || "white-on-red";

const RED = "#dc2626";
const waspSvg = readFileSync(join(repo, "blt-home", "public", "_home", "blt-logo.svg"), "utf8");
const waspViewBox = waspSvg.match(/viewBox="([^"]+)"/)[1];
const waspPath = waspSvg.match(/\sd="([^"]+)"/)[1];

// Geometry on a 64-unit canvas. Main badge fills the canvas; the wasp sits up and left so its
// wings and head stay clear of the sub-badge. Sub-badge: ~44% of the main diameter, white ring.
const MAIN = { cx: 32, cy: 32, r: 30 };
const WASP = { x: 9, y: 7, size: 41 };
const SUB = { cx: 48.5, cy: 48.5, r: 13.2, ring: 2.3 };

function symbolParts(svg) {
  const viewBox = (svg.match(/<svg[^>]*\sviewBox="([^"]+)"/) || [])[1] || "0 0 64 64";
  const inner = svg
    .replace(/<\?xml[^>]*>/g, "")
    .replace(/^[\s\S]*?<svg[^>]*>/, "")
    .replace(/<\/svg>\s*$/, "")
    .replace(/<title>[\s\S]*?<\/title>/g, "")
    .trim();
  return { viewBox, inner };
}

// Ids inside a symbol (gradients, clip paths) get a per-project prefix so they never clash.
function prefixIds(inner, prefix) {
  const ids = [...inner.matchAll(/\sid="([^"]+)"/g)].map((m) => m[1]);
  let out = inner;
  for (const id of ids) {
    out = out
      .replaceAll(`id="${id}"`, `id="${prefix}-${id}"`)
      .replaceAll(`url(#${id})`, `url(#${prefix}-${id})`)
      .replaceAll(`href="#${id}"`, `href="#${prefix}-${id}"`);
  }
  return out;
}

function title(project) {
  return project === "my-gsoc-tool"
    ? "MY-GSOC-TOOL"
    : project.replace(/^blt-/, "BLT-").replace(/-([a-z])/g, (_, c) => "-" + c.toUpperCase()).replace(/^BLT-([a-z])/, (_, c) => "BLT-" + c.toUpperCase());
}

export function badge(project, symbolSvg) {
  const { viewBox, inner } = symbolParts(symbolSvg);
  const name = (symbolSvg.match(/<title>([^<]+)<\/title>/) || [])[1] || title(project);
  const s = SUB.r * 2;
  const mainFill = variant === "red-on-white" ? "#ffffff" : RED;
  const waspFill = variant === "red-on-white" ? RED : "#ffffff";
  const mainStroke = variant === "red-on-white" ? ` stroke="${RED}" stroke-width="3"` : "";
  const id = project.replace(/[^a-z0-9]/g, "");
  return (
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img">` +
    `<title>${name}</title>` +
    `<circle cx="${MAIN.cx}" cy="${MAIN.cy}" r="${MAIN.r - (mainStroke ? 1.5 : 0)}" fill="${mainFill}"${mainStroke}/>` +
    `<svg x="${WASP.x}" y="${WASP.y}" width="${WASP.size}" height="${WASP.size}" viewBox="${waspViewBox}">` +
    `<path fill="${waspFill}" d="${waspPath}"/></svg>` +
    `<circle cx="${SUB.cx}" cy="${SUB.cy}" r="${SUB.r + SUB.ring}" fill="#ffffff"/>` +
    `<clipPath id="${id}-sub"><circle cx="${SUB.cx}" cy="${SUB.cy}" r="${SUB.r}"/></clipPath>` +
    `<g clip-path="url(#${id}-sub)"><circle cx="${SUB.cx}" cy="${SUB.cy}" r="${SUB.r}" fill="${RED}"/>` +
    `<svg x="${(SUB.cx - SUB.r).toFixed(2)}" y="${(SUB.cy - SUB.r).toFixed(2)}" width="${s.toFixed(2)}" height="${s.toFixed(2)}" viewBox="${viewBox}">` +
    `${prefixIds(inner, id)}</svg></g></svg>\n`
  );
}

const targets = JSON.parse(readFileSync(join(here, "targets.json"), "utf8"));
let stale = 0;
let written = 0;
for (const file of readdirSync(join(here, "symbols")).filter((f) => f.endsWith(".svg")).sort()) {
  const project = file.slice(0, -4);
  const out = badge(project, readFileSync(join(here, "symbols", file), "utf8"));
  let paths = [join(repo, project, "logo.svg"), ...(targets[project] || []).map((p) => join(repo, p))];
  if (existsSync(join(homeLogos, project + ".svg"))) paths.push(join(homeLogos, project + ".svg"));
  if (outDir) paths = [join(outDir, project + ".svg")]; // preview: write only here
  for (const p of paths) {
    const cur = existsSync(p) ? readFileSync(p, "utf8") : null;
    if (cur === out) continue;
    if (check) { stale++; console.error("stale:", p); continue; }
    writeFileSync(p, out);
    written++;
  }
}
if (check && stale) process.exit(1);
console.log(check ? "all badges up to date" : `wrote ${written} files`);
