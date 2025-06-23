# Volante Lokalnie

A modern Python CLI tool for managing offers on Allegro Lokalnie, providing automation for common tasks like bulk updating listings and managing offer descriptions.

## 🚀 TLDR

```bash
uv pip install git+https://github.com/twardoch/volante_lokalnie/
python -m volante_lokalnie --help
```

## 🎯 Purpose & Background

Allegro Lokalnie is a popular platform for local sales, but managing a large number of listings, especially for semi-professional sellers or those frequently rotating items, can become a significant time sink. Standard web interfaces are designed for manual, one-by-one operations. `volante_lokalnie` (meaning "flying locally" or "steering wheel locally") aims to provide a more efficient, programmatic way to interact with your Allegro Lokalnie offers.

This tool was born out of the need to:
- **Automate Repetitive Tasks:** Such as updating prices, descriptions, or titles across multiple offers based on templates or external data.
- **Maintain Local Offer Data:** Keep a local, editable copy of offer details, allowing for offline editing and versioning if desired.
- **Track Offer Performance:** Systematically fetch and store offer statistics like views.
- **Reduce Manual Effort:** Minimize clicks and page navigation through a powerful command-line interface.
- **Enable Scripting:** Allow integration of Allegro Lokalnie management into larger scripts or workflows.

It leverages web scraping techniques to interact with the Allegro Lokalnie website, simulating browser actions to perform tasks that are not available via an official API for Allegro Lokalnie.

**Disclaimer:** This tool relies on web scraping, which can be fragile and subject to break if the website structure changes. Use it responsibly and be aware of Allegro Lokalnie's terms of service. The tool includes delays to mimic human behavior but automating interactions with websites should always be done with caution.

## ✨ Features

