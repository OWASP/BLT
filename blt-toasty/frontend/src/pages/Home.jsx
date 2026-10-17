import React from 'react';
import { Link } from 'react-router-dom';
import Footer from '../components/Footer';
import {
  ShieldCheck,
  Search,
  Brain,
  MessageSquare,
  Share2,
  FlaskConical,
  Webhook,
  ScanEye,
  Binary,
  GitCompareArrows,
  Cpu,
  LayoutDashboard,
  ArrowRight,
  ExternalLink,
  Database,
  Server,
  Lock,
  Zap,
  Globe,
  Terminal,
  Copy,
  Check,
} from 'lucide-react';

/* ─── Feature cards data ──────────────────────────────────────────────── */
const features = [
  {
    icon: ShieldCheck,
    title: 'Fail-Closed PII Redaction',
    description:
      '17+ native recognizers scrub emails, API keys, AWS secrets, private keys, and more. If redaction fails, the payload is immediately quarantined — zero data reaches the LLM.',
    accent: 'text-red-600 bg-red-50 border-red-200',
  },
  {
    icon: Search,
    title: 'Semantic Duplicate Detection',
    description:
      '384-dimensional vector embeddings via FastEmbed + Cloudflare Vectorize find semantically similar bug reports with sub-second cosine similarity matching.',
    accent: 'text-blue-600 bg-blue-50 border-blue-200',
  },
  {
    icon: Brain,
    title: 'AI Summarization & CWE Labeling',
    description:
      'Token-budgeted prompts generate structured summaries with severity scoring, CWE classification, and actionable remediation guidance via Workers AI.',
    accent: 'text-purple-600 bg-purple-50 border-purple-200',
  },
  {
    icon: MessageSquare,
    title: 'Stateful Conversations',
    description:
      'Cloudflare Durable Objects maintain multi-turn conversation context across triage sessions — no context loss, no external databases.',
    accent: 'text-emerald-600 bg-emerald-50 border-emerald-200',
  },
  {
    icon: Share2,
    title: 'MCP Export API',
    description:
      'JWT-secured Model Context Protocol endpoints let external AI agents (Claude, Cursor, custom tools) securely query triage data via JSON-RPC or REST.',
    accent: 'text-amber-600 bg-amber-50 border-amber-200',
  },
  {
    icon: FlaskConical,
    title: 'Shadow Mode Validation',
    description:
      'Run ML predictions in parallel against production traffic without mutating state. Hourly cron validates accuracy against maintainer ground truth.',
    accent: 'text-indigo-600 bg-indigo-50 border-indigo-200',
  },
];

/* ─── Pipeline steps ──────────────────────────────────────────────────── */
const pipelineSteps = [
  {
    icon: Webhook,
    title: 'Webhook Ingress',
    description: 'GitLab webhooks arrive with HMAC signature validation and 24h KV replay protection.',
  },
  {
    icon: ScanEye,
    title: 'PII Redaction Gate',
    description: 'Native regex engine scrubs secrets and PII. Fails closed — quarantines on any detection failure.',
  },
  {
    icon: Binary,
    title: 'Vector Embedding',
    description: 'Clean text is embedded into 384-dim vectors via FastEmbed and indexed in Cloudflare Vectorize.',
  },
  {
    icon: GitCompareArrows,
    title: 'Duplicate Detection',
    description: 'Cosine similarity search finds semantically related reports from the entire issue history.',
  },
  {
    icon: Cpu,
    title: 'AI Triage & Summary',
    description: 'Workers AI generates structured summaries with CWE labels, severity scores, and remediation steps.',
  },
  {
    icon: LayoutDashboard,
    title: 'Dashboard & Export',
    description: 'Results flow to the React dashboard and are available via the JWT-secured MCP Export API.',
  },
];

/* ─── Tech stack items ────────────────────────────────────────────────── */
const techStack = [
  { icon: Globe, label: 'Cloudflare Workers', sub: 'Python Runtime' },
  { icon: Database, label: 'Cloudflare D1', sub: 'Edge SQLite' },
  { icon: Search, label: 'Vectorize', sub: '384-dim Vectors' },
  { icon: Server, label: 'Durable Objects', sub: 'Stateful Edge' },
  { icon: Lock, label: 'Workers KV', sub: 'Replay Protection' },
  { icon: Zap, label: 'Workers AI', sub: 'Llama 3.1 8B' },
];

