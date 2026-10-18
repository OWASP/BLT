import React from 'react';

const footerLinks = [
  {
    heading: 'Docs',
    links: [
      { label: 'API Reference', href: '#' },
      { label: 'Architecture', href: '#' },
      { label: 'Worker Docs', href: '#' },
    ],
  },
  {
    heading: 'Triage',
    links: [
      { label: 'Quarantine', href: '#/triage' },
      { label: 'Duplicates', href: '#/triage' },
      { label: 'Redaction Log', href: '#/security' },
    ],
  },
  {
    heading: 'Project',
    links: [
      {
        label: 'Source',
        href: 'https://git.owaspblt.org/BLT/tree/main/blt-toasty',
        external: true,
      },
      {
        label: 'Issues',
        href: 'https://git.owaspblt.org/BLT/issues',
        external: true,
      },
    ],
  },
  {
    heading: 'OWASP',
    links: [
      { label: 'OWASP BLT', href: 'https://owaspblt.org', external: true },
      {
        label: 'Foundation page',
        href: 'https://owasp.org/www-project-bug-logging-tool/',
        external: true,
      },
      { label: 'owasp.org', href: 'https://owasp.org', external: true },
    ],
  },
];

export default function Footer() {
  return (
    <footer className="footer-grid-overlay relative mt-14 w-full overflow-hidden rounded-t-3xl border border-white/5 bg-blt-footer py-10 pb-8 text-white max-md:rounded-t-[0.8rem]">
      {/* Domain heading */}
      <h2 className="relative m-0 break-all px-2 text-center text-[clamp(2rem,5vw,4.5rem)] font-light leading-[1.02] tracking-[-0.045em] text-white sm:break-normal">
        toasty.owaspblt.org
      </h2>

      {/* Red divider */}
      <div
        className="relative mx-auto mt-3 h-[3px] w-16 rounded-full bg-red-600"
        aria-hidden="true"
      />

      {/* Link grid */}
      <div className="footer-links relative mx-auto mt-8 grid max-w-6xl grid-cols-1 gap-6 px-6 font-mono sm:grid-cols-2 md:grid-cols-4 md:gap-8">
        {footerLinks.map((section) => (
          <div key={section.heading}>
            <p>{section.heading}</p>
            {section.links.map((link) => (
              <a
                key={link.label}
                href={link.href}
                {...(link.external
                  ? { target: '_blank', rel: 'noopener noreferrer' }
                  : {})}
              >
                {link.label}
              </a>
            ))}
          </div>
        ))}
      </div>

      {/* Bottom copyright */}
      <div className="relative mt-10 border-t border-white/10 pt-6 text-center">
        <p className="text-xs text-gray-500">
          © {new Date().getFullYear()} OWASP Foundation. BLT-Toasty is an OWASP BLT project.
        </p>
      </div>
    </footer>
  );
}
