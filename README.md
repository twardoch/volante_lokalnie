# 



## Features

- Modern Python packaging with PEP 621 compliance
- Type hints and runtime type checking
- Comprehensive test suite and documentation
- CI/CD ready configuration

## Installation

```bash
pip install volante_lokalnie
```

## Usage

```python
import volante_lokalnie
```

## Development

## 🔧 Usage

### Setup Development Environment

```bash
# Install hatch if you haven't already
pip install hatch

# Create and activate development environment
hatch shell

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

This project uses modern Python tooling including [UV](https://docs.astral.sh/uv/) for fast dependency management and [Hatch](https://hatch.pypa.io/) for project management. The build system supports git-tag-based semantic versioning and multiplatform binary distribution.

### Quick Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/twardoch/volante_lokalnie.git
    cd volante_lokalnie
    ```

2.  **Install UV (recommended):**
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

3.  **Setup development environment:**
    ```bash
    # Install all dependencies
    uv pip install ".[dev,test,build]"
    
    # Or use the convenience Makefile
    make dev-setup
    ```

### Build System

The project includes a comprehensive build system with convenient scripts:

#### Using the Build Script

```bash
# Clean build artifacts
python scripts/build.py clean

# Run linting checks
python scripts/build.py lint

# Run tests
python scripts/build.py test

# Build package distributions
python scripts/build.py build

# Create binary distributions
python scripts/build.py binary

# Run all checks
python scripts/build.py all
```

#### Using the Makefile

```bash
# Show all available commands
make help

# Setup development environment
make dev-setup

# Run all checks and build
make all

# Run tests with coverage
make dev-test

# Create releases
make release-patch    # 1.0.0 -> 1.0.1
make release-minor    # 1.0.0 -> 1.1.0
make release-major    # 1.0.0 -> 2.0.0
make release-dry-run  # Test without actually releasing
```

### Release Process

The project uses git-tag-based semantic versioning with automated CI/CD:

#### Manual Release

```bash
# Create a patch release (1.0.0 -> 1.0.1)
./scripts/release.sh -t patch

# Create a minor release (1.0.0 -> 1.1.0)
./scripts/release.sh -t minor -m "Add new features"

# Create a major release (1.0.0 -> 2.0.0)
./scripts/release.sh -t major -m "Breaking changes"

# Custom version
./scripts/release.sh -v 1.2.3 -m "Custom release"
```

#### Automated CI/CD

**⚠️ Note for Repository Maintainers**: GitHub Actions workflows need to be manually activated. See [GITHUB_ACTIONS_SETUP.md](GITHUB_ACTIONS_SETUP.md) for setup instructions.

1. **Push to main branch**: Runs tests, linting, and builds
2. **Create git tag**: `git tag v1.2.3 && git push origin v1.2.3`
3. **GitHub Actions automatically**:
   - Runs comprehensive tests across Python 3.10, 3.11, 3.12
   - Tests on Linux, Windows, and macOS
   - Creates multiplatform binaries (Linux, Windows, macOS)
   - Publishes to PyPI
   - Creates GitHub release with binaries attached

**Quick Setup for Maintainers**:
```bash
# Copy workflow files
cp .github/workflows-templates/*.yml .github/workflows/

# Configure PYPI_TOKEN secret in repository settings
# Then test with a pre-release tag
git tag v1.0.3-rc1 && git push origin v1.0.3-rc1
```

### Binary Distribution

The project creates standalone binaries for easy installation:

```bash
# Create binary for current platform
python scripts/build.py binary

# Create binary for specific platform
python scripts/build.py binary --target-os linux
python scripts/build.py binary --target-os windows
python scripts/build.py binary --target-os macos
```

Users can download binaries from GitHub releases:
- **Linux**: `volante-lokalnie-linux`
- **Windows**: `volante-lokalnie-windows.exe`
- **macOS**: `volante-lokalnie-macos`

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

## License

MIT License 