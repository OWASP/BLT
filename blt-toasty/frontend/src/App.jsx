import React from 'react';
import { HashRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import BarLinks from './components/BarLinks';
import Home from './pages/Home';
import AccessDenied from './components/AccessDenied';
import { useAuth } from './hooks/useAuth';
import Overview from './pages/Overview';
import Triage from './pages/Triage';
import Security from './pages/Security';

/**
 * AuthGate — renders children only when a dashboard token is present
 * and the backend has not rejected it. Placed here rather than inside
 * Layout so that the check happens at the router level: unauthorised
 * users never receive any dashboard HTML at all.
 */
function AuthGate({ children }) {
  const isAuthorized = useAuth();
  return isAuthorized ? children : <AccessDenied />;
}

export default function App() {
  return (
    <HashRouter>
      <BarLinks />
      <Routes>
        {/* Public landing page — no sidebar, no auth gate */}
        <Route path="/" element={<Home />} />

        {/* Dashboard routes — wrapped in AuthGate and Layout with sidebar */}
        <Route
          element={
            <AuthGate>
              <Layout />
            </AuthGate>
          }
        >
          <Route path="/dashboard" element={<Overview />} />
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
        </Route>
      </Routes>
    </HashRouter>
  );
}
