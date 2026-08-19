export const overviewMetrics = [
  {
    id: 'metrics-1',
    label: 'Total Webhooks Processed',
    value: '12,458',
    change: '12.3%',
    changeType: 'up',
    icon: 'Activity',
    accentColor: 'text-blue-500'
  },
  {
    id: 'metrics-2',
    label: 'PII Catch Rate',
    value: '99.7%',
    change: '0.2%',
    changeType: 'up',
    icon: 'ShieldCheck',
    accentColor: 'text-green-500'
  },
  {
    id: 'metrics-3',
    label: 'Avg Triage Latency',
    value: '1.2s',
    change: '8.1%',
    changeType: 'down',
    icon: 'Timer',
    accentColor: 'text-green-500'
  },
  {
    id: 'metrics-4',
    label: 'Active Quarantine',
    value: '3',
    change: '2',
    changeType: 'up',
    icon: 'AlertTriangle',
    accentColor: 'text-red-500'
  }
];

export const activityFeed = [
  {
    id: 'act-1',
    eventId: 'EVT-7841',
    type: 'webhook_received',
    status: 'pending',
    source: 'Reflected XSS in search endpoint #1234',
    timestamp: '2026-08-14T23:45:12.000Z',
    target: 'gitlab.com/owasp-blt/blt/issues/1234',
    latencyMs: 12
  },
  {
    id: 'act-2',
    eventId: 'EVT-7840',
    type: 'redaction_check',
    status: 'redaction_passed',
    source: 'Stored XSS in user profile #1233',
    timestamp: '2026-08-14T23:40:05.000Z',
    target: 'gitlab.com/owasp-blt/blt/issues/1233',
    latencyMs: 450
  },
  {
    id: 'act-3',
    eventId: 'EVT-7839',
    type: 'summarization',
    status: 'summarized',
    source: 'SQL Injection in login form #1232',
    timestamp: '2026-08-14T23:35:10.000Z',
    target: 'gitlab.com/owasp-blt/blt/issues/1232',
    latencyMs: 1250
  },
  {
    id: 'act-4',
    eventId: 'EVT-7838',
    type: 'embedding',
    status: 'embedded',
    source: 'CSRF token missing on password reset #1231',
    timestamp: '2026-08-14T23:25:00.000Z',
    target: 'gitlab.com/owasp-blt/blt/issues/1231',
    latencyMs: 820
  },
  {
    id: 'act-5',
    eventId: 'EVT-7837',
    type: 'duplicate_check',
    status: 'failed',
    source: 'Insecure Direct Object Reference in API #1230',
    timestamp: '2026-08-14T23:15:30.000Z',
    target: 'gitlab.com/owasp-blt/blt/issues/1230',
    latencyMs: 3100
  },
  {
    id: 'act-6',
    eventId: 'EVT-7836',
    type: 'webhook_received',
    status: 'pending',
    source: 'Broken Access Control in admin panel #1229',
    timestamp: '2026-08-14T22:50:45.000Z',
    target: 'gitlab.com/owasp-blt/blt/issues/1229',
    latencyMs: 15
  },
  {
    id: 'act-7',
    eventId: 'EVT-7835',
    type: 'redaction_check',
    status: 'redaction_passed',
    source: 'Exposed API Keys in repository #1228',
    timestamp: '2026-08-14T22:45:10.000Z',
    target: 'gitlab.com/owasp-blt/blt/issues/1228',
    latencyMs: 520
  },
  {
    id: 'act-8',
    eventId: 'EVT-7834',
    type: 'summarization',
    status: 'summarized',
    source: 'Rate limiting bypass on login #1227',
    timestamp: '2026-08-14T22:30:22.000Z',
    target: 'gitlab.com/owasp-blt/blt/issues/1227',
    latencyMs: 1400
  },
  {
    id: 'act-9',
    eventId: 'EVT-7833',
    type: 'embedding',
    status: 'embedded',
    source: 'Unvalidated redirects in OAuth flow #1226',
    timestamp: '2026-08-14T22:15:15.000Z',
    target: 'gitlab.com/owasp-blt/blt/issues/1226',
    latencyMs: 850
  },
  {
    id: 'act-10',
    eventId: 'EVT-7832',
    type: 'duplicate_check',
    status: 'failed',
    source: 'Server-Side Request Forgery (SSRF) #1225',
    timestamp: '2026-08-14T21:45:50.000Z',
    target: 'gitlab.com/owasp-blt/blt/issues/1225',
    latencyMs: 3500
  },
  {
    id: 'act-11',
    eventId: 'EVT-7831',
    type: 'webhook_received',
    status: 'pending',
    source: 'XML External Entity (XXE) injection #1224',
    timestamp: '2026-08-14T21:20:10.000Z',
    target: 'gitlab.com/owasp-blt/blt/issues/1224',
    latencyMs: 18
  },
  {
    id: 'act-12',
    eventId: 'EVT-7830',
    type: 'redaction_check',
    status: 'redaction_passed',
    source: 'Missing Security Headers #1223',
    timestamp: '2026-08-14T21:05:40.000Z',
    target: 'gitlab.com/owasp-blt/blt/issues/1223',
    latencyMs: 410
  },
  {
    id: 'act-13',
    eventId: 'EVT-7829',
    type: 'summarization',
    status: 'summarized',
    source: 'Command Injection via image upload #1222',
    timestamp: '2026-08-14T20:50:20.000Z',
    target: 'gitlab.com/owasp-blt/blt/issues/1222',
    latencyMs: 1600
  },
  {
    id: 'act-14',
    eventId: 'EVT-7828',
    type: 'embedding',
    status: 'embedded',
    source: 'Insecure Deserialization of user session #1221',
    timestamp: '2026-08-14T20:25:10.000Z',
    target: 'gitlab.com/owasp-blt/blt/issues/1221',
    latencyMs: 910
  },
  {
    id: 'act-15',
    eventId: 'EVT-7827',
    type: 'duplicate_check',
    status: 'failed',
    source: 'Session Fixation Vulnerability #1220',
    timestamp: '2026-08-14T20:10:05.000Z',
    target: 'gitlab.com/owasp-blt/blt/issues/1220',
    latencyMs: 3050
  }
];

