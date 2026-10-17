(() => {
  const root = document.documentElement;
  let savedTheme = null;

  try {
    savedTheme = localStorage.getItem('theme');
  } catch (error) {
    savedTheme = null;
  }

  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  const shouldUseDark = savedTheme === 'dark' || (!savedTheme && prefersDark);

  root.classList.toggle('dark', shouldUseDark);
})();