# Project N — AI Agent (RAG) for Intelligent Onboarding & Security Learning

**One line:** Replace the inoperative chatbot with a RAG-powered AI assistant for user/contributor onboarding, CVE result clarification, security education without disclosing vulnerabilities and other features.


## Description

OWASP BLT currently has a **completely commented-out LangChain-based chatbot implementation** (`website/bot.py`, 202 lines) that was disabled due to issues. This project will **restore, refactor, and expand** that infrastructure alongside making the website chatbot operational.

### Core Use Cases

1. **User & Contributor Onboarding**
   - Guide new users through setup, explain platform features (BACON rewards, bug bounties, Adventures)
   - Help contributors navigate codebase, understand contribution workflows, and find issues to work on
   - Answer common questions about OWASP, security concepts, and BLT architecture

2. **CVE Results Clarification (Project A Integration)**
   - Help maintainers understand CVE severity scores and CVSS metrics from automated scans
   - Provide context about vulnerability classifications without exposing raw vulnerability data
   - Explain remediation priorities and connect to relevant documentation

3. **Security Education Support (Project C Integration)**
   - Answer security concept questions and guide users through Adventures and Labs
   - Provide learning resources without disclosing confidential vulnerability details
   - Maintain strict architectural boundaries: knowledge base uses ONLY documentation and educational content, NEVER Issue model data
