**Blt-education(refined) : Hands-On Code-Centric Security Labs for OWASP BLT (350 hr)**

#### This project transforms BLT’s existing theory-heavy labs into hands-on, code-centric security exercises.
Learners analyze real vulnerable code and configurations, identify security flaws, reason about how they could be exploited, and then apply secure fixes.
The focus is on security thinking, inspired by OWASP Top 10, ethical hacking workflows, and CTF-style reasoning, but scoped for maintainability and learning depth. 

**Each lab follows a three-step workflow:**
- Identify the vulnerability
(What is wrong? Where is it?)

- Explain the exploitation scenario
(How could this be abused? What is the impact?)

- Apply or select the secure fix
(Correct remediation pattern + explanation)

**Proposed Timeline**
- Phase 1 (Weeks 1–4 | ~90-100 hours):
Multi-step validation framework, content schema, and UI foundations
  - Implement multi-step validation (identify, explain, fix)
  - Define reusable content schema for security labs
  - Add UI support for step-wise progress and feedback
   - Maintain backward compatibility with existing labs
   - AI-assisted support:
      - Help draft concise explanations for vulnerabilities and fixes

- Phase 2 (Weeks 5–8 | ~120 hours):
Core hands-on labs covering SQL Injection, XSS, and Configuration Security using the identify → explain → fix workflow
  - Create hands-on labs for:
  - SQL Injection
  - XSS
  - CSRF, IDOR, Authentication flaws
Include exploitation reasoning and secure remediation patterns
Add progress tracking, hints.

- Phase 3 (Weeks 9–11 | ~110 hours):
  - create scheduled security challenges/puzzles, learning progress tracking, and skill coverage visualization
  - Build unified dashboard for labs, challenges, and skill coverage
  Optional AI support:
  - Suggest next labs based on skill gaps

- Phase 4(week12): 
  - e2e testing
  - documentation

**Benefits**
- Helps contributors learn how to think like security reviewers.
- Improves quality of future vulnerability reports and PRs

**Next-Steps**
- It can be integrated with badges/bacon. 
- Mapping NetGuardian findings to learning labs. 
- Can later evolve into a dedicated security learning playground, enabling richer lab types, additional vulnerability categories, and deeper practice