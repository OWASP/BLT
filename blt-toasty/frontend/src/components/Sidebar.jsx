import React from 'react';
import { NavLink, Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  ShieldAlert,
  Lock,
  Activity,
  Settings,
  Home,
} from 'lucide-react';

const iconMap = {
  LayoutDashboard,
  ShieldAlert,
  Lock,
  Activity,
  Settings,
};

const navigation = [
  {
    group: 'Platform',
    items: [
      { label: 'Overview', path: '/dashboard', icon: 'LayoutDashboard' },
      { label: 'Triage & Operations', path: '/triage', icon: 'ShieldAlert' },
      { label: 'Security Log', path: '/security', icon: 'Lock' },
    ],
  },
  // {
  //   group: 'Operations',
  //   items: [
  //     // { label: 'Activity', path: '/activity', icon: 'Activity' },
  //     // { label: 'Settings', path: '/settings', icon: 'Settings' },
  //   ],
  // },
];

// Wide screens only: on phones these links are in the shared OWASP BLT bar's menu (BarLinks).
export default function Sidebar() {
  const location = useLocation();

  const navContent = (
    <>
      {/* Logo & Branding */}
      <div className="border-b border-neutral-border px-6 py-6">
        <Link
          to="/"
          className="mb-3 inline-flex items-center gap-1.5 text-xs font-medium text-gray-400 transition-colors hover:text-brand"
        >
          <Home size={12} />
          Back to Home
        </Link>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-gray-500">
          OWASP BLT
        </p>
        <div className="mt-2 flex items-center gap-3">
          <img src="/logo.svg" alt="BLT-Toasty" className="h-9 w-9" />
          <div>
            <h1 className="text-lg font-extrabold text-dark-base">BLT-Toasty</h1>
            <p className="text-xs text-gray-500">AI Code Review Engine</p>
          </div>
        </div>
      </div>

      {/* Navigation Groups */}
      <nav className="flex-1 space-y-8 overflow-y-auto px-4 py-6" aria-label="Primary navigation">
        {navigation.map((group) => (
          <div key={group.group}>
            <p className="px-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
              {group.group}
            </p>
            <div className="mt-3 space-y-1">
              {group.items.map((item) => {
                const Icon = iconMap[item.icon];
                const isActive =
                  item.path === '/dashboard'
                    ? location.pathname === '/dashboard'
                    : location.pathname.startsWith(item.path);

                return (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    className={`flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors duration-150 ${
                      isActive
                        ? 'bg-nav-active font-semibold text-brand'
                        : 'text-gray-700 hover:bg-gray-100'
                    }`}
                  >
                    {Icon && <Icon size={16} aria-hidden="true" />}
                    {item.label}
                  </NavLink>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Bottom section */}
      <div className="border-t border-neutral-border px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-100 text-xs font-bold text-gray-600">
            OB
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold text-dark-base">OWASP BLT</p>
            <p className="truncate text-xs text-gray-500">toasty@owaspblt.org</p>
          </div>
        </div>
      </div>
    </>
  );

  return (
    <aside className="hidden lg:flex lg:w-72 lg:flex-col border-r border-neutral-border bg-white">
      {navContent}
    </aside>
  );
}