/* ─── Quick start commands ────────────────────────────────────────────── */
const quickStartCommands = `# Clone & install
git clone https://git.owaspblt.org/BLT/BLT.git
cd BLT-Toasty
npm install && uv sync && pre-commit install

# Start FastEmbed sidecar
docker compose up -d

# Configure Vectorize metadata indexes
npx wrangler vectorize create-metadata-index toasty-embeddings \\
  --property-name repo --type string
npx wrangler vectorize create-metadata-index toasty-embeddings \\
  --property-name model_version --type string

# Launch local dev server
npx wrangler dev`;

/* ─── Terminal demo content ───────────────────────────────────────────── */
const terminalLines = [
  { type: 'comment', text: '# Incoming vulnerability report with embedded secrets' },
  { type: 'input', text: '$ curl -X POST /webhook/gitlab -d \'{"title": "SQL Injection",' },
  { type: 'input', text: '    "description": "Token: glpat-abc123, email: dev@corp.io"}\'' },
  { type: 'blank' },
  { type: 'output', text: '\u2713 Webhook validated (HMAC signature OK)' },
  { type: 'output', text: '\u2713 Replay check passed (event UUID unique)' },
  { type: 'redact', text: '\u26d4 PII Detected: [API_TOKEN] (conf: 0.99)' },
  { type: 'redact', text: '\u26d4 PII Detected: [EMAIL_ADDRESS] (conf: 0.99)' },
  { type: 'output', text: '\u2713 Redaction complete \u2014 safe payload forwarded' },
  { type: 'output', text: '\u2713 Vectorized (384-dim) \u2192 duplicate scan: 0 matches' },
  { type: 'success', text: '\u2713 Triage complete \u2192 severity: HIGH, CWE-89' },
];

/* ─── CopyButton component ───────────────────────────────────────────── */
function CopyButton({ text }) {
  const [copied, setCopied] = React.useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button
      onClick={handleCopy}
      className="flex items-center gap-1 rounded-md border border-white/10 bg-white/5 px-2.5 py-1 text-xs text-gray-400 transition-colors hover:bg-white/10 hover:text-white"
    >
      {copied ? <Check size={12} /> : <Copy size={12} />}
      {copied ? 'Copied' : 'Copy'}
    </button>
  );
}

