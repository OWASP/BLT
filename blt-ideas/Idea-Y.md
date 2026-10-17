# Idea Y — SecureCall: Privacy-First Video Call Note Taker for Bug Disclosure Discussions

## One line

A secure video call note taker that doesn't save transcriptions and can be useful when talking securely about bug disclosures.

---

## Problem & personas

- **Security Researcher Sam** needs to discuss sensitive vulnerabilities with maintainers via video calls but worries about transcripts leaking or being stored insecurely.
- **Maintainer Maya** wants structured notes from disclosure discussions without risking permanent storage of exploit details that could be compromised.
- **Bug Bounty Program Manager Patricia** requires ephemeral documentation of disclosure conversations that can be reviewed during the call but vanishes afterwards.

Today, when discussing sensitive security issues over video calls, participants either:
1. Take manual notes that may miss critical details
2. Use transcription services that permanently store sensitive vulnerability information
3. Record calls with retention risks and compliance concerns

**SecureCall** provides real-time, AI-powered note-taking during security-focused video calls with a unique architecture: notes are displayed live but **never persisted** after the call ends. Participants can review structured takeaways during the discussion, export temporary summaries if needed, but the system ensures no long-term storage of sensitive exploit details.

---

## Core idea

A **privacy-first video call companion** that:

1. **Real-time transcription display** — Shows live transcription during the call only; participants can see what's being captured.
2. **Structured note generation** — AI extracts key points, action items, decisions, and vulnerability classifications into a structured format during the call.
3. **Zero persistence** — Transcriptions and audio are **never saved** to disk or cloud; all processing happens in-memory.
4. **Optional ephemeral export** — During or immediately after the call, participants can copy/export a summary with sensitive details redacted (e.g., "discussed XSS in auth flow" without exploit code).
5. **End-to-end encrypted** — All audio/video streams use E2EE; the AI processing layer never sees raw media, only encrypted chunks.
6. **Compliance-ready** — Designed for GDPR, SOC 2, and responsible disclosure policies; explicit "no recording" mode with participant consent.

**Use cases:**
- Initial triage calls for vulnerability disclosures
- Coordination between researcher and maintainer
- Internal security team discussions about active incidents
- Bug bounty program review meetings

---

## Technical architecture (sketch)

### Components

1. **Web-based client** (React/Next.js)
   - WebRTC integration for audio capture (no video storage)
   - Real-time transcription display
   - Structured note preview panel
   - Copy/export summary button

2. **Processing pipeline (in-memory only)**
   - Audio chunks → streaming speech-to-text (e.g., Whisper API, Deepgram)
   - Transcription → AI summarization (GPT-4, Gemini, or local Llama)
   - Structured extraction: action items, decisions, vulnerability severity, next steps
   - No disk writes, no database persistence

3. **Privacy controls**
   - Participant consent UI: "This call uses ephemeral note-taking; transcripts will not be saved."
   - Optional redaction layer: auto-remove specific exploit code patterns, IP addresses, credentials
   - Session timeout: all in-memory data cleared 5 minutes after call ends

4. **Optional integrations**
   - GitHub Issues: export sanitized summary as private issue comment (user-triggered)
   - BLT platform: create disclosure event with high-level details (e.g., "XSS discussed, CVE pending")
   - Slack/Discord webhooks: send ephemeral summary to private channels

---

## Data model (ephemeral only)

**No persistent database.** All data structures exist in-memory during the call session.

```text
CallSession (in-memory, TTL = call duration + 5 min)
  - session_id (UUID)
  - participants (list of user IDs)
  - start_time, end_time
  - consent_acknowledged (bool)
  - encryption_key (ephemeral, per-session)

TranscriptChunk (in-memory stream)
  - speaker_id
  - text
  - timestamp
  - confidence_score

StructuredNotes (in-memory, updated live)
  - action_items (list)
  - decisions (list)
  - vulnerability_summary (redacted high-level)
  - next_steps (list)
  - participants_summary
```

Export format (user-triggered, one-time only):
```markdown
## Call Summary (generated [timestamp])
**Participants:** [names]
**Duration:** [minutes]

### Key Points
- [AI-extracted, redacted]

### Action Items
- [ ] [action]

### Next Steps
- [next steps]

_Note: This summary was generated ephemerally. Original transcription was not saved._
```

---

## API surface (minimal)

- `POST /api/v1/secure-call/session/start` — Create ephemeral session, return session_id and WebRTC config.
- `WS /api/v1/secure-call/session/{id}/stream` — WebSocket for audio chunks → transcription stream.
- `GET /api/v1/secure-call/session/{id}/notes` — Fetch current structured notes (in-memory only, expires after call).
- `POST /api/v1/secure-call/session/{id}/export` — Generate one-time sanitized summary (user-triggered).
- `POST /api/v1/secure-call/session/{id}/end` — Explicitly end session; clears all in-memory data.

