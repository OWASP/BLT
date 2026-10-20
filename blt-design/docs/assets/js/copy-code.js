document.addEventListener('DOMContentLoaded', () => {
  const HEX_PATTERN = /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/;

  function flashState(button, status, icon, label, revert) {
    button.innerHTML = `<i class="fa-solid ${icon}" aria-hidden="true"></i><span class="sr-only">${label}</span>`;
    status.textContent = label;
    setTimeout(revert, 1500);
  }

  function attachCopy(target, getText, buttonClass) {
    const button = document.createElement('button');
    button.type = 'button';
    button.setAttribute('aria-label', 'Copy to clipboard');
    button.className = buttonClass;

    const status = document.createElement('span');
    status.className = 'sr-only';
    status.setAttribute('role', 'status');
    status.setAttribute('aria-live', 'polite');

    const reset = () => {
      button.innerHTML = '<i class="fa-solid fa-copy" aria-hidden="true"></i>';
    };
    reset();

    button.addEventListener('click', async (e) => {
      e.stopPropagation();
      try {
        await navigator.clipboard.writeText(getText());
        flashState(button, status, 'fa-check', 'Copied', reset);
      } catch (err) {
        flashState(button, status, 'fa-xmark', 'Copy failed', reset);
      }
    });

    target.appendChild(button);
    target.appendChild(status);
  }

  document.querySelectorAll('pre').forEach((pre) => {
    const code = pre.querySelector('code');
    if (!code) return;
    pre.classList.add('relative');
    attachCopy(
      pre,
      () => code.innerText,
      'absolute right-2 top-2 inline-flex items-center gap-1 rounded-md border border-slate-200 ' +
        'bg-white/90 px-2 py-1 text-xs text-slate-600 shadow-sm transition hover:bg-slate-50 ' +
        'dark:border-slate-600 dark:bg-slate-800/90 dark:text-slate-300 dark:hover:bg-slate-700'
    );
  });

  document.querySelectorAll('div').forEach((div) => {
    if (div.children.length > 0) return;
    const text = div.textContent.trim();
    if (!HEX_PATTERN.test(text)) return;

    div.classList.add('relative');
    attachCopy(
      div,
      () => text,
      'absolute right-1.5 top-1.5 inline-flex h-6 w-6 items-center justify-center rounded-md ' +
        'bg-black/10 text-current backdrop-blur-sm transition hover:bg-black/20'
    );
  });
});