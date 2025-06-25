1.  **Project Setup and Initial File Creation:**
    *   Create `PLAN.md` for the detailed plan.
    *   Create `TODO.md` for the checklist version of the plan.
    *   Create `CHANGELOG.md` to track changes.

2.  **Analyze `ensure_debug_chrome` function:**
    *   Investigate the `tempfile.mkdtemp()` call and the unused `temp_dir` variable.
    *   If `temp_dir` is indeed unused and not part of a planned feature, remove the `tempfile.mkdtemp()` call to simplify the function.
    *   *Decision:* For MVP, keep `CHROME_PATH` hardcoded but add a prominent log/documentation note about it if detection/launch fails. Configurable paths are a v1.x feature.

3.  **Refactor `fetch_offers` and `refresh_offers` in `AllegroScraper`:**
    *   **Goal:** Reduce code duplication and clarify roles. `refresh_offers` is more comprehensive.
    *   **Proposal:**
        *   Modify `refresh_offers` to optionally accept a `reset_pending_changes: bool` parameter (defaulting to `False`).
        *   When `reset_pending_changes` is `True`, `refresh_offers` will mimic the reset behavior currently in `fetch_offers` (clearing `title_new`, `desc_new`, `published` for existing offers).
        *   The core logic of iterating pages and processing cards will primarily reside in `refresh_offers` (or a shared helper).
        *   `fetch_offers` will become a simpler method that calls `refresh_offers` with `reset_pending_changes=self.reset`.
        *   Ensure that `refresh_offers` correctly handles the logic for fetching descriptions for new offers or existing offers that are missing descriptions (currently, it calls `self.read_offer_details`).
    *   Update calls to these methods in `ScrapeExecutor` if their signatures change (though `fetch_offers` in `AllegroScraper` might keep its signature and internally call the modified `refresh_offers`).

4.  **Clarify `set-title`/`set-desc` and `publish_offer_details` workflow:**
    *   **Current:** `set-title`/`set-desc` CLI commands call `ScrapeExecutor.execute_set_title/desc` which calls `AllegroScraper.publish_offer_details` with only one field. `publish_offer_details` seems to:
        1.  Update the local `title_new`/`desc_new` in the `OfferData` model *with the evaluated content*.
        2.  Attempt to publish this one change to the website.
    *   **Problem:**
        *   Storing evaluated content in `title_new`/`desc_new` means the original template/intent is lost from the DB after the first attempt.
        *   The commands `set-title`/`set-desc` imply "setting" a value locally for later publishing, but they trigger an immediate publish attempt for that single field.
    *   **Proposal for MVP (Focus on clear, distinct actions):**
        *   **`AllegroScraper.stage_offer_details(offer_id: str, new_title_template: str | None = None, new_desc_template: str | None = None)`:**
            *   This new method will be responsible *only* for updating `offer.title_new` or `offer.desc_new` in the database with the provided *template strings*.
            *   It will *not* evaluate templates and *not* interact with Selenium.
            *   It will set `offer.published = False`.
        *   **`VolanteCLI.set_title(offer_id, new_title_template)` and `VolanteCLI.set_desc(offer_id, new_desc_template)`:**
            *   These CLI commands will now call `ScrapeExecutor.execute_stage_title/desc` which in turn call `AllegroScraper.stage_offer_details`.
        *   **`AllegroScraper.publish_offer_details(offer_id: str)` (Modified):**
            *   This method will now *only* handle the publishing of *already staged* changes.
            *   It will read `offer.title_new` and `offer.desc_new` (which contain templates).
            *   It will call `_prepare_title_and_desc_for_publish` (which evaluates templates from `offer.title_new` and `offer.desc_new` against `offer.title` and `offer.desc`).
            *   It will then proceed with Selenium interactions to publish.
            *   The arguments `new_title: str | None = None, new_desc: str | None = None` will be removed from `publish_offer_details`.
        *   **`ScrapeExecutor.execute_set_title` and `execute_set_desc` will be renamed** to `execute_stage_title` and `execute_stage_desc`.
        *   **`ScrapeExecutor.execute_publish(offer_id)` and `execute_publish_all()`** will continue to call the modified `AllegroScraper.publish_offer_details(offer_id)`.
    *   This makes a clearer separation: `set-*` commands stage changes locally, `publish*` commands push staged changes.

5.  **Refine `_finalize_successful_publish` in `AllegroScraper`:**
    *   After a successful publish and the call to `self.read_offer_details(offer_id)` (which updates `offer.desc` and potentially other fields from the live site):
        *   Explicitly set `self.db.data[offer_link_key].title_new = ""`
        *   Explicitly set `self.db.data[offer_link_key].desc_new = ""`
        *   Ensure `self.db.data[offer_link_key].published = True` is set.
        *   Save the database.
    *   This ensures that pending changes are clearly marked as resolved.

6.  **Update `_evaluate_template` in `AllegroScraper`:**
    *   Modify the `context` dictionary to include all fields from the `OfferData` model if they are intended to be available as placeholders (e.g., `price`, `views`, `offer_id`, `listing_date`).
    *   The `offer` argument should ideally be an `OfferData` instance or its `model_dump()` result. Currently, it's typed as `dict`. This is acceptable for MVP but ensure all relevant fields are passed.

7.  **Review `offer_id` extraction:**
    *   In `_extract_offer_card_data`, the line `offer_id = offer_link.split("/")[-1]` has a TODO.
    *   For MVP, if this is working, leave as is but ensure the TODO comment remains prominent. A more robust solution (e.g., regex, more specific element attribute) can be for v1.x.

8.  **Documentation and Cleanup:**
    *   Update docstrings for modified methods and classes.
    *   Ensure comments are relevant.
    *   Update `README.md` if command behavior changes significantly (e.g., `set-title` no longer auto-publishes).
    *   Update `PLAN.md` and `TODO.md` as steps are completed.
    *   Record all significant changes in `CHANGELOG.md`.

9.  **Testing:**
    *   Update existing tests to reflect changes in method signatures and behavior.
    *   Add new tests for any new methods (e.g., `stage_offer_details`).
    *   Ensure all tests pass.

10. **Final Review and Submission:**
    *   Review all changes.
    *   Ensure the application works as expected.
    *   Submit the changes with a descriptive commit message.
