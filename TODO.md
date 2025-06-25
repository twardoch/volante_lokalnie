- [ ] **Project Setup and Initial File Creation:**
    - [x] Create `PLAN.md`
    - [ ] Create `TODO.md`
    - [x] Create `CHANGELOG.md`

- [ ] **Analyze `ensure_debug_chrome` function:**
    - [x] Investigate `tempfile.mkdtemp()` and unused `temp_dir`.
    - [x] Remove `tempfile.mkdtemp()` if unused.
    - [ ] Add logging/documentation note for hardcoded `CHROME_PATH` (inline TODO added, full doc update later).

- [ ] **Refactor `fetch_offers` and `refresh_offers` in `AllegroScraper`:**
    - [x] Modify `refresh_offers` to accept optional `reset_pending_changes: bool` and `fetch_missing_descriptions: bool`.
    - [x] Implement reset logic in `refresh_offers` based on the new parameter.
    - [x] Simplify `fetch_offers` to call `refresh_offers`.
    - [x] Ensure description fetching logic in `refresh_offers` is correct and conditional.
    - [x] Update calls in `ScrapeExecutor` if necessary (verified no changes needed in `ScrapeExecutor` for these specific methods as `AllegroScraper.fetch_offers()` signature remained, and `AllegroScraper.refresh_offers()` default call from `execute_read_all` is appropriate).

- [ ] **Clarify `set-title`/`set-desc` and `publish_offer_details` workflow:**
    - [x] Create `AllegroScraper.stage_offer_details` method.
    - [x] Modify `AllegroScraper.publish_offer_details` to only publish staged changes and remove `new_title`/`new_desc` parameters.
    - [x] Update `AllegroScraper._prepare_title_and_desc_for_publish` to use staged templates.
    - [x] Update `AllegroScraper._fill_offer_title` and `_fill_offer_description` to not save evaluated templates to `title_new`/`desc_new`.
    - [x] Rename `ScrapeExecutor.execute_set_title/desc` to `execute_stage_title/desc` and update to call `scraper.stage_offer_details`.
    - [x] Update `ScrapeExecutor.execute_publish` and `execute_publish_all` to correctly use the modified `publish_offer_details`.
    - [x] Rename `VolanteCLI.set_title/desc` to `stage_title/desc` and update to call new executor methods. Update docstrings.

- [ ] **Refine `_finalize_successful_publish` in `AllegroScraper`:**
    - [x] Explicitly clear `title_new` and `desc_new` in the database.
    - [x] Ensure `published = True` is set.
    - [x] Save the database (before calling `read_offer_details`).

- [ ] **Update `_evaluate_template` in `AllegroScraper`:**
    - [x] Expand context dictionary with more `OfferData` fields (e.g., `price`, `views`) by using `OfferData.model_fields.keys()`.

- [ ] **Review `offer_id` extraction:**
    - [x] Keep current `offer_id` extraction for MVP but retain TODO (expanded TODO comment).

- [ ] **Documentation and Cleanup:**
    - [ ] Update docstrings for modified/new methods.
    - [ ] Update `README.md` for CLI behavior changes.
    - [ ] Keep `CHANGELOG.md` updated.
    - [ ] Mark items in `TODO.md` and `PLAN.md` as completed.

- [ ] **Testing:**
    - [ ] Update existing tests.
    - [ ] Add new tests for `stage_offer_details` and other changes.
    - [ ] Ensure all tests pass.

- [ ] **Final Review and Submission:**
    - [ ] Perform a final review of all changes.
    - [ ] Verify application functionality.
    - [ ] Submit.