/* ═══════════════════════════════════════════════════════════════════════ */
/*  HOME PAGE COMPONENT                                                   */
/* ═══════════════════════════════════════════════════════════════════════ */
export default function Home() {
  return (
    <div className="min-h-screen">
      {/* ── Navbar ─────────────────────────────────────────────────── */}
      <nav className="sticky top-0 z-50 border-b border-neutral-border glass">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3">
          <button
            onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
            className="flex items-center gap-3 transition-opacity hover:opacity-80"
          >
            <img src="/logo.svg" alt="BLT-Toasty" className="h-9 w-9" />
            <span className="text-lg font-extrabold text-dark-base">
              BLT-Toasty
            </span>
          </button>

          <div className="hidden items-center gap-8 md:flex">
            <button onClick={() => document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' })} className="text-sm font-medium text-gray-600 transition-colors hover:text-brand">
              Features
            </button>
            <button onClick={() => document.getElementById('how-it-works')?.scrollIntoView({ behavior: 'smooth' })} className="text-sm font-medium text-gray-600 transition-colors hover:text-brand">
              How It Works
            </button>
            <button onClick={() => document.getElementById('quick-start')?.scrollIntoView({ behavior: 'smooth' })} className="text-sm font-medium text-gray-600 transition-colors hover:text-brand">
              Quick Start
            </button>
            <Link to="/dashboard" className="btn-primary">
              Open Dashboard
              <ArrowRight size={14} />
            </Link>
          </div>

          {/* Mobile CTA */}
          <Link to="/dashboard" className="btn-primary md:hidden">
            Dashboard
            <ArrowRight size={14} />
          </Link>
        </div>
      </nav>

      {/* ── Hero Section ───────────────────────────────────────────── */}
      <section className="relative overflow-hidden pb-16 pt-20 lg:pb-24 lg:pt-28">
        {/* Subtle background gradient */}
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-red-50/60 via-transparent to-transparent" />

        <div className="relative mx-auto max-w-7xl px-6">
          <div className="grid items-center gap-12 lg:grid-cols-2 lg:gap-16">
            {/* Left: Copy */}
            <div>
              <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-red-200 bg-red-50 px-4 py-1.5 text-xs font-semibold text-red-700">
                <span className="live-dot" />
                OWASP BLT Project
              </div>
              <h1 className="text-4xl font-extrabold leading-[1.1] tracking-tight text-dark-base sm:text-5xl lg:text-6xl">
                AI-Powered Triage for{' '}
                <span className="text-brand">Vulnerability Disclosure</span>
              </h1>
              <p className="mt-6 max-w-xl text-lg leading-relaxed text-gray-600">
                BLT-Toasty eliminates duplicate reports, redacts secrets before
                they reach any LLM, and auto-generates structured summaries —
                reducing manual triage time by{' '}
                <strong className="text-dark-base">over 30%</strong>.
              </p>
              <div className="mt-8 flex flex-wrap gap-4">
                <Link to="/dashboard" className="btn-primary">
                  View Dashboard
                  <ArrowRight size={16} />
                </Link>
                <a
                  href="https://git.owaspblt.org/BLT/BLT/tree/main/blt-toasty"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-outline"
                >
                  GitLab Repo
                  <ExternalLink size={14} />
                </a>
              </div>
            </div>

            {/* Right: Terminal mockup */}
            <div className="rounded-2xl border border-gray-800 bg-gray-950 shadow-2xl">
              {/* Title bar */}
              <div className="flex items-center gap-2 border-b border-gray-800 px-4 py-3">
                <div className="h-3 w-3 rounded-full bg-red-500" />
                <div className="h-3 w-3 rounded-full bg-yellow-500" />
                <div className="h-3 w-3 rounded-full bg-green-500" />
                <span className="ml-3 font-mono text-xs text-gray-500">
                  toasty-pipeline
                </span>
              </div>
              {/* Terminal content */}
              <div className="space-y-1 p-5 font-mono text-[13px] leading-relaxed">
                {terminalLines.map((line, i) => (
                  <div key={i}>
                    {line.type === 'blank' && <div className="h-3" />}
                    {line.type === 'comment' && (
                      <span className="text-gray-600">{line.text}</span>
                    )}
                    {line.type === 'input' && (
                      <span className="text-gray-300">{line.text}</span>
                    )}
                    {line.type === 'output' && (
                      <span className="text-emerald-400">{line.text}</span>
                    )}
                    {line.type === 'redact' && (
                      <span className="text-red-400">{line.text}</span>
                    )}
                    {line.type === 'success' && (
                      <span className="font-semibold text-amber-300">{line.text}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Features Grid ──────────────────────────────────────────── */}
      <section id="features" className="py-20">
        <div className="mx-auto max-w-7xl px-6">
          <div className="text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-brand">
              Core Capabilities
            </p>
            <h2 className="mt-3 text-3xl font-extrabold text-dark-base sm:text-4xl">
              Everything you need for secure triage
            </h2>
            <p className="mx-auto mt-4 max-w-2xl text-gray-600">
              Built on Cloudflare&rsquo;s global edge, BLT-Toasty delivers
              sub-second semantic deduplication, guaranteed PII redaction, and
              AI-generated summaries with full explainability.
            </p>
          </div>

          <div className="mt-14 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {features.map((f) => (
              <div
                key={f.title}
                className="group rounded-xl border border-neutral-border bg-white p-6 shadow-soft transition-all duration-200 hover:-translate-y-1 hover:shadow-card"
              >
                <div
                  className={`mb-4 inline-flex h-11 w-11 items-center justify-center rounded-lg border ${f.accent}`}
                >
                  <f.icon size={20} />
                </div>
                <h3 className="text-lg font-bold text-dark-base">{f.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-gray-600">
                  {f.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How It Works ───────────────────────────────────────────── */}
      <section id="how-it-works" className="border-t border-neutral-border bg-gray-50/50 py-20">
        <div className="mx-auto max-w-7xl px-6">
          <div className="text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-brand">
              Pipeline Architecture
            </p>
            <h2 className="mt-3 text-3xl font-extrabold text-dark-base sm:text-4xl">
              How It Works
            </h2>
            <p className="mx-auto mt-4 max-w-2xl text-gray-600">
              Every incoming vulnerability report flows through a strict
              six-stage pipeline before reaching the dashboard.
            </p>
          </div>

          <div className="relative mt-14">
            {/* Connection line (desktop) */}
            <div className="absolute left-0 right-0 top-[3.25rem] hidden h-0.5 bg-gradient-to-r from-red-200 via-red-300 to-red-200 lg:block" />

            <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-6">
              {pipelineSteps.map((step, i) => (
                <div key={step.title} className="relative text-center">
                  {/* Step icon */}
                  <div className="relative z-10 mx-auto mb-4 flex h-[4.25rem] w-[4.25rem] items-center justify-center rounded-2xl border border-neutral-border bg-white shadow-soft">
                    <step.icon size={24} className="text-brand" />
                  </div>
                  <div className="mb-1 font-mono text-xs text-gray-400">
                    0{i + 1}
                  </div>
                  <h3 className="text-sm font-bold text-dark-base">
                    {step.title}
                  </h3>
                  <p className="mt-1 text-xs leading-relaxed text-gray-500">
                    {step.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── Tech Stack ─────────────────────────────────────────────── */}
      <section className="py-20">
        <div className="mx-auto max-w-7xl px-6">
          <div className="text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-brand">
              Powered By
            </p>
            <h2 className="mt-3 text-3xl font-extrabold text-dark-base sm:text-4xl">
              Cloudflare-Native Stack
            </h2>
            <p className="mx-auto mt-4 max-w-2xl text-gray-600">
              Every component runs on Cloudflare&rsquo;s global edge network —
              zero origin servers, zero cold starts, infinite scalability.
            </p>
          </div>

          <div className="mx-auto mt-14 grid max-w-4xl grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
            {techStack.map((item) => (
              <div
                key={item.label}
                className="flex flex-col items-center rounded-xl border border-neutral-border bg-white p-5 text-center shadow-soft transition-all duration-200 hover:-translate-y-1 hover:shadow-card"
              >
                <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-brand/5 text-brand">
                  <item.icon size={22} />
                </div>
                <p className="text-xs font-bold text-dark-base">{item.label}</p>
                <p className="mt-0.5 text-[10px] text-gray-500">{item.sub}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Quick Start ────────────────────────────────────────────── */}
      <section id="quick-start" className="border-t border-neutral-border bg-gray-950 py-20 text-white">
        <div className="mx-auto max-w-4xl px-6">
          <div className="text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-red-400">
              Get Started
            </p>
            <h2 className="mt-3 text-3xl font-extrabold sm:text-4xl">
              Quick Start
            </h2>
            <p className="mx-auto mt-4 max-w-xl text-gray-400">
              Get BLT-Toasty running locally in under 5 minutes.
            </p>
          </div>

          <div className="relative mt-10 rounded-2xl border border-gray-800 bg-gray-900">
            <div className="flex items-center justify-between border-b border-gray-800 px-5 py-3">
              <div className="flex items-center gap-2">
                <Terminal size={14} className="text-gray-500" />
                <span className="font-mono text-xs text-gray-500">terminal</span>
              </div>
              <CopyButton text={quickStartCommands} />
            </div>
            <pre className="overflow-x-auto p-5 font-mono text-[13px] leading-relaxed">
              <code>
                {quickStartCommands.split('\n').map((line, i) => (
                  <div key={i}>
                    {line.startsWith('#') ? (
                      <span className="text-gray-600">{line}</span>
                    ) : line.trim() === '' ? (
                      <span>&nbsp;</span>
                    ) : (
                      <span className="text-emerald-400">{line}</span>
                    )}
                  </div>
                ))}
              </code>
            </pre>
          </div>

          {/* Bottom CTA */}
          <div className="mt-12 text-center">
            <Link to="/dashboard" className="btn-primary">
              Open Dashboard
              <ArrowRight size={16} />
            </Link>
            <p className="mt-4 text-xs text-gray-500">
              Need help?{' '}
              <a
                href="https://git.owaspblt.org/BLT/BLT/issues"
                target="_blank"
                rel="noopener noreferrer"
                className="text-red-400 underline hover:text-red-300"
              >
                Open an issue on GitLab
              </a>
            </p>
          </div>
        </div>
      </section>

      {/* ── Footer ─────────────────────────────────────────────────── */}
      <Footer />
    </div>
  );
}
