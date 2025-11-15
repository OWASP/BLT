# Changelog

All notable changes to the SelfErase project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project structure
- Flutter app with encrypted local storage
- Cloudflare Workers for public broker metadata
- Core UI screens (Dashboard, Brokers, Profile, Requests)
- Broker database with 5 initial brokers
- Opt-out request templates (GDPR, CCPA, generic)
- Comprehensive documentation
- Security whitepaper
- Contribution guidelines
- GitHub Actions CI/CD workflows
- Multi-platform support (Android, iOS, Windows, macOS, Linux)

### Security
- AES-256-GCM encryption for all local PII storage
- Zero PII transmission architecture
- Stateless Workers (no user data processing)
- Platform secure storage integration
- HTTPS-only communication

## [1.0.0] - TBD

### Initial Release Features

#### Flutter Local App
- ✅ Encrypted local storage with AES-256
- ✅ User profile management
- ✅ Broker browsing and search
- ✅ Opt-out request tracking
- ✅ Privacy dashboard
- ✅ Offline-first functionality
- ✅ Cross-platform support

#### Cloudflare Workers
- ✅ Broker metadata API
- ✅ Health check endpoints
- ✅ Template serving
- ✅ No PII processing

#### Broker Database
- ✅ 5 initial brokers (Whitepages, Spokeo, BeenVerified, TruthFinder, Intelius)
- ✅ Multiple opt-out templates
- ✅ JSON schema validation

#### Documentation
- ✅ README with quick start guide
- ✅ Security whitepaper
- ✅ Architecture documentation
- ✅ Broker addition guide
- ✅ Contributing guidelines

#### Build & Deploy
- ✅ GitHub Actions for CI/CD
- ✅ Multi-platform builds
- ✅ Release workflow with checksums
- ✅ Reproducible builds

### Known Limitations
- No automated opt-out submission (manual only)
- No browser extension yet
- Limited to US data brokers initially
- No hardware key support yet

### Roadmap
See [README.md](README.md#-roadmap) for planned features.

---

## Version Guidelines

### Major Version (X.0.0)
- Breaking changes to data format
- Major architectural changes
- Incompatible API changes

### Minor Version (0.X.0)
- New features (backwards compatible)
- New brokers added
- UI improvements
- Performance enhancements

### Patch Version (0.0.X)
- Bug fixes
- Security patches
- Documentation updates
- Broker information updates

---

## Changelog Categories

### Added
New features, endpoints, brokers, or documentation

### Changed
Changes to existing functionality

### Deprecated
Features that will be removed in future versions

### Removed
Features that have been removed

### Fixed
Bug fixes and error corrections

### Security
Security-related changes and fixes

---

## Contributing to Changelog

When contributing, please add your changes to the `[Unreleased]` section following the categories above.

For more information, see [CONTRIBUTING.md](CONTRIBUTING.md).
