import { createPortal } from 'react-dom';
import { Link, NavLink, useLocation } from 'react-router-dom';

// The site's links live in the shared OWASP BLT top bar (<blt-nav> in index.html), the one
// header on every BLT site. React renders them straight into it, so router links and click
// handlers work as usual; the bar puts them in its centre, or in its menu on phones.
const dashboardLinks = [
  { label: 'Overview', path: '/dashboard' },
  { label: 'Triage', path: '/triage' },
  { label: 'Security Log', path: '/security' },
];

function scrollToSection(id) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
}

export default function BarLinks() {
  const location = useLocation();
  const bar = typeof document !== 'undefined' ? document.querySelector('blt-nav') : null;
  if (!bar) return null;

  const links =
    location.pathname === '/' ? (
      <>
        <button type="button" onClick={() => scrollToSection('features')}>Features</button>
        <button type="button" onClick={() => scrollToSection('how-it-works')}>How It Works</button>
        <button type="button" onClick={() => scrollToSection('quick-start')}>Quick Start</button>
        <Link to="/dashboard" slot="actions" data-primary="">Open Dashboard</Link>
      </>
    ) : (
      <>
        {dashboardLinks.map((item) => (
          <NavLink key={item.path} to={item.path}>
            {item.label}
          </NavLink>
        ))}
        <Link to="/" slot="actions">Home</Link>
      </>
    );

  return createPortal(links, bar);
}
