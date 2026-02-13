function getDocsBase() {
  const marker = '/docs/';
  const pathname = window.location.pathname;
  const idx = pathname.indexOf(marker);
  if (idx === -1) return './';
  return pathname.slice(0, idx + marker.length);
}

function normalizePath(path) {
  return path.replace(/\/+/g, '/').replace(/index\.html$/, '').replace(/\/$/, '');
}

function setActive(link) {
  link.classList.remove('border-transparent', 'text-slate-700');
  link.classList.add('border-red-200', 'bg-red-50', 'font-semibold', 'text-red-700');

  const icon = link.querySelector('i');
  if (icon) {
    icon.classList.remove('text-slate-500');
    icon.classList.add('text-red-600');
  }
}

function wireDocLinks(root) {
  const base = getDocsBase();
  const links = root.querySelectorAll('[data-doc-link]');
  const current = normalizePath(window.location.pathname);

  for (const link of links) {
    const path = link.getAttribute('data-doc-link');
    if (!path) continue;

    const href = `${base}${path}`;
    link.setAttribute('href', href);

    const targetPath = normalizePath(new URL(href, window.location.origin).pathname);
    if (current === targetPath) {
      setActive(link);
      link.setAttribute('aria-current', 'page');
    }
  }
}

function wireAssets(root) {
  const base = getDocsBase();
  const assets = root.querySelectorAll('[data-asset-src]');

  for (const asset of assets) {
    const path = asset.getAttribute('data-asset-src');
    if (!path) continue;

    const src = `${base}${path}`;
    asset.setAttribute('src', src);
  }
}

async function loadIncludes() {
  const nodes = document.querySelectorAll('[data-include]');
  for (const node of nodes) {
    const path = node.getAttribute('data-include');
    if (!path) continue;

    try {
      const res = await fetch(path);
      if (!res.ok) throw new Error(`Failed include: ${path}`);
      node.innerHTML = await res.text();
      wireDocLinks(node);
      wireAssets(node);
    } catch (err) {
      node.innerHTML = '<p class="p-4 text-sm text-red-700">Unable to load shared navigation.</p>';
      console.error(err);
    }
  }
  wireAssets(document);
}

loadIncludes();
