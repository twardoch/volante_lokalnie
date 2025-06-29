# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Textual-based Terminal User Interface (TUI)** - A new interactive interface for managing offers
  - Interactive offer table with sorting and filtering capabilities
  - Real-time statistics panel showing total offers, value, views, and pending changes
  - Detailed offer view/edit screen with markdown preview
  - Progress indicators for long-running operations
  - Keyboard shortcuts for common operations
- `LOG.md` for tracking development progress and issues resolved
- `.specstory/` directory documenting development history and decisions
- Support for uv package manager with `uv.lock` file
- Platform-specific user directory support via `platformdirs`

### Changed
- **Major Architecture Refactoring** - Simplified and streamlined core logic
  - Separated TUI functionality into dedicated `tui.py` module
  - Reduced main `volante_lokalnie.py` by ~1400 lines through better code organization
  - Improved separation of concerns between CLI and TUI interfaces
- **Offer Detection Improvements**
  - Changed from "my-offer-card" to "active-offer-card" class detection
  - Increased timeout from 10 to 30 seconds for better reliability
  - Added empty state detection and better error handling
  - Improved pagination handling and offer counting
- **TUI Event Handling**
  - Fixed dynamic binding errors by using on_key override instead of _update_bindings
  - Improved keyboard event handling based on context
- Updated dependencies to use more recent versions
- Enhanced error messages and logging throughout

### Fixed
- Offer card detection in `refresh_offers` method
- Dynamic key binding issues in TUI MainScreen
- Page navigation and state detection reliability
- Timeout issues when loading offers

### Removed
- Redundant URL checks in favor of login state verification
- Unnecessary binding update methods in TUI

## [1.0.1] - 2025-01-xx

### Added
- `PLAN.md` for detailed project planning.
- `TODO.md` for a checklist of tasks.
- `CHANGELOG.md` to track project changes.

### Changed
- Simplified `ensure_debug_chrome` by removing an unused `tempfile.mkdtemp()` call.
- Refactored `fetch_offers` and `refresh_offers` methods in `AllegroScraper` for better code reuse and clarity. `fetch_offers` now calls `refresh_offers` with specific parameters. `refresh_offers` now handles optional resetting of pending changes and conditional fetching of missing descriptions.
- Clarified the workflow for staging and publishing offer details:
    - CLI commands `set-title` and `set-desc` renamed to `stage_title` and `stage_desc` respectively. These now only save title/description templates locally.
    - `AllegroScraper.publish_offer_details` now only publishes changes that have been previously staged via `title_new` and `desc_new` fields.
    - Internal methods in `AllegroScraper` and `ScrapeExecutor` updated to support this clearer separation of staging and publishing.
- Refined `_finalize_successful_publish` in `AllegroScraper` to explicitly clear `title_new` and `desc_new` templates and set `published=True` after a successful publish, before refreshing the offer data from the site.
- Enhanced template evaluation in `_evaluate_template` to support all fields from `OfferData` (e.g., `{price}`, `{views}`, `{offer_id}`) as placeholders.
- Reviewed `offer_id` extraction. Kept current simple method for MVP and expanded TODO comment for future robustness.

### Removed
- Unused `tempfile.mkdtemp()` call in `ensure_debug_chrome`.
