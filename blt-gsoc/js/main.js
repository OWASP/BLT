const mobileDrawer = document.getElementById('mobile-drawer');
const mobileBtn = document.getElementById('mobile-menu-btn');
const mobileCloseBtn = document.getElementById('mobile-close-btn');
const mobileOverlay = document.getElementById('mobile-overlay');

function openDrawer() {
    mobileDrawer.classList.remove('hidden');
    mobileDrawer.setAttribute('aria-hidden', 'false');
    mobileBtn.setAttribute('aria-expanded', 'true');
    document.body.classList.add('overflow-hidden');
}

function closeDrawer() {
    mobileDrawer.classList.add('hidden');
    mobileDrawer.setAttribute('aria-hidden', 'true');
    mobileBtn.setAttribute('aria-expanded', 'false');
    document.body.classList.remove('overflow-hidden');
}

mobileBtn.addEventListener('click', openDrawer);
mobileCloseBtn.addEventListener('click', closeDrawer);
mobileOverlay.addEventListener('click', closeDrawer);

document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && !mobileDrawer.classList.contains('hidden')) {
        closeDrawer();
    }
});

document.querySelectorAll('#mobile-drawer a[href^="#"]').forEach(function (link) {
    link.addEventListener('click', closeDrawer);
});

document.getElementById('year').textContent = new Date().getFullYear();

// Scroll-spy navigation highlighting
const sections = document.querySelectorAll('section[id]');
const navLinks = document.querySelectorAll('aside a[href^="#"]');

const observerOptions = {
    root: null,
    rootMargin: '-20% 0px -70% 0px',
    threshold: 0
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            const id = entry.target.getAttribute('id');
            updateActiveLink(id);
        }
    });
}, observerOptions);

sections.forEach(section => observer.observe(section));

function updateActiveLink(id) {
    navLinks.forEach(link => {
        const href = link.getAttribute('href').substring(1);
        const isActive = href === id;

        const activeClasses = ['bg-[#feeae9]', 'text-[#E10101]', 'dark:bg-red-950/30', 'dark:text-red-400'];
        const inactiveClasses = ['text-gray-700', 'hover:bg-gray-50', 'dark:text-gray-300', 'dark:hover:bg-gray-800'];

        if (isActive) {
            link.classList.add(...activeClasses);
            link.classList.remove(...inactiveClasses);
        } else {
            link.classList.remove(...activeClasses);
            link.classList.add(...inactiveClasses);
        }
    });
}