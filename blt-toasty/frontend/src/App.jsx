import React from 'react';
import { HashRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Overview from './pages/Overview';
import Triage from './pages/Triage';
import Security from './pages/Security';

export default function App() {
  return (
    <HashRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/triage" element={<Triage />} />
          <Route path="/security" element={<Security />} />
          {/* Placeholder routes for future pages */}
          <Route
            path="/activity"
            element={
              <div className="flex h-64 items-center justify-center rounded-xl border border-neutral-border bg-white shadow-card">
                <div className="text-center">
                  <p className="text-2xl font-bold text-dark-base">Activity Stream</p>
                  <p className="mt-2 text-sm text-gray-500">Coming soon — real-time pipeline monitoring</p>
                </div>
              </div>
            }
          />
          <Route
            path="/settings"
            element={
              <div className="flex h-64 items-center justify-center rounded-xl border border-neutral-border bg-white shadow-card">
                <div className="text-center">
                  <p className="text-2xl font-bold text-dark-base">Settings</p>
                  <p className="mt-2 text-sm text-gray-500">Configuration panel — coming soon</p>
                </div>
              </div>
            }
          />
        </Routes>
      </Layout>
    </HashRouter>
  );
}