export const quarantineItems = [
  {
    id: 'q-1',
    eventId: 'EVT-7837',
    errorType: 'DuplicateConflict',
    severity: 'high',
    message: 'Duplicate check timed out after 3000ms while querying vector DB',
    source: 'Insecure Direct Object Reference in API #1230',
    timestamp: '2026-08-14T23:15:30.000Z',
    retryCount: 2,
    maxRetries: 3
  },
  {
    id: 'q-2',
    eventId: 'EVT-7832',
    errorType: 'StateTransitionError',
    severity: 'critical',
    message: 'Failed to transition issue state from triage to assigned',
    source: 'Server-Side Request Forgery (SSRF) #1225',
    timestamp: '2026-08-14T21:45:50.000Z',
    retryCount: 1,
    maxRetries: 3
  },
  {
    id: 'q-3',
    eventId: 'EVT-7827',
    errorType: 'RedactionFailed',
    severity: 'high',
    message: 'Presidio analyzer service unavailable',
    source: 'Session Fixation Vulnerability #1220',
    timestamp: '2026-08-14T20:10:05.000Z',
    retryCount: 3,
    maxRetries: 3
  },
  {
    id: 'q-4',
    eventId: 'EVT-7790',
    errorType: 'EmbeddingTimeout',
    severity: 'medium',
    message: 'OpenAI API latency exceeded configured threshold',
    source: 'Directory Traversal via file parameter #1195',
    timestamp: '2026-08-14T15:20:00.000Z',
    retryCount: 2,
    maxRetries: 3
  },
  {
    id: 'q-5',
    eventId: 'EVT-7750',
    errorType: 'StateTransitionError',
    severity: 'critical',
    message: 'GitLab API returned 502 Bad Gateway',
    source: 'Denial of Service via XML bomb #1150',
    timestamp: '2026-08-13T10:45:12.000Z',
    retryCount: 3,
    maxRetries: 3
  },
  {
    id: 'q-6',
    eventId: 'EVT-7721',
    errorType: 'DuplicateConflict',
    severity: 'low',
    message: 'Concurrent update detected during duplicate merge',
    source: 'Sensitive data exposure in logs #1125',
    timestamp: '2026-08-12T09:10:30.000Z',
    retryCount: 1,
    maxRetries: 3
  }
];

