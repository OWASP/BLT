(function () {
  const MOCK_DELAY = 120;
  window.sizzleMockState = {
    organizations: ['OWASP BLT', 'GSoC Contributors', 'Security Research Lab'],
    selectedOrg: 'OWASP BLT'
  };

  window.showToast = function showToast(message) {
    let container = document.querySelector('.toast-container');
    if (!container) {
      container = document.createElement('div');
      container.className = 'toast-container';
      document.body.appendChild(container);
    }
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 2800);
  };

  window.openSheet = function openSheet(id) {
    const sheet = document.getElementById(id);
    const overlay = document.querySelector('.sheet-overlay');
    if (overlay) overlay.classList.add('active');
    if (sheet) sheet.classList.add('active');
  };

  window.closeSheet = function closeSheet() {
    document.querySelectorAll('.sheet.active').forEach((sheet) => sheet.classList.remove('active'));
    document.querySelectorAll('.sheet-overlay.active').forEach((overlay) => overlay.classList.remove('active'));
  };

  window.openModal = function openModal(id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.add('active');
  };

  window.closeModal = function closeModal(id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.remove('active');
  };

  window.mockSave = function mockSave(message) {
    setTimeout(() => window.showToast(message || 'Saved in Phase 1 mock UI'), MOCK_DELAY);
  };

  window.switchMockOrg = function switchMockOrg(select) {
    window.sizzleMockState.selectedOrg = select.value;
    window.showToast('Switched mock organization to ' + select.value);
  };

  document.addEventListener('click', (event) => {
    if (event.target.matches('[data-close-sheet]')) window.closeSheet();
    if (event.target.matches('[data-toast]')) window.showToast(event.target.getAttribute('data-toast'));
  });
})();