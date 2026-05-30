/**
 * BLT Nexus – Cybersecurity Projects & Ambassadors Data
 *
 * Each project entry:
 *   id          – unique slug
 *   name        – display name
 *   logo        – emoji fallback logo
 *   url         – project homepage
 *   category    – one of: bug-bounty | scanning | ctf | platform | framework | community
 *   description – short blurb
 *   bltUrl      – link to the project on BLT (optional)
 *   ambassadors – array of ambassador objects
 *
 * Each ambassador:
 *   name        – display name
 *   github      – GitHub username
 *   role        – role / title
 *   avatarUrl   – GitHub avatar URL (derived automatically)
 */

const PROJECTS = [
    {
      id: "owasp-blt",
      name: "OWASP BLT",
      logo: "🐛",
      url: "https://blt.owasp.org",
      category: "platform",
      description:
        "Bug Logging Tool (BLT) lets users report bugs on any website, rewarding reporters and helping companies keep their software secure.",
      bltUrl: "https://blt.owasp.org",
      ambassadors: [
        {
          name: "Donnie",
          github: "DonnieBLT",
          role: "BLT Core Lead",
        },
      ],
    },
    {
      id: "hackerone",
      name: "HackerOne",
      logo: "🎯",
      url: "https://www.hackerone.com",
      category: "bug-bounty",
      description:
        "The world's most trusted hacker-powered security platform, connecting organizations with a global community of ethical hackers.",
      bltUrl: "https://blt.owasp.org/projects/hackerone",
      ambassadors: [
        {
          name: "Alex Rivera",
          github: "alexr-sec",
          role: "Bug Bounty Hunter",
        },
        {
          name: "Priya Nair",
          github: "priyanair",
          role: "Security Researcher",
        },
      ],
    },
    {
      id: "bugcrowd",
      name: "Bugcrowd",
      logo: "🏆",
      url: "https://www.bugcrowd.com",
      category: "bug-bounty",
      description:
        "Bugcrowd is the #1 crowdsourced cybersecurity platform, running managed bug bounty, vulnerability disclosure, and pen testing programs.",
      bltUrl: "https://blt.owasp.org/projects/bugcrowd",
      ambassadors: [
        {
          name: "Sam Chen",
          github: "samchen-security",
          role: "Platform Ambassador",
        },
      ],
    },
    {
      id: "owasp-zap",
      name: "OWASP ZAP",
      logo: "🔍",
      url: "https://www.zaproxy.org",
      category: "scanning",
      description:
        "Zed Attack Proxy (ZAP) is one of the world's most popular free security tools for finding vulnerabilities in web applications.",
      bltUrl: "https://blt.owasp.org/projects/owasp-zap",
      ambassadors: [
        {
          name: "Maya Patel",
          github: "mayap-owasp",
          role: "ZAP Contributor",
        },
        {
          name: "Liam Foster",
          github: "liamfoster",
          role: "AppSec Engineer",
        },
      ],
    },
    {
      id: "tryhackme",
      name: "TryHackMe",
      logo: "🖥️",
      url: "https://tryhackme.com",
      category: "ctf",
      description:
        "TryHackMe is a free online platform for learning cyber security, using hands-on exercises and labs in a browser-based environment.",
      bltUrl: "https://blt.owasp.org/projects/tryhackme",
      ambassadors: [
        {
          name: "Jordan Kim",
          github: "jordankim-sec",
          role: "CTF Champion",
        },
        {
          name: "Fatima Al-Hassan",
          github: "fatimah-sec",
          role: "Education Lead",
        },
      ],
    },
    {
      id: "hackthebox",
      name: "Hack The Box",
      logo: "📦",
      url: "https://www.hackthebox.com",
      category: "ctf",
      description:
        "Hack The Box is a massive hacking playground, offering labs and challenges to practice penetration testing skills in a legal environment.",
      bltUrl: "https://blt.owasp.org/projects/hackthebox",
      ambassadors: [
        {
          name: "Carlos Mendez",
          github: "carlos-htb",
          role: "Pro Hacker",
        },
      ],
    },
    {
      id: "metasploit",
      name: "Metasploit",
      logo: "⚡",
      url: "https://www.metasploit.com",
      category: "framework",
      description:
        "The world's most used penetration testing framework, enabling security professionals to find, exploit, and validate vulnerabilities.",
      bltUrl: "https://blt.owasp.org/projects/metasploit",
      ambassadors: [
        {
          name: "Nina Volkov",
          github: "ninaV-pentest",
          role: "Exploit Developer",
        },
      ],
    },
    {
      id: "snyk",
      name: "Snyk",
      logo: "🛡️",
      url: "https://snyk.io",
      category: "scanning",
      description:
        "Snyk helps developers find and fix vulnerabilities in their code, open source dependencies, container images, and infrastructure as code.",
      bltUrl: "https://blt.owasp.org/projects/snyk",
      ambassadors: [
        {
          name: "Rohan Gupta",
          github: "rohang-dev",
          role: "DevSecOps Engineer",
        },
        {
          name: "Sophie Turner",
          github: "sophiet-sec",
          role: "OSS Security Lead",
        },
      ],
    },
    {
      id: "cve-mitre",
      name: "CVE / MITRE",
      logo: "📋",
      url: "https://cve.mitre.org",
      category: "community",
      description:
        "The CVE Program identifies, defines, and catalogs publicly disclosed cybersecurity vulnerabilities, forming the foundation of global vulnerability management.",
      bltUrl: "https://blt.owasp.org/projects/cve",
      ambassadors: [
        {
          name: "Elena Kowalski",
          github: "elenakow",
          role: "CVE Analyst",
        },
      ],
    },
    {
      id: "intigriti",
      name: "Intigriti",
      logo: "🎪",
      url: "https://www.intigriti.com",
      category: "bug-bounty",
      description:
        "Europe's leading ethical hacking and bug bounty platform, connecting companies with top security researchers to secure their digital assets.",
      bltUrl: "https://blt.owasp.org/projects/intigriti",
      ambassadors: [
        {
          name: "Tobias Bauer",
          github: "tobiasbauer",
          role: "Bug Bounty Hunter",
        },
        {
          name: "Aisha Diallo",
          github: "aishadiallo",
          role: "Security Researcher",
        },
      ],
    },
    {
      id: "semgrep",
      name: "Semgrep",
      logo: "🔬",
      url: "https://semgrep.dev",
      category: "scanning",
      description:
        "Semgrep is a fast, open-source, static analysis tool for finding bugs and enforcing code standards across many languages.",
      bltUrl: "https://blt.owasp.org/projects/semgrep",
      ambassadors: [
        {
          name: "Yuki Tanaka",
          github: "yukitanaka",
          role: "SAST Specialist",
        },
      ],
    },
    {
      id: "owasp-top10",
      name: "OWASP Top 10",
      logo: "🔟",
      url: "https://owasp.org/www-project-top-ten/",
      category: "community",
      description:
        "The OWASP Top 10 is the standard awareness document for web application security, representing the most critical security risks to web applications.",
      bltUrl: "https://blt.owasp.org/projects/owasp-top10",
      ambassadors: [
        {
          name: "Marcus Johnson",
          github: "marcusj-owasp",
          role: "OWASP Chapter Lead",
        },
        {
          name: "Layla Hassan",
          github: "laylah-sec",
          role: "AppSec Advocate",
        },
      ],
    },
  ];
  
  // Derive GitHub avatar URLs automatically
  PROJECTS.forEach((project) => {
    project.ambassadors.forEach((amb) => {
      if (!amb.avatarUrl && amb.github) {
        amb.avatarUrl = `https://github.com/${amb.github}.png?size=56`;
      }
    });
  });