Auth: BLT session + CSRF; only participants in the session can access notes.

---

## UX flows

### Security researcher initiating a disclosure call

1. Navigate to BLT → "Start Secure Disclosure Call"
2. Invite maintainer (email or BLT username)
3. Call UI: video/audio controls, live transcription panel (right side), structured notes panel (below)
4. During call: AI extracts action items, decisions, severity assessment
5. At end of call: "Export Summary" button → copy sanitized markdown to clipboard
6. 5 minutes after call ends: all data purged from memory

### Maintainer reviewing a disclosure

1. Receive BLT notification: "Sam has invited you to a secure disclosure call"
2. Join call → consent UI: "Transcripts will be displayed live but not saved. Proceed?"
3. See live transcription, structured notes updating in real-time
4. Take screenshots of structured notes if needed (user responsibility, not system-stored)
5. End call → data purged; only user-exported summaries remain (if triggered)

---

## Privacy & compliance

- **No recording:** Audio/video streams are never stored; only ephemeral transcription chunks in memory.
- **Consent-first:** All participants must acknowledge ephemeral processing before call starts.
- **Data retention:** Zero. All session data cleared within 5 minutes of call end.
- **Encryption:** E2EE for all audio/video; AI processing layer uses ephemeral keys per session.
- **GDPR compliance:** No personal data storage; transcripts are not retained; export is user-triggered and optional.
- **Security best practices:** No logs containing transcription content; rate-limiting on export to prevent scraping.

---

## Development program scope (350h)

**Must-have (MVP):**

- Session management (create, join, end) with participant consent UI.
- WebRTC audio capture (no video storage) + streaming transcription (Whisper API or Deepgram).
- In-memory transcription display (live-updating React component).
- AI-powered structured note extraction (action items, decisions, severity) using GPT-4 or Gemini.
- Ephemeral data architecture: no disk writes, TTL-based memory cleanup.
- Export sanitized summary (one-time, user-triggered, markdown format).
- Privacy controls: consent, data purge on session end, redaction of exploit patterns.
- Tests for ephemeral lifecycle, WebSocket streaming, note extraction (~70%+ coverage).
- User docs: how to start a call, privacy guarantees, export instructions.

**Nice-to-have (stretch):**

- Optional GitHub Issues integration: export summary as private comment (with user auth).
- Speaker diarization: identify who said what (ephemeral only).
- Multi-language transcription support.
- Local model option (e.g., Whisper running locally for fully air-gapped deployments).

---

## Evaluation metrics (for development program)

- **Adoption:** ≥20 disclosure calls conducted during pilot; ≥15 participants from 5+ organizations.
- **Usefulness:** Participant rating ≥4/5 on "The structured notes were accurate and helpful for tracking disclosure decisions."
- **Privacy trust:** ≥90% of participants agree "I trust that my transcripts were not saved."
- **Export utility:** ≥70% of calls result in at least one user-triggered summary export.

---

## Pros / cons

**Pros**

- Unique value proposition: privacy-first, zero-persistence note-taking for sensitive security discussions.
- Addresses a real gap: no existing tool combines real-time structured notes with guaranteed ephemeral processing.
- Builds trust: explicit "no recording" mode is ideal for responsible disclosure.
- Complements BLT: natural fit for disclosure workflows, triage calls, bug bounty programs.

**Cons**

- Requires user trust in ephemeral architecture (mitigated by open-source code, independent audits).
- No playback or review after call ends (by design; trade-off for privacy).
- Depends on external transcription APIs (Whisper, Deepgram) unless self-hosted model is used.
- Limited utility outside security/disclosure context (narrow focus).

---

## Why it fits development program

- Clear, standalone scope: ephemeral session management + WebRTC audio + AI summarization + privacy guarantees.
- 350h is sufficient to build MVP: session lifecycle, in-memory transcription, structured notes, export, and pilot testing.
- Addresses Discussion #5495: helps security researchers and maintainers communicate safely about vulnerabilities without retention risk.
- Unique positioning: no direct competitor offers privacy-first, ephemeral note-taking for security disclosure calls.

---

## Integration points

- **BLT platform:** Optional integration to create disclosure events or link summaries to issues (user-triggered).
- **GitHub:** Optional export to private issue comments (requires user OAuth).
- **Slack/Discord:** Optional webhooks to send ephemeral summaries to private security channels.
- **Local models:** Stretch goal to support self-hosted Whisper or Llama for fully air-gapped deployments.

---

_Last Updated: February 2026_