- **Modern Python Stack:**
  - Python 3.10+
  - PEP 621 packaging with `pyproject.toml` and [Hatch](https://hatch.pypa.io/).
  - Formatted with [Ruff](https://astral.sh/ruff) and type-checked with [MyPy](http://mypy-lang.org/).
  - Fast dependency management with [uv](https://github.com/astral-sh/uv).
  - Comprehensive (and growing) test suite using [Pytest](https://pytest.org/).
  - CI/CD with GitHub Actions for linting, testing, and releases.
  - Versioning based on Git tags via `hatch-vcs`.

- **Core Offer Management:**
  - `fetch`: Retrieve all active offers and store them locally.
  - `read`: Get detailed description for a specific offer.
  - `set-title`: Update an offer's title. Supports simple string templates.
  - `set-desc`: Update an offer's description. Supports simple string templates.
  - `read-all`: Refresh data for all offers, including their full descriptions.
  - `publish`: Push pending local changes (title/description) for a specific offer to Allegro Lokalnie.
  - `publish-all`: Push all pending local changes for all modified offers.

- **Local Data Store:**
  - Offers are stored in a human-readable TOML file (`volante_lokalnie.toml`) in the same directory as the script, allowing for easy inspection or manual edits if necessary.
  - Tracks original and new (pending) titles and descriptions.

- **Automation & Convenience:**
  - **Templating:** Use placeholders like `{title}`, `{desc}`, `{price}`, `{views}` in `set-title` and `set_desc` commands to dynamically generate content. (Note: price/views are read-only from the site, but can be used in templates if you have them from other sources).
  - **Dry-run Mode (`--dryrun`):** See what changes would be made without actually performing them.
  - **Verbose Mode (`--verbose`):** Get detailed logging output for debugging.
  - **Reset Mode (`--reset` with `fetch`):** Clear pending local changes (`title_new`, `desc_new`) when fetching offers.

## 📦 Installation

```bash
Prerequisites:
- Python 3.10+
- `uv` (recommended) or `pip`
- A running instance of Google Chrome (the tool will attempt to connect to it in debug mode).

```bash
# Using uv (recommended for speed)
uv pip install git+https://github.com/twardoch/volante_lokalnie.git

# Using pip
pip install git+https://github.com/twardoch/volante_lokalnie.git
```

After installation, you can run the tool using `python -m volante_lokalnie` or simply `volante` if the script is installed to your PATH.

```bash
volante --help
# or
python -m volante_lokalnie --help
```

**Initial Setup - Chrome Debugging:**
The tool uses Selenium to control a Chrome browser. It expects Chrome to be running with remote debugging enabled on port 9222.
- On macOS, it will attempt to launch Chrome with the correct flags if it's not already running in debug mode at `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`.
- On other systems, or if your Chrome is elsewhere, you might need to launch Chrome manually first:
  ```bash
  # Example for Linux
  google-chrome --remote-debugging-port=9222 --no-first-run --no-default-browser-check
  # Example for Windows
  "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --no-first-run --no-default-browser-check
  ```
Modify the `CHROME_PATH` constant in the script if your Chrome executable is in a non-standard location and auto-detection fails.

## 🔧 Usage

The tool operates via commands and sub-commands. All commands interact with a local data file named `volante_lokalnie.toml` (created in the directory where you run the script, or where the script itself is located if run directly).

### Global Options

These options can be used with any command:
- `--verbose`: Enables detailed debug logging. Useful for troubleshooting.
  ```bash
  volante --verbose fetch
  ```
- `--dryrun`: Simulates the command without making any actual changes to the website or the local database. Useful for testing.
  ```bash
  volante --dryrun publish-all
  ```
- `--reset`: Used with the `fetch` command. When fetching offers, if this flag is active, any pending local changes (new titles or descriptions stored in `title_new` or `desc_new` fields in the database) for existing offers will be cleared. Their `published` status will also be reset to `False`.
  ```bash
  volante --reset fetch
  ```

### Core Commands

**1. `fetch`**
   Fetches all your active offers from Allegro Lokalnie and stores their basic information (title, price, views, etc.) in the local `volante_lokalnie.toml` database. If the database file already exists, this command will update existing entries and add new ones. Offers no longer found online will be removed from the local database.
   ```bash
   volante fetch
   ```
   If you use `--reset` with `fetch`, any local un-published changes (`title_new`, `desc_new`) for offers that are re-fetched will be discarded.

**2. `read <OFFER_ID>`**
   Reads the full description for a specific offer from its Allegro Lokalnie page and stores it in the `desc` field in the local database. The `OFFER_ID` is the numerical ID from the offer's URL.
   ```bash
   volante read 12345678
   ```

**3. `read-all`**
   Refreshes the list of active offers (like `fetch`) and then ensures that the full description for every active offer is present in the local database. If a description is missing for an offer, it will be fetched.
   ```bash
   volante read-all
   ```

**4. `set-title <OFFER_ID> "<NEW_TITLE_OR_TEMPLATE>"`**
   Sets a new title for the specified offer. This new title is stored locally in the `title_new` field of the database and will be pushed to Allegro Lokalnie when `publish` or `publish-all` is used.
   - The `<NEW_TITLE_OR_TEMPLATE>` can be a simple string or include placeholders like `{title}` (original title), `{price}`, `{views}`.
   ```bash
   volante set-title 12345678 "Awesome New Title - {price} PLN"
   # To use the existing title_new from the database (e.g., if set manually in TOML):
   volante set-title 12345678
   ```
   If no new title string is provided, it attempts to use the value already in `title_new` from the database.

**5. `set-desc <OFFER_ID> "<NEW_DESC_OR_TEMPLATE>"`**
   Sets a new description for the specified offer. Stored locally in `desc_new`.
   - Supports placeholders like `{desc}` (original description), `{title}`, etc.
   ```bash
   volante set-desc 12345678 "This is a new description. Original was: {desc}"
   # To use the existing desc_new from the database:
   volante set-desc 12345678
   ```

**6. `publish <OFFER_ID>`**
   Publishes pending local changes (from `title_new` and/or `desc_new`) for the specified offer to Allegro Lokalnie. After successful publishing, the `published` flag is set to `True` in the database, and the main `title` and `desc` fields are updated with the new content.
   ```bash
   volante publish 12345678
   ```

**7. `publish-all`**
   Identifies all offers in the local database that have pending changes (`title_new` or `desc_new` is set and `published` is `False`) and publishes them one by one.
   ```bash
   volante publish-all
   ```

### Data Storage: `volante_lokalnie.toml`

- The tool stores all offer data in a file named `volante_lokalnie.toml`. This file is typically created in the directory where you execute the `volante` command.
- The file uses the TOML format, which is human-readable. You can inspect or even carefully edit this file.
- Each offer is a key-value map, where the key is the offer's URL on Allegro Lokalnie.
- Key fields for each offer include:
  - `offer_id`: The unique numerical ID.
  - `title`: The current title on Allegro.
  - `price`, `views`, `listing_date`, `image_url`, `offer_type`: Basic offer info.
  - `desc`: The full description from Allegro (in Markdown format).
  - `title_new`: Your pending new title. Empty if no change is pending or after publishing.
  - `desc_new`: Your pending new description. Empty if no change is pending or after publishing.
  - `published`: `true` if pending changes have been published, `false` otherwise.

## 🛠️ Development

This project uses [Hatch](https://hatch.pypa.io/) for Python project and environment management. Pre-commit hooks are used for code quality.

### Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/twardoch/volante_lokalnie.git
    cd volante_lokalnie
    ```
2.  **Install Hatch:**
    ```bash
    pip install hatch
    # or using uv
    uv pip install hatch
    ```
3.  **Activate development environment:**
    Hatch will automatically create and manage a virtual environment.
    ```bash
    hatch shell
    ```
    This installs all dependencies, including development tools like `pytest`, `ruff`, `mypy`.

### Running Quality Checks

-   **Linting and Formatting (Ruff):**
    ```bash
    hatch run lint:style  # Run ruff check and format check
    hatch run lint:fmt    # Run ruff format (auto-format) and ruff check --fix (auto-fix lint)
    # Individual commands:
    # hatch run ruff check .
    # hatch run ruff format . --respect-gitignore
    ```
-   **Type Checking (MyPy):**
    ```bash
    hatch run lint:typing # Runs mypy
    # or directly:
    # hatch run mypy src tests --config-file pyproject.toml
    ```
-   **Run all linters configured in Hatch:**
    ```bash
    hatch run lint:all
    ```

### Running Tests

-   **Run all tests (Pytest):**
    ```bash
    hatch run test
    ```
-   **Run tests with coverage:**
    ```bash
    hatch run test-cov
    ```
    A coverage report will be generated in `coverage.xml` and printed to the terminal.

### Pre-commit Hooks

The project is set up with pre-commit hooks (Ruff, MyPy, and others) to automatically check and format code before committing.
1.  **Install pre-commit:**
    ```bash
    # If not already installed (typically installed via hatch env)
    # pip install pre-commit
    # uv pip install pre-commit
    ```
2.  **Install the git hooks:**
    ```bash
    pre-commit install
    ```
    Now, the hooks will run automatically on `git commit`. You can also run them manually:
    ```bash
    pre-commit run --all-files
    ```

## 🏛️ Codebase Structure & Technical Overview

-   **`pyproject.toml`**: Defines project metadata, dependencies, and tool configurations (Hatch, Ruff, MyPy, Pytest) according to PEP 621.
-   **`src/volante_lokalnie/`**: Main source code directory.
    -   **`__init__.py`**: Package initializer.
    -   **`__main__.py`**: Main CLI entry point, uses `fire` to expose `VolanteCLI`.
    -   **`volante_lokalnie.py`**: Core logic.
        -   `OfferData(BaseModel)`: Pydantic model for offer data structure and validation.
        -   `OfferDatabase`: Handles loading/saving offer data to/from the TOML file.
        -   `AllegroScraper`: Contains all Selenium-based web scraping logic to interact with Allegro Lokalnie (fetching offers, reading details, publishing changes).
        -   `ScrapeExecutor`: A wrapper that initializes `AllegroScraper` only when an actual scraping command is run, preventing Selenium startup for help messages or simple CLI invocations. It translates CLI commands into calls to `AllegroScraper`.
        -   `VolanteCLI`: Defines the command-line interface using `python-fire`. Methods in this class become CLI commands.
    -   **`__version__.py`**: Version information, managed by `hatch-vcs`.
-   **`tests/`**: Contains Pytest tests.
    -   `test_package.py`: Basic package tests.
    -   `test_offer_data.py`: Tests for the `OfferData` model.
    -   `test_offer_database.py`: Tests for `OfferDatabase`.
    -   `test_allegro_scraper.py`: Tests for `AllegroScraper` (especially helper methods; Selenium interaction tests are more complex).
    -   `test_cli.py`: Tests for the CLI layer (`VolanteCLI`, `ScrapeExecutor`).
-   **`.github/workflows/`**: GitHub Actions workflows for CI (testing, linting, building) and CD (releasing to PyPI).
-   **`.pre-commit-config.yaml`**: Configuration for pre-commit hooks.

### Data Flow Example: Publishing a Change

1.  User runs `volante set-title <ID> "New Title"`.
2.  `VolanteCLI.set_title()` is called.
3.  It instantiates `ScrapeExecutor`.
4.  `ScrapeExecutor.execute_set_title()` is called.
    -   This method internally uses `AllegroScraper.publish_offer_details()` but only to set the title *locally in the database* if `publish_offer_details` is smart enough, or it updates `db.data[offer_key].title_new = "New Title"` and `db.save()`. *Correction based on current code: `set-title` calls `publish_offer_details` which directly tries to publish if not dryrun, after updating the local `title_new` field. This is slightly different from just staging it.* The `publish_offer_details` method is responsible for both staging the change (by setting `title_new` or `desc_new` on the OfferData model) and then performing the web submission.
5.  User runs `volante publish <ID>`.
6.  `VolanteCLI.publish()` calls `ScrapeExecutor.execute_publish()`.
7.  `ScrapeExecutor.execute_publish()` calls `AllegroScraper.publish_offer_details()`.
8.  `AllegroScraper.publish_offer_details()`:
    a.  Navigates to the offer edit page using Selenium.
    b.  Retrieves `title_new` and `desc_new` from the `OfferData` model for that offer.
    c.  Evaluates any templates in them.
    d.  Fills the title and/or description fields on the web page.
    e.  Navigates through the multi-step submission process (description form, details form, highlight page, summary page).
    f.  If successful, updates the local `OfferData` (e.g., sets `published=True`, copies `title_new` to `title`) and calls `read_offer_details()` to refresh data from the site.
    g.  Saves the database.

### Web Scraping Approach

-   **Selenium:** The primary tool for browser automation. `volante_lokalnie` controls a Chrome browser instance.
-   **Debugging Port:** It connects to Chrome via its remote debugging port (default 9222). This allows interaction with an existing browser session where the user is already logged in.
-   **Login:** The script requires the user to be manually logged into Allegro Lokalnie in the controlled browser instance. It includes a step to wait for the user to log in and navigate to the active offers page.
-   **Selectors:** Uses CSS selectors (and occasionally XPath) to find elements on web pages. These can be brittle if the website structure changes.
-   **Human-like Delays:** Small random delays (`human_delay()`) are inserted between actions to reduce the chance of being flagged as a bot.
-   **HTML Parsing:** `BeautifulSoup4` is used to parse page content obtained from Selenium.
-   **Markdown Conversion:** `html2text` is used to convert offer descriptions from HTML to Markdown for local storage.

## 🤝 Contributing

Contributions are welcome! Whether it's bug reports, feature suggestions, documentation improvements, or code contributions, please feel free to open an issue or a pull request.

### Contribution Workflow

1.  **Fork the repository** on GitHub.
2.  **Clone your fork** locally: `git clone https://github.com/YOUR_USERNAME/volante_lokalnie.git`
3.  **Create a new branch** for your changes: `git checkout -b feature/your-feature-name` or `bugfix/issue-number`.
4.  **Set up the development environment** as described in the "Development" section (using Hatch and pre-commit).
5.  **Make your changes.** Ensure you add or update tests for your changes.
6.  **Run linters and tests:** `hatch run lint:all` and `hatch run test-cov`.
7.  **Commit your changes:** `git commit -m "Your descriptive commit message"`
8.  **Push to your fork:** `git push origin feature/your-feature-name`
9.  **Open a Pull Request** from your fork's branch to the `main` branch of the original `twardoch/volante_lokalnie` repository. Provide a clear description of your changes.

### Coding Standards

-   Follow PEP 8 guidelines (Ruff helps enforce this).
-   Write clear, readable code with type hints.
-   Ensure MyPy passes without errors.
-   Add unit tests for new functionality.
-   Keep documentation (README, docstrings) updated.

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details.

## 📝 Author

Adam Twardoch ([@twardoch](https://github.com/twardoch)) - (adam+github@twardoch.com)

## 🔗 Links

- [Documentation](https://github.com/twardoch/volante_lokalnie#readme) (You are here)
- [Issue Tracker](https://github.com/twardoch/volante_lokalnie/issues)
- [Source Code](https://github.com/twardoch/volante_lokalnie)