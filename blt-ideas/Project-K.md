# Core BLT frontend Migration from Django to Next.js/TypeScript Architecture

## INTRODUCTION

The OWASP Bug Logging Tool (BLT) is a critical platform for security researchers to report, track, and manage vulnerability discoveries across organizations. This project proposes a comprehensive migration of the BLT platform from its current Django-based monolithic architecture to a modern, edge-optimized Next.js/TypeScript stack deployed on Cloudflare Pages. The migration will transform Django template-based pages into React components while maintaining full feature parity with the existing Django REST API backend. With the exponential growth in edge computing and the need for zero-latency global access to security vulnerability data, this migration positions BLT to serve a worldwide community of security researchers with instant page loads, improved SEO, and enhanced developer experience through strict TypeScript type safety.

## OBJECTIVE

- Performance: Moving the UI rendering to the "Edge" with Cloudflare reduces latency significantly compared to standard server-side rendering.

- Scalability: By offloading the frontend rendering from the Django server, we reduce CPU load on the core backend.

- Modernization: This aligns the project with 2026 industry standards (Headless React/Next.js) and makes it more accessible to new contributors familiar with the React ecosystem.

- Co-existence: This new version will act as a "Satellite" UI, communicating securely with the existing Django database without disrupting the current platform.

## Project Timeline(~350hrs)

### Phase 1: Foundation & Infrastructure analysis adn planning (Weeks 1-2)

1. Analyze Django BLT repository structure

2. Create centralized TypeScript type definitions

3. Set up TanStack Query provider and API client with JWT intercept

4. Core Page Migration (High Priority)

### Phase 2: API Layer & Hooks (Weeks 3-4)

1. Creating Next.js API routes proxying to Django

2. Building TanStack Query hooks

3. Updating existing 8 pages to use hooks instead of inline queries

### Phase 3: High-Priority Pages (Weeks 5-7)

1. Organization Management

2. Issue CRUD Operations

3. User Account & Blog

### Phase 4: Medium-Priority Pages (Weeks 8-10)

1. Projects & Community

2. Education & Gamification

3. Utility Pages

### Phase 5: Low-Priority Pages (Week 11)

1. Admin page and other pages

### Phase 6: Testing & Optimization (Week 12)

1. Testing and optimization for production launch

---

## ARCHITECTURE MIGRATION

| Module | Core BLT | BLT-on-Cloudflare | Why this change? |
| --- | --- | --- | --- |
| Language | Python | TypeScript (TSX) | Ensures strict "data contracts" between the API and the UI, reducing runtime crashes. |
| Framework | Django (Monolithic) | Next.js (App Router) | Provides SEO-friendly Static Generation (SSG) and instant page transitions. |
| Hosting | VPS / Docker | Cloudflare Pages | Zero-latency global delivery via Cloudflare’s Edge network; infinite scalability. |
| UI/Styling | CSS | Tailwind CSS | Drastically reduces CSS bundle size by stripping unused styles at build time. |
| API Layer | Django Templates | Django REST Framework (DRF) | Converts Python logic into JSON, making the data accessible to any frontend. |
| Data Fetching | Server-Side Querying | TanStack Query (React Query) | Handles caching, loading states, and "optimistic updates" for a seamless UI. |
| Authentication | Session Cookies | JWT (JSON Web Tokens) | Allows secure authentication across different domains (.org to .dev). |
| Icons/Assets | FontAwesome / PNG | FontAwesome for now (can be used Lucide React) | Lightweight, tree-shakeable SVG icons optimized for React. |

## Conclusion

This migration strategically positions OWASP BLT as a modern, high-performance platform for global security research. By combining Next.js, TypeScript, and Cloudflare's edge network with the existing Django backend, we'll deliver superior user experience and performance. The phased approach with live initial pages validates the architecture, establishing BLT as a reference implementation that will attract a new generation of contributors.

---