export const duplicateDetections = [
  {
    id: 'dup-1',
    sourceIssue: { id: 'ISS-1234', title: 'Reflected XSS in search endpoint #1234', url: 'https://gitlab.com/owasp-blt/blt/issues/1234' },
    targetIssue: { id: 'ISS-1180', title: 'XSS vulnerability in search bar #1180', url: 'https://gitlab.com/owasp-blt/blt/issues/1180' },
    confidence: 0.92,
    vectorSimilarity: 0.89,
    status: 'matched',
    detectedAt: '2026-08-14T23:46:00.000Z',
    entityOverlap: ['XSS', 'search', 'input validation']
  },
  {
    id: 'dup-2',
    sourceIssue: { id: 'ISS-1232', title: 'SQL Injection in login form #1232', url: 'https://gitlab.com/owasp-blt/blt/issues/1232' },
    targetIssue: { id: 'ISS-1050', title: 'Blind SQLi on authentication endpoint #1050', url: 'https://gitlab.com/owasp-blt/blt/issues/1050' },
    confidence: 0.87,
    vectorSimilarity: 0.85,
    status: 'reviewing',
    detectedAt: '2026-08-14T23:36:15.000Z',
    entityOverlap: ['SQL Injection', 'login', 'auth']
  },
  {
    id: 'dup-3',
    sourceIssue: { id: 'ISS-1222', title: 'Command Injection via image upload #1222', url: 'https://gitlab.com/owasp-blt/blt/issues/1222' },
    targetIssue: { id: 'ISS-0985', title: 'RCE in avatar upload #985', url: 'https://gitlab.com/owasp-blt/blt/issues/985' },
    confidence: 0.95,
    vectorSimilarity: 0.93,
    status: 'matched',
    detectedAt: '2026-08-14T20:51:25.000Z',
    entityOverlap: ['Command Injection', 'upload', 'RCE']
  },
  {
    id: 'dup-4',
    sourceIssue: { id: 'ISS-1229', title: 'Broken Access Control in admin panel #1229', url: 'https://gitlab.com/owasp-blt/blt/issues/1229' },
    targetIssue: { id: 'ISS-1100', title: 'Privilege escalation via admin routes #1100', url: 'https://gitlab.com/owasp-blt/blt/issues/1100' },
    confidence: 0.81,
    vectorSimilarity: 0.79,
    status: 'dismissed',
    detectedAt: '2026-08-14T22:52:00.000Z',
    entityOverlap: ['Access Control', 'admin', 'privilege']
  },
  {
    id: 'dup-5',
    sourceIssue: { id: 'ISS-1226', title: 'Unvalidated redirects in OAuth flow #1226', url: 'https://gitlab.com/owasp-blt/blt/issues/1226' },
    targetIssue: { id: 'ISS-0890', title: 'Open redirect vulnerability on login #890', url: 'https://gitlab.com/owasp-blt/blt/issues/890' },
    confidence: 0.88,
    vectorSimilarity: 0.86,
    status: 'reviewing',
    detectedAt: '2026-08-14T22:16:10.000Z',
    entityOverlap: ['redirect', 'OAuth', 'login']
  }
];

