function getDocsBase() {
  const marker = '/docs/';
  const pathname = window.location.pathname;
  const idx = pathname.indexOf(marker);
  if (idx === -1) {
    return './';
  }
  return pathname.slice(0, idx + marker.length);
}

function wireDocLinks(root) {
  const base = getDocsBase();
  const links = root.querySelectorAll('[data-doc-link]');

  for (const link of links) {
    const path = link.getAttribute('data-doc-link');
    if (!path) continue;
    link.setAttribute('href', `${base}${path}`);
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
    } catch (err) {
      node.innerHTML = '<p>Unable to load shared navigation.</p>';
      console.error(err);
    }
  }
}

loadIncludes();
