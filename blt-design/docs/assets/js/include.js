function getDocsBase() {
  const markers = ['/docs/'];
  const pathname = window.location.pathname;

  for (const marker of markers) {
    const idx = pathname.indexOf(marker);
    if (idx !== -1) {
      return pathname.slice(0, idx + marker.length);
    }
  }

  return './docs/';
}

function getSiteBase() {
  const marker = '/docs/';
  const pathname = window.location.pathname;
  const idx = pathname.indexOf(marker);

  if (idx !== -1) {
    return pathname.slice(0, idx + 1);
  }

  if (pathname.endsWith('/')) return pathname;
  return pathname.replace(/\/[^/]*$/, '/');
}

function normalizePath(path) {
  return path.replace(/\/+/g, '/').replace(/index\.html$/, '').replace(/\/$/, '');
}

function setActive(link) {
  link.classList.remove('border-transparent', 'text-slate-700');
  link.classList.add('border-[#E10101]/30', 'bg-[#feeae9]', 'font-semibold', 'text-[#E10101]');

  const icon = link.querySelector('i');
  if (icon) {
    icon.classList.remove('text-slate-500');
    icon.classList.add('text-[#E10101]');
  }
}

function wireDocLinks(root) {
  const base = getDocsBase();
  const siteBase = getSiteBase();
  const links = root.querySelectorAll('[data-doc-link]');
  const rootLinks = root.querySelectorAll('[data-root-link]');
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

  for (const link of rootLinks) {
    const path = link.getAttribute('data-root-link');
    if (!path) continue;

    const href = `${siteBase}${path}`;
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

function sanitizeIncludedHtml(html) {
  // Includes are expected to be trusted local partials from this repository.
  const parser = new DOMParser();
  const doc = parser.parseFromString(html, 'text/html');

  doc.querySelectorAll('script').forEach((script) => script.remove());

  doc.querySelectorAll('*').forEach((el) => {
    Array.from(el.attributes).forEach((attr) => {
      const name = attr.name.toLowerCase();
      const value = attr.value.trim().toLowerCase();

      if (name.startsWith('on')) {
        el.removeAttribute(attr.name);
      }

      if ((name === 'href' || name === 'src') && value.startsWith('javascript:')) {
        el.removeAttribute(attr.name);
      }
    });
  });

  const fragment = document.createDocumentFragment();
  while (doc.body.firstChild) {
    fragment.appendChild(doc.body.firstChild);
  }
  return fragment;
}

async function loadIncludes() {
  const nodes = document.querySelectorAll('[data-include]');
  for (const node of nodes) {
    const path = node.getAttribute('data-include');
    if (!path) continue;

    try {
      const res = await fetch(path);
      if (!res.ok) throw new Error(`Failed include: ${path}`);

      const html = await res.text();
      const safeContent = sanitizeIncludedHtml(html);
      node.replaceChildren(safeContent);

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