export const redactionLog = [
  {
    id: 'red-1',
    eventId: 'EVT-7840',
    entityType: 'EMAIL_ADDRESS',
    originalByteLength: 24,
    redactionMethod: 'presidio',
    timestamp: '2026-08-14T23:40:02.000Z',
    sourceFile: 'issue_body.md',
    confidence: 0.99
  },
  {
    id: 'red-2',
    eventId: 'EVT-7840',
    entityType: 'PHONE_NUMBER',
    originalByteLength: 12,
    redactionMethod: 'presidio',
    timestamp: '2026-08-14T23:40:03.000Z',
    sourceFile: 'issue_body.md',
    confidence: 0.95
  },
  {
    id: 'red-3',
    eventId: 'EVT-7835',
    entityType: 'AWS_KEY',
    originalByteLength: 20,
    redactionMethod: 'regex_fallback',
    timestamp: '2026-08-14T22:45:05.000Z',
    sourceFile: 'issue_body.md',
    confidence: 1.0
  },
  {
    id: 'red-4',
    eventId: 'EVT-7835',
    entityType: 'GITHUB_TOKEN',
    originalByteLength: 40,
    redactionMethod: 'regex_fallback',
    timestamp: '2026-08-14T22:45:06.000Z',
    sourceFile: 'issue_comments.json',
    confidence: 0.98
  },
  {
    id: 'red-5',
    eventId: 'EVT-7830',
    entityType: 'IP_ADDRESS',
    originalByteLength: 15,
    redactionMethod: 'presidio',
    timestamp: '2026-08-14T21:05:38.000Z',
    sourceFile: 'issue_body.md',
    confidence: 0.99
  },
  {
    id: 'red-6',
    eventId: 'EVT-7825',
    entityType: 'JWT',
    originalByteLength: 180,
    redactionMethod: 'regex_fallback',
    timestamp: '2026-08-14T19:30:15.000Z',
    sourceFile: 'attachment_headers.txt',
    confidence: 1.0
  },
  {
    id: 'red-7',
    eventId: 'EVT-7820',
    entityType: 'CREDIT_CARD',
    originalByteLength: 19,
    redactionMethod: 'presidio',
    timestamp: '2026-08-14T18:15:20.000Z',
    sourceFile: 'issue_body.md',
    confidence: 0.94
  },
  {
    id: 'red-8',
    eventId: 'EVT-7815',
    entityType: 'SSN',
    originalByteLength: 11,
    redactionMethod: 'presidio',
    timestamp: '2026-08-14T17:05:40.000Z',
    sourceFile: 'issue_body.md',
    confidence: 0.92
  },
  {
    id: 'red-9',
    eventId: 'EVT-7810',
    entityType: 'API_KEY',
    originalByteLength: 32,
    redactionMethod: 'regex_fallback',
    timestamp: '2026-08-14T16:20:10.000Z',
    sourceFile: 'issue_body.md',
    confidence: 0.98
  },
  {
    id: 'red-10',
    eventId: 'EVT-7805',
    entityType: 'EMAIL_ADDRESS',
    originalByteLength: 21,
    redactionMethod: 'presidio',
    timestamp: '2026-08-14T15:10:05.000Z',
    sourceFile: 'issue_body.md',
    confidence: 0.99
  },
  {
    id: 'red-11',
    eventId: 'EVT-7800',
    entityType: 'IP_ADDRESS',
    originalByteLength: 13,
    redactionMethod: 'presidio',
    timestamp: '2026-08-14T14:45:30.000Z',
    sourceFile: 'network_logs.txt',
    confidence: 0.99
  },
  {
    id: 'red-12',
    eventId: 'EVT-7795',
    entityType: 'PHONE_NUMBER',
    originalByteLength: 14,
    redactionMethod: 'presidio',
    timestamp: '2026-08-14T13:20:15.000Z',
    sourceFile: 'contact_info.md',
    confidence: 0.96
  }
];

export const sidebarNavigation = [
  {
    group: 'Platform',
    items: [
      { label: 'Overview', path: '/', icon: 'LayoutDashboard' },
      { label: 'Triage', path: '/triage', icon: 'ListChecks' },
      { label: 'Security', path: '/security', icon: 'ShieldAlert' }
    ]
  },
  {
    group: 'Operations',
    items: [
      { label: 'Activity', path: '/activity', icon: 'Activity' },
      { label: 'Settings', path: '/settings', icon: 'Settings' }
    ]
  }
];
