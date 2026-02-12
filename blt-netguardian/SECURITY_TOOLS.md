# Security Scanning Tools and Resources

This document provides a comprehensive list of security scanning tools and resources that can be integrated with BLT-NetGuardian for vulnerability detection across different domains.

## Table of Contents

- [Static Application Security Testing (SAST)](#static-application-security-testing-sast)
- [Dynamic Application Security Testing (DAST)](#dynamic-application-security-testing-dast)
- [Dependency and Supply Chain Security](#dependency-and-supply-chain-security)
- [Container and Infrastructure Security](#container-and-infrastructure-security)
- [Web Application Security](#web-application-security)
- [API Security](#api-security)
- [Smart Contract Security](#smart-contract-security)
- [Secret Detection](#secret-detection)
- [Network Security](#network-security)
- [Fuzzing and Testing](#fuzzing-and-testing)
- [Compliance and Configuration](#compliance-and-configuration)
- [Specialized Tools](#specialized-tools)

---

## Static Application Security Testing (SAST)

### Semgrep
- **Website**: https://semgrep.dev/
- **Description**: Fast, customizable static analysis for finding bugs and enforcing code standards
- **Languages**: 30+ languages including Python, JavaScript, Java, Go, Ruby, PHP
- **Use Case**: Code pattern matching, security rule enforcement, custom rule creation
- **License**: LGPL 2.1 (Community Edition)

### Bandit
- **Website**: https://bandit.readthedocs.io/
- **Description**: Security-focused static analyzer for Python code
- **Languages**: Python
- **Use Case**: Finding common security issues in Python code
- **License**: Apache 2.0

### CodeQL
- **Website**: https://codeql.github.com/
- **Description**: Semantic code analysis engine by GitHub
- **Languages**: C/C++, C#, Go, Java, JavaScript/TypeScript, Python, Ruby
- **Use Case**: Advanced code queries, security research, vulnerability detection
- **License**: Free for open source

### Brakeman
- **Website**: https://brakemanscanner.org/
- **Description**: Static analysis security scanner for Ruby on Rails applications
- **Languages**: Ruby
- **Use Case**: Rails-specific vulnerability detection
- **License**: MIT

### SonarQube
- **Website**: https://www.sonarqube.org/
- **Description**: Continuous code quality and security inspection platform
- **Languages**: 25+ languages
- **Use Case**: Code quality metrics, security hotspots, technical debt
- **License**: LGPL 3.0 (Community Edition)

### Gosec
- **Website**: https://github.com/securego/gosec
- **Description**: Security checker for Go source code
- **Languages**: Go
- **Use Case**: Go-specific security vulnerability scanning
- **License**: Apache 2.0

### ESLint Security Plugin
- **Website**: https://github.com/nodesecurity/eslint-plugin-security
- **Description**: ESLint rules for Node.js security
- **Languages**: JavaScript/Node.js
- **Use Case**: JavaScript security best practices
- **License**: Apache 2.0

---

## Dynamic Application Security Testing (DAST)

### OWASP ZAP (Zed Attack Proxy)
- **Website**: https://www.zaproxy.org/
- **Description**: World's most widely used web app scanner
- **Use Case**: Automated and manual web application security testing
- **Features**: Active/passive scanning, fuzzing, API testing
- **License**: Apache 2.0

### Nuclei
- **Website**: https://github.com/projectdiscovery/nuclei
- **Description**: Fast vulnerability scanner based on templates
- **Use Case**: Automated vulnerability detection using YAML templates
- **Features**: 4000+ community templates, custom templates
- **License**: MIT

### w3af
- **Website**: http://w3af.org/
- **Description**: Web Application Attack and Audit Framework
- **Use Case**: Web application vulnerability scanning and exploitation
- **License**: GPL 2.0

### SQLMap
- **Website**: https://sqlmap.org/
- **Description**: Automatic SQL injection and database takeover tool
- **Use Case**: SQL injection detection and exploitation
- **License**: GPL 2.0

### Nikto
- **Website**: https://cirt.net/Nikto2
- **Description**: Web server scanner
- **Use Case**: Web server misconfiguration and vulnerability detection
- **License**: GPL 2.0

### Wapiti
- **Website**: https://wapiti-scanner.github.io/
- **Description**: Web application vulnerability scanner
- **Use Case**: Black-box web security testing
- **License**: GPL 2.0

---

## Dependency and Supply Chain Security

### OWASP Dependency-Check
- **Website**: https://owasp.org/www-project-dependency-check/
- **Description**: Identifies project dependencies with known vulnerabilities
- **Languages**: Java, .NET, Node.js, Python, Ruby, and more
- **Use Case**: Dependency vulnerability scanning using NVD data
- **License**: Apache 2.0

### Snyk
- **Website**: https://snyk.io/
- **Description**: Developer security platform for finding and fixing vulnerabilities
- **Use Case**: Dependency scanning, container scanning, IaC scanning
- **License**: Free tier available

### Trivy
- **Website**: https://github.com/aquasecurity/trivy
- **Description**: Comprehensive security scanner
- **Use Case**: Container images, filesystems, Git repositories, Kubernetes
- **License**: Apache 2.0

### Safety
- **Website**: https://github.com/pyupio/safety
- **Description**: Checks Python dependencies for known security vulnerabilities
- **Languages**: Python
- **Use Case**: Python dependency vulnerability scanning
- **License**: MIT

### npm audit
- **Website**: https://docs.npmjs.com/cli/v8/commands/npm-audit
- **Description**: Built-in Node.js security auditing
- **Languages**: JavaScript/Node.js
- **Use Case**: npm package vulnerability detection
- **License**: Built into npm

### Bundler-audit
- **Website**: https://github.com/rubysec/bundler-audit
- **Description**: Patch-level security verification for Ruby
- **Languages**: Ruby
- **Use Case**: Ruby gem vulnerability scanning
- **License**: GPL 3.0

### OSV-Scanner
- **Website**: https://google.github.io/osv-scanner/
- **Description**: Vulnerability scanner using OSV database
- **Languages**: Multiple ecosystems
- **Use Case**: Cross-ecosystem vulnerability scanning
- **License**: Apache 2.0

---

## Container and Infrastructure Security

### Trivy (Container Scanning)
- **Website**: https://github.com/aquasecurity/trivy
- **Description**: Comprehensive container security scanner
- **Use Case**: Docker/OCI image vulnerability scanning
- **License**: Apache 2.0

### Clair
- **Website**: https://github.com/quay/clair
- **Description**: Static analysis of vulnerabilities in containers
- **Use Case**: Container image layer analysis
- **License**: Apache 2.0

### Anchore Engine
- **Website**: https://github.com/anchore/anchore-engine
- **Description**: Container analysis and inspection platform
- **Use Case**: Deep image inspection and policy-based compliance
- **License**: Apache 2.0

### Grype
- **Website**: https://github.com/anchore/grype
- **Description**: Vulnerability scanner for container images and filesystems
- **Use Case**: Fast container and filesystem vulnerability scanning
- **License**: Apache 2.0

### Checkov
- **Website**: https://www.checkov.io/
- **Description**: Static analysis for Infrastructure as Code
- **Use Case**: Terraform, CloudFormation, Kubernetes, ARM templates
- **License**: Apache 2.0

### tfsec
- **Website**: https://github.com/aquasecurity/tfsec
- **Description**: Security scanner for Terraform code
- **Use Case**: Terraform misconfiguration detection
- **License**: MIT

### Terrascan
- **Website**: https://github.com/tenable/terrascan
- **Description**: Static code analyzer for IaC
- **Use Case**: Multi-cloud IaC security scanning
- **License**: Apache 2.0

---

## Web Application Security

### Burp Suite Community Edition
- **Website**: https://portswigger.net/burp/communitydownload
- **Description**: Web security testing toolkit
- **Use Case**: Manual web application security testing, proxy, scanner
- **License**: Community Edition available

### XSStrike
- **Website**: https://github.com/s0md3v/XSStrike
- **Description**: Advanced XSS detection suite
- **Use Case**: Cross-site scripting vulnerability detection
- **License**: GPL 3.0

### Dalfox
- **Website**: https://github.com/hahwul/dalfox
- **Description**: Parameter analysis and XSS scanning tool
- **Use Case**: Fast XSS scanning and parameter analysis
- **License**: MIT

### Retire.js
- **Website**: https://retirejs.github.io/retire.js/
- **Description**: Scanner detecting use of JavaScript libraries with known vulnerabilities
- **Languages**: JavaScript
- **Use Case**: Frontend JavaScript library vulnerability detection
- **License**: Apache 2.0

### Security Headers
- **Website**: https://github.com/koenbuyens/securityheaders
- **Description**: Checks security headers on websites
- **Use Case**: HTTP security header analysis
- **License**: MIT

---

## API Security

### OWASP API Security Top 10
- **Website**: https://owasp.org/www-project-api-security/
- **Description**: Documentation of most critical API security risks
- **Use Case**: API security awareness and testing guidance

### Postman Security Testing
- **Website**: https://www.postman.com/
- **Description**: API development and testing platform with security features
- **Use Case**: API security testing and validation

### REST-Attacker
- **Website**: https://github.com/RUB-NDS/REST-Attacker
- **Description**: Automatic testing tool for REST APIs
- **Use Case**: REST API security testing
- **License**: MIT

### Fuzzapi
- **Website**: https://github.com/Fuzzapi/fuzzapi
- **Description**: REST API fuzzing tool
- **Use Case**: API endpoint fuzzing and vulnerability detection
- **License**: MIT

### Astra
- **Website**: https://github.com/flipkart-incubator/astra
- **Description**: Automated Security Testing for REST APIs
- **Use Case**: REST API vulnerability scanning
- **License**: Apache 2.0

---

## Smart Contract Security

### Slither
- **Website**: https://github.com/crytic/slither
- **Description**: Static analysis framework for Solidity
- **Languages**: Solidity, Vyper
- **Use Case**: Smart contract vulnerability detection
- **License**: AGPL 3.0

### Mythril
- **Website**: https://github.com/ConsenSys/mythril
- **Description**: Security analysis tool for EVM bytecode
- **Languages**: Solidity, Vyper
- **Use Case**: Smart contract security analysis using symbolic execution
- **License**: MIT

### Manticore
- **Website**: https://github.com/trailofbits/manticore
- **Description**: Symbolic execution tool for analysis of binaries and smart contracts
- **Languages**: Solidity, EVM bytecode, x86, x86-64, ARMv7
- **Use Case**: Deep smart contract and binary analysis
- **License**: AGPL 3.0

### Echidna
- **Website**: https://github.com/crytic/echidna
- **Description**: Ethereum smart contract fuzzer
- **Languages**: Solidity
- **Use Case**: Property-based fuzzing for smart contracts
- **License**: AGPL 3.0

### Securify
- **Website**: https://github.com/eth-sri/securify2
- **Description**: Security scanner for Ethereum smart contracts
- **Languages**: Solidity
- **Use Case**: Automated security analysis of smart contracts
- **License**: Apache 2.0

### Oyente
- **Website**: https://github.com/enzymefinance/oyente
- **Description**: Symbolic execution tool for Ethereum smart contracts
- **Languages**: Solidity
- **Use Case**: Smart contract vulnerability detection
- **License**: GPL 3.0

---

## Secret Detection

### TruffleHog
- **Website**: https://github.com/trufflesecurity/trufflehog
- **Description**: Find credentials in git repositories
- **Use Case**: Secret scanning in git history and filesystems
- **License**: AGPL 3.0

### GitLeaks
- **Website**: https://github.com/gitleaks/gitleaks
- **Description**: SAST tool for detecting hardcoded secrets
- **Use Case**: Secret detection in git repositories
- **License**: MIT

### detect-secrets
- **Website**: https://github.com/Yelp/detect-secrets
- **Description**: Enterprise-friendly way to detect and prevent secrets in code
- **Use Case**: Pre-commit secret detection
- **License**: Apache 2.0

### git-secrets
- **Website**: https://github.com/awslabs/git-secrets
- **Description**: Prevents committing secrets to git repositories
- **Use Case**: AWS credential and secret protection
- **License**: Apache 2.0

### SecretScanner
- **Website**: https://github.com/deepfence/SecretScanner
- **Description**: Find secrets in container images and file systems
- **Use Case**: Container and filesystem secret scanning
- **License**: Apache 2.0

---

## Network Security

### Nmap
- **Website**: https://nmap.org/
- **Description**: Network discovery and security auditing
- **Use Case**: Network scanning, port scanning, service detection
- **License**: NPSL (Nmap Public Source License)

### Masscan
- **Website**: https://github.com/robertdavidgraham/masscan
- **Description**: TCP port scanner, fastest scanner on the Internet
- **Use Case**: Fast network-wide port scanning
- **License**: AGPL 3.0

### Nessus Essentials
- **Website**: https://www.tenable.com/products/nessus/nessus-essentials
- **Description**: Vulnerability scanner
- **Use Case**: Network vulnerability assessment
- **License**: Free for limited use

### OpenVAS
- **Website**: https://www.openvas.org/
- **Description**: Full-featured vulnerability scanner
- **Use Case**: Network vulnerability scanning and management
- **License**: GPL

### Metasploit Framework
- **Website**: https://www.metasploit.com/
- **Description**: Penetration testing framework
- **Use Case**: Exploit development and vulnerability validation
- **License**: BSD 3-Clause

---

## Fuzzing and Testing

### AFL (American Fuzzy Lop)
- **Website**: https://github.com/google/AFL
- **Description**: Security-oriented fuzzer
- **Use Case**: Coverage-guided fuzzing for binaries
- **License**: Apache 2.0

### LibFuzzer
- **Website**: https://llvm.org/docs/LibFuzzer.html
- **Description**: In-process, coverage-guided evolutionary fuzzer
- **Use Case**: Library fuzzing integrated into LLVM
- **License**: Part of LLVM

### Honggfuzz
- **Website**: https://github.com/google/honggfuzz
- **Description**: Security-oriented fuzzer with powerful analysis options
- **Use Case**: Feedback-driven fuzzing
- **License**: Apache 2.0

### Ffuf
- **Website**: https://github.com/ffuf/ffuf
- **Description**: Fast web fuzzer written in Go
- **Use Case**: Web application fuzzing, directory brute-forcing
- **License**: MIT

### Wfuzz
- **Website**: https://github.com/xmendez/wfuzz
- **Description**: Web application fuzzer
- **Use Case**: Web application brute-forcing and fuzzing
- **License**: GPL 2.0

### Radamsa
- **Website**: https://gitlab.com/akihe/radamsa
- **Description**: General-purpose fuzzer
- **Use Case**: Test case generation from samples
- **License**: MIT

### Atheris
- **Website**: https://github.com/google/atheris
- **Description**: Coverage-guided Python fuzzing engine
- **Languages**: Python
- **Use Case**: Python application fuzzing
- **License**: Apache 2.0

---

## Compliance and Configuration

### OpenSCAP
- **Website**: https://www.open-scap.org/
- **Description**: Security compliance and vulnerability management
- **Use Case**: SCAP-based security compliance validation
- **License**: LGPL 2.1+

### Lynis
- **Website**: https://cisofy.com/lynis/
- **Description**: Security auditing tool for Unix/Linux systems
- **Use Case**: System hardening and compliance auditing
- **License**: GPL 3.0

### InSpec
- **Website**: https://www.inspec.io/
- **Description**: Infrastructure testing and compliance framework
- **Use Case**: Compliance as code, infrastructure testing
- **License**: Apache 2.0

### ScoutSuite
- **Website**: https://github.com/nccgroup/ScoutSuite
- **Description**: Multi-cloud security auditing tool
- **Use Case**: AWS, Azure, GCP security configuration auditing
- **License**: GPL 2.0

### Prowler
- **Website**: https://github.com/prowler-cloud/prowler
- **Description**: AWS and multi-cloud security best practices assessment
- **Use Case**: Cloud security compliance and CIS benchmarks
- **License**: Apache 2.0

---

## Specialized Tools

### Buttercup
- **Website**: https://github.com/trailofbits/buttercup
- **Description**: Web framework for writing security tests in JavaScript
- **Use Case**: Building custom security testing tools and browsers
- **Features**: Instrumented browser for security research, scriptable testing
- **License**: AGPL 3.0
- **Provider**: Trail of Bits

### Mobile Security Framework (MobSF)
- **Website**: https://github.com/MobSF/Mobile-Security-Framework-MobSF
- **Description**: Automated mobile application security testing framework
- **Use Case**: Android and iOS application security testing
- **License**: GPL 3.0

### Androbugs
- **Website**: https://github.com/AndroBugs/AndroBugs_Framework
- **Description**: Android vulnerability analysis system
- **Use Case**: Android application vulnerability scanning
- **License**: GPL 3.0

### Drozer
- **Website**: https://github.com/WithSecureLabs/drozer
- **Description**: Security assessment framework for Android
- **Use Case**: Android application security assessment
- **License**: BSD 3-Clause

### Frida
- **Website**: https://frida.re/
- **Description**: Dynamic instrumentation toolkit
- **Use Case**: Runtime analysis, reverse engineering
- **License**: wxWindows Library License

### Ghidra
- **Website**: https://ghidra-sre.org/
- **Description**: Software reverse engineering framework
- **Use Case**: Binary analysis, reverse engineering
- **License**: Apache 2.0

### Radare2
- **Website**: https://rada.re/
- **Description**: Reverse engineering framework
- **Use Case**: Binary analysis, debugging, disassembly
- **License**: LGPL 3.0

### angr
- **Website**: https://angr.io/
- **Description**: Binary analysis platform
- **Use Case**: Symbolic execution, binary analysis
- **License**: BSD 2-Clause

### Taint Analysis Tools

#### Pysa (Python Static Analyzer)
- **Website**: https://pyre-check.org/docs/pysa-basics/
- **Description**: Security-focused static analysis for Python
- **Languages**: Python
- **Use Case**: Taint analysis for Python applications
- **License**: MIT

#### FlowDroid
- **Website**: https://github.com/secure-software-engineering/FlowDroid
- **Description**: Static taint analysis tool for Android applications
- **Use Case**: Android data flow analysis
- **License**: LGPL 2.1

---

## Integration Recommendations for BLT-NetGuardian

### High Priority Integrations

1. **SAST**: Semgrep, Bandit (for Python), CodeQL
2. **DAST**: OWASP ZAP, Nuclei
3. **Dependency Scanning**: OWASP Dependency-Check, Trivy, OSV-Scanner
4. **Container Security**: Trivy, Grype
5. **Secret Detection**: TruffleHog, GitLeaks
6. **Smart Contracts**: Slither, Mythril
7. **API Security**: REST-Attacker, Astra
8. **Web Security**: XSStrike, Dalfox

### Workflow Integration

```
Discovery → Classification → Scanner Selection → Execution → Result Aggregation
                                    ↓
    ┌───────────────────────────────┴────────────────────────────┐
    │                                                             │
    ▼                           ▼                     ▼           ▼
Web Apps                  Repositories          Smart           APIs
(ZAP, Nuclei)            (Semgrep, GitLeaks)  Contracts    (REST-Attacker)
                         (Dep-Check, Trivy)   (Slither)
```

### Tool Selection Criteria

When selecting tools for integration:

1. **License Compatibility**: Prefer Apache 2.0, MIT, GPL licenses
2. **Maintenance**: Active development and community support
3. **Performance**: Fast execution for autonomous scanning
4. **Accuracy**: Low false positive rates
5. **Automation**: CLI-friendly, scriptable
6. **Coverage**: Broad vulnerability detection
7. **Output Format**: Structured output (JSON, SARIF)

### API-First Tools

Tools with REST APIs or easy CLI integration:
- Semgrep (CLI + API)
- Trivy (CLI)
- Nuclei (CLI)
- GitLeaks (CLI)
- Slither (CLI)
- OWASP ZAP (API)

---

## Additional Resources

### Vulnerability Databases

- **National Vulnerability Database (NVD)**: https://nvd.nist.gov/
- **OSV (Open Source Vulnerabilities)**: https://osv.dev/
- **GitHub Advisory Database**: https://github.com/advisories
- **Exploit Database**: https://www.exploit-db.com/
- **CVE Details**: https://www.cvedetails.com/

### Security Testing Guides

- **OWASP Testing Guide**: https://owasp.org/www-project-web-security-testing-guide/
- **OWASP ASVS**: https://owasp.org/www-project-application-security-verification-standard/
- **OWASP Mobile Security Testing Guide**: https://owasp.org/www-project-mobile-security-testing-guide/
- **NIST Security Guidelines**: https://www.nist.gov/cybersecurity

### Security Frameworks

- **MITRE ATT&CK**: https://attack.mitre.org/
- **CWE (Common Weakness Enumeration)**: https://cwe.mitre.org/
- **CAPEC (Common Attack Pattern Enumeration)**: https://capec.mitre.org/

---

## Maintenance

This document should be updated regularly as:
- New security tools emerge
- Existing tools evolve or become deprecated
- Integration experiences provide insights
- Community feedback identifies gaps

**Last Updated**: 2025-12-13

**Contributors**: OWASP BLT Community

---

## Contributing

To suggest additional tools or updates to this list:
1. Open an issue with tool details
2. Include: name, website, description, use case, license
3. Explain why it should be included
4. Submit a pull request with the addition

---

*This document is maintained by the OWASP BLT community to support the BLT-NetGuardian autonomous security scanning platform.*
