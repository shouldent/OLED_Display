# Changelog

## [1.0.0] - 2026-06-10
### Final release
### Added
- New splash screen with a "typing" animation effect.
- GPU temperature monitoring integration.
- Support for custom fonts (TTF) using JetBrains Mono.
- Visual indicator (pin icon) for manual mode.

### Fixed
- Fixed `TypeError` in framebuffer during text rendering.
- Resolved `OSError` when loading external font resources.
- Optimized coordinate logic for 128x64 displays.

## [0.5.0] - 2026-06-08
### Fixed
- Corrected Google Calendar integration issues.

## [0.4.0] - 2026-06-06
### Added
- Server functionality including a Jarvis-style Desklet and Service.

## [0.3.0] - 2026-06-06
### Added
- Documentation update: Added installation instructions to README.

## [0.2.0] - 2026-06-05
### Added
- New weather screen and associated display functions.
- State persistence: implemented function to save settings to `status.json`.

### Changed
- Refactored project structure for modular screen handling.
- Removed duplicated "resume-auto" function and optimized variable ordering.

## [0.1.0] - 2026-06-03
### Added
- Initial feature: Google Calendar screen with dynamic scrolling.
- Base architecture setup.