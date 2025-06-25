# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
