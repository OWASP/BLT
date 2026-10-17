import React from 'react';
import { useLocation, Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Footer from './Footer';

const pageTitles = {
  '/dashboard': { eyebrow: 'OWASP BLT \u00b7 TOASTY', title: 'Triage Operations Dashboard' },
  '/triage': { eyebrow: 'OPERATIONS', title: 'Triage & Quarantine' },
  '/security': { eyebrow: 'SECURITY', title: 'PII Redaction Audit Log' },
  '/activity': { eyebrow: 'MONITORING', title: 'Activity Stream' },
  '/settings': { eyebrow: 'CONFIGURATION', title: 'Settings' },
};

export default function Layout() {
  const location = useLocation();
  const pageInfo = pageTitles[location.pathname] || pageTitles['/dashboard'];

  return (
    <div className="min-h-screen lg:flex">
      <Sidebar />

      <div className="flex min-h-screen flex-1 flex-col">
        {/* Glassmorphic Header */}
        <header className="sticky top-0 z-20 border-b border-neutral-border glass px-5 py-4 lg:px-8">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="pl-12 lg:pl-0">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-gray-500">
                {pageInfo.eyebrow}
              </p>
              <h2 className="text-2xl font-extrabold text-dark-base">
                {pageInfo.title}
              </h2>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <div className="flex items-center gap-2 rounded-full border border-neutral-border bg-white px-3 py-1.5 text-xs font-medium text-gray-600">
                <span className="live-dot" />
                <span>System Operational</span>
              </div>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 space-y-6 px-5 py-6 lg:px-8">
          <Outlet />
        </main>

        {/* Footer */}
        <div className="px-4 lg:px-6">
          <Footer />
        </div>
      </div>
    </div>
  );
}
