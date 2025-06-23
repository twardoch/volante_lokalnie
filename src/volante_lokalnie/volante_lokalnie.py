#!/usr/bin/env -S uv run
# this_file: src/volante_lokalnie/volante_lokalnnie.py
# The script implements a Fire CLI with commands to fetch, read, and update offers.
# It uses a JSON file (with the same basename as the script) as a simple backend database.
#
# The CLI commands and their purposes are:
#   • list: fetch offers from the website and store in database.
#   • read: read an offer's description from its detail page.
#   • set-title: update the offer title on the website (if needed).
#   • set-desc: update the offer description on the website (if needed).
#   • read-all: refresh the list of offers along with their detailed descriptions.
#   • publish-all: update offers from the database by applying pending title/description edits.

import logging
import random
import socket
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Annotated as Doc
from typing import cast
from urllib.parse import urljoin

import fire
import html2text
import psutil
import tomli
import tomli_w
from bs4 import BeautifulSoup, Tag
from pydantic import BaseModel
from rich.logging import RichHandler
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# ------------------------------------------------------------------------------
# Setup logging using Rich
# ------------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,  # Default to INFO level
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[RichHandler(rich_tracebacks=True)],
)
logger = logging.getLogger("allegro_scraper")

# ------------------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------------------
ALLEGRO_URL = "https://allegrolokalnie.pl/konto/oferty/aktywne"
BASE_URL = "https://allegrolokalnie.pl"
CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
DEBUG_PORT = 9222


# ------------------------------------------------------------------------------
# Utility Functions
# ------------------------------------------------------------------------------
def is_port_in_use(port: int) -> bool:
    """Check if a port is in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0


def find_chrome_debug_process() -> psutil.Process | None:
    """Find a Chrome process running with remote debugging enabled."""
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if proc.info["cmdline"]:
                cmdline = " ".join(proc.info["cmdline"])
                if (
                    CHROME_PATH in cmdline
                    and f"--remote-debugging-port={DEBUG_PORT}" in cmdline
                ):
                    return proc
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return None


def ensure_debug_chrome() -> None:
    """Ensure Chrome is running with remote debugging enabled."""
    if is_port_in_use(DEBUG_PORT):
        logger.debug("[yellow]Chrome debugging port already in use[/yellow]")
        return
    if find_chrome_debug_process():
        logger.debug("[yellow]Chrome debugging process already running[/yellow]")
        return
    logger.debug("Launching Chrome with remote debugging enabled...")
    tempfile.mkdtemp()
    subprocess.Popen(
        [
            CHROME_PATH,
            f"--remote-debugging-port={DEBUG_PORT}",
            "--no-first-run",
            "--no-default-browser-check",
            # f"--user-data-dir={temp_dir}",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(10):
        if is_port_in_use(DEBUG_PORT):
            logger.debug("[green]Chrome started successfully[/green]")
            return
        time.sleep(1)
    raise RuntimeError("[red]Failed to start Chrome with debugging enabled[/red]")


def human_delay(min_seconds: float = 1.0, max_seconds: float = 3.0) -> None:
    """Pause execution for a random delay to simulate human behavior."""
    delay = random.uniform(min_seconds, max_seconds)
    logger.debug(f"Delaying for {delay:.2f} seconds to simulate human behavior.")
    time.sleep(delay)


# ------------------------------------------------------------------------------
# Pydantic Model for Offer Data
# ------------------------------------------------------------------------------
class OfferData(BaseModel):
    """Data structure for offer information."""

    title: str
    price: float
    views: int
    listing_date: str  # ISO format string
    image_url: str
    offer_type: str
    offer_id: str
    title_new: str = ""
    desc: str = ""
    desc_new: str = ""
    published: bool = False  # Track if changes have been published


# ------------------------------------------------------------------------------
# Offer Database
# ------------------------------------------------------------------------------
class OfferDatabase:
    """Handles reading and writing offer data to disk.

    Offers are stored in a TOML file whose name is derived from the current script.
    Uses OfferData models internally, converting to/from dicts only for TOML I/O.
    """

    def __init__(self, file_path: Path):
        """Initialize the database with a TOML file path."""
        self.file_path: Path = file_path.with_suffix(".toml")
        self.data: dict[str, OfferData] = {}
        self.load()

    def _sort_data(self) -> None:
        """Sort the data dictionary by listing date in descending order (newest first)."""
        sorted_items = sorted(
            self.data.items(),
            key=lambda x: x[1].listing_date,
            reverse=True,  # Descending order
        )
        # Rebuild the dictionary with sorted items
        self.data = dict(sorted_items)

    def load(self) -> None:
        """Load data from a TOML file and convert to OfferData models."""
        if not self.file_path.exists():
            logger.warning(
                f"[DB] Database {self.file_path} not found, starting empty."
            )
            self.data = {}
            return

        try:
            with open(self.file_path, "rb") as f:
                raw_data = tomli.load(f)
            # Convert each dict to an OfferData model
            self.data = {
                url: OfferData.model_validate(offer_dict)
                for url, offer_dict in raw_data.items()
            }
            self._sort_data()
            logger.debug(
                f"[DB] Loaded {len(self.data)} offers from {self.file_path}"
            )
        except FileNotFoundError: # Should be caught by exists() check, but good practice
            logger.warning(
                f"[DB] Database {self.file_path} not found, starting empty."
            )
            self.data = {}
        except (tomli.TOMLDecodeError, ValueError) as e: # ValueError for Pydantic validation
            logger.error(
                f"[DB] Failed to parse database {self.file_path}: {e}. Starting with an empty database."
            )
            self.data = {}
        except Exception as e: # Catch-all for other unexpected errors
            import traceback
            logger.error(
                f"[DB] Unexpected error loading database: {e}. Traceback:\n{traceback.format_exc()}"
            )
            raise

    def save(self) -> None:
        """Convert OfferData models to dicts and save to TOML file."""
        try:
            self._sort_data()
            # Convert OfferData models to dicts for TOML serialization
            data_dict = {url: offer.model_dump() for url, offer in self.data.items()}
            with open(self.file_path, "wb") as f:
                tomli_w.dump(data_dict, f)
            logger.debug(f"[DB] Saved {len(self.data)} offers to {self.file_path}")
        except OSError as e:
            logger.error(f"[DB] File I/O error saving database to {self.file_path}: {e}")
        except Exception as e: # Catch-all for other unexpected errors like tomli_w issues
            logger.error(f"[DB] Unexpected error saving database: {e}")

    def get_offer(self, offer_id: str) -> OfferData | None:
        """Retrieve an offer by its offer_id."""
        for _url, offer in self.data.items():
            if offer.offer_id == offer_id:
                return offer
        return None


# ------------------------------------------------------------------------------
# Allegro Scraper
# ------------------------------------------------------------------------------
class AllegroScraper:
    """Interacts with the Allegrolokalnie website to fetch and update offers.

    This class defers browser initialization until a command is invoked,
    in order to avoid launching a browser during help display or other non-action commands.

    Key methods:
    - fetch_offers: retrieves offer cards from paginated listings.
    - read_offer_details: reads and updates an offer's detailed description.
    - publish_offer_details: updates title and description using the website's edit pages.
    - refresh_offers: merges the current list with new arrivals while preserving details.
    """

    def __init__(
        self,
        db: OfferDatabase,
        verbose: bool = False,
        dryrun: bool = False,
        reset: bool = False,
    ):
        self.db = db
        self.driver: webdriver.Chrome | None = None  # Browser not initialized yet
        self.verbose = verbose
        self.dryrun = dryrun
        self.reset = reset

        # Set logging level based on verbose flag
        if verbose:
            logger.setLevel(logging.DEBUG)
            logger.debug("[Scraper] Debug logging enabled")
        else:
            logger.setLevel(logging.INFO)

    @staticmethod
    def _setup_driver() -> webdriver.Chrome:
        """Set up and return a Chrome WebDriver attached to the debugger."""
        options = webdriver.ChromeOptions()
        options.debugger_address = f"127.0.0.1:{DEBUG_PORT}"
        try:
            logger.debug("Initializing Chrome WebDriver with debugger...")
            return webdriver.Chrome(options=options)
        except WebDriverException as e:
            logger.error(f"Failed to connect to Chrome: {e}")
            raise RuntimeError("Could not connect to Chrome debugging instance") from e

    def _ensure_driver(self) -> None:
        """Ensure that the Chrome WebDriver is initialized."""
        if self.driver is None:
            ensure_debug_chrome()
            self.driver = self._setup_driver()

    def _wait_for_login(self) -> None:
        """Wait for user to manually log in."""
        logger.info(
            """
[Manual Login Required]
1. Please log into Allegro Lokalnie in the browser window
2. Navigate to: https://allegrolokalnie.pl/konto/oferty/aktywne
3. The script will continue once you're logged in and on the offers page
"""
        )

        max_wait = 300  # 5 minutes timeout
        check_interval = 2  # Check every 2 seconds
        start_time = time.time()

        while time.time() - start_time < max_wait:
            try:
                if "konto/oferty/aktywne" not in self.driver.current_url:
                    logger.info("Waiting for you to navigate to the offers page...")
                    time.sleep(check_interval)
                    continue

                title = self.driver.find_element(
                    By.CLASS_NAME, "page-header__page-title"
                )
                if "Moje aktywne ogłoszenia" in title.text:
                    logger.info("[green]Successfully detected logged-in state!")
                    return
            except Exception:
                pass
            time.sleep(check_interval)

        raise TimeoutError("Login timeout exceeded (5 minutes). Please try again.")

    def fetch_offers(self) -> None:
        """Fetch offer data from the website and update the local database."""
        self._ensure_driver()
        logger.debug("Starting to fetch offers from website...")
        self.driver.get(ALLEGRO_URL)

        # Add manual login wait here
        self._wait_for_login()

        # Continue with existing code...
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "my-offer-card"))
        )
        max_pages = self._get_max_pages()
        # This dictionary will hold all offers found in the current scrape session.
        # It will become the new self.db.data at the end.
        live_offers_on_site: dict[str, OfferData] = {}

        for page_num in range(1, max_pages + 1):
            logger.info(f"[Site] Processing page {page_num} of {max_pages}...")

            # Navigate to the correct page if not the first page (already on page 1)
            if page_num > 1:
                self.driver.get(f"{ALLEGRO_URL}?page={page_num}")
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "my-offer-card"))
                )
                human_delay()

            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            offer_cards_on_page = soup.find_all("div", class_="my-offer-card")

            if not offer_cards_on_page:
                logger.warning(f"[Site] No offers found on page {page_num}. This might be the end or an issue.")
                break # Stop if a page is empty

            for card_html in offer_cards_on_page:
                # _extract_offer_card_data parses a single card and returns OfferData
                # It should not interact with the database.
                parsed_result = self._extract_offer_card_data(card_html)

                if parsed_result:
                    offer_link_key, fresh_data_from_card = parsed_result

                    # Check if this offer was already in our database from a previous run
                    if offer_link_key in self.db.data:
                        # It exists. We update the existing OfferData model with fresh basic info.
                        # Custom fields (desc, desc_new, title_new, published) are preserved unless reset.
                        existing_model_in_db = self.db.data[offer_link_key]

                        # Update core fields from the newly scraped card data
                        existing_model_in_db.title = fresh_data_from_card.title
                        existing_model_in_db.price = fresh_data_from_card.price
                        existing_model_in_db.views = fresh_data_from_card.views
                        existing_model_in_db.listing_date = fresh_data_from_card.listing_date
                        existing_model_in_db.image_url = fresh_data_from_card.image_url
                        existing_model_in_db.offer_type = fresh_data_from_card.offer_type
                        # offer_id should be the same.

                        if self.reset:
                            logger.debug(f"[DB] Resetting editable fields for offer ID {existing_model_in_db.offer_id}")
                            existing_model_in_db.title_new = ""
                            # Note: existing_model_in_db.desc (original description) is NOT reset here.
                            # Fetching with --reset clears pending changes (title_new, desc_new)
                            # and published status. It does not erase known original descriptions.
                            existing_model_in_db.desc_new = ""
                            existing_model_in_db.published = False

                        live_offers_on_site[offer_link_key] = existing_model_in_db
                    else:
                        # This is a new offer not seen before.
                        # Ensure 'published' and editable fields are default/empty.
                        fresh_data_from_card.published = False
                        fresh_data_from_card.title_new = ""
                        fresh_data_from_card.desc = "" # Original description is empty until read by `read` or `read_all`
                        fresh_data_from_card.desc_new = ""
                        live_offers_on_site[offer_link_key] = fresh_data_from_card

            logger.debug(f"[Site] Processed {len(offer_cards_on_page)} cards on page {page_num}. Total live offers found so far: {len(live_offers_on_site)}")

        # After processing all pages, replace the database content with the live offers found.
        # Offers that were in self.db.data but not in live_offers_on_site are effectively removed (no longer active).
        self.db.data = live_offers_on_site
        self.db.save()

        logger.info(
            f"[Site] Fetch operation complete. Database updated with {len(self.db.data)} currently active offers."
        )

    def _extract_offer_card_data(self, card: Tag) -> tuple[str, OfferData] | None:
        """Extracts offer data from a single offer card HTML element. Does not interact with DB."""
        try:
            if self.verbose:
                logger.debug("[Scraper] Starting to extract offer data from card")

            link_elem = card.select_one("a[itemprop='url']")
            if not link_elem or not isinstance(link_elem.get("href"), str):
                logger.warning("Offer card missing link element; skipping.")
                return None

            href = cast(str, link_elem["href"])
            offer_link = urljoin(BASE_URL, href)
            offer_id = offer_link.split("/")[-1] # TODO: ensure this is robust

            if not offer_id:
                logger.warning(f"Could not extract offer_id from link {offer_link}; skipping.")
                return None

            if self.verbose:
                logger.debug(f"[Scraper] Processing card for offer {offer_id} at {offer_link}")

            title_elem = card.select_one(".my-offer-card__title a")
            title = title_elem.text.strip() if title_elem else "Unknown Title"

            price_elem = card.select_one("span[itemprop='price']")
            price_text = price_elem.text.strip() if price_elem else "0"
            try:
                price = float(price_text.replace(",", ".").replace("zł", "").strip())
            except ValueError:
                logger.warning(f"Could not parse price '{price_text}' for offer {offer_id}. Defaulting to 0.0.")
                price = 0.0

            views_elem = card.select_one(".m-t-1.m-b-1") # Example selector, might need adjustment
            views_text = views_elem.text if views_elem else "0"
            try:
                views = int("".join(filter(str.isdigit, views_text)))
            except ValueError:
                logger.warning(f"Could not parse views '{views_text}' for offer {offer_id}. Defaulting to 0.")
                views = 0

            date_elem = card.select_one("time[itemprop='startDate']")
            date_str = date_elem.get("datetime") if date_elem else None
            listing_date : str
            if date_str:
                try:
                    listing_date = datetime.fromisoformat(cast(str, date_str).replace("Z", "+00:00")).isoformat()
                except ValueError:
                    logger.warning(f"Could not parse date '{date_str}' for offer {offer_id}. Defaulting to now.")
                    listing_date = datetime.now().isoformat()
            else:
                logger.warning(f"Missing listing date for offer {offer_id}. Defaulting to now.")
                listing_date = datetime.now().isoformat()


            img_elem = card.select_one("img[itemprop='image']")
            image_url = cast(str, img_elem.get("src")) if img_elem else ""

            type_elem = card.select_one("[data-testid^='offer-type-']") # Example selector
            offer_type = type_elem.text.strip() if type_elem else "Unknown"

            if self.verbose:
                logger.debug(
                    f"[Scraper] Successfully extracted data for offer {offer_id}: Title='{title}', Price={price}, Views={views}, Type='{offer_type}'"
                )

            # This method now ONLY returns fresh data. It does not interact with self.db.data.
            # The caller (fetch_offers / refresh_offers) will handle merging.
            return offer_link, OfferData(
                title=title,
                price=price,
                views=views,
                listing_date=listing_date,
                image_url=image_url,
                offer_type=offer_type,
                offer_id=offer_id,
                # desc, title_new, desc_new, published will be set by caller or use defaults
            )

        except Exception as e:
            logger.error(f"Error extracting data from an offer card: {e}")
            if self.verbose:
                logger.exception("[Scraper] Full error details:")
            return None

    def _get_max_pages(self) -> int:
        """Extract the maximum number of pages from the pagination element."""
        try:
            soup = BeautifulSoup(self.driver.page_source, "html.parser")

            # Look for the pagination input element that contains max pages
            page_input = soup.select_one(".pagination__pages input[type='number']")
            if page_input and page_input.get("max"):
                return int(page_input["max"])

            # Fallback: if no pagination input found, we're on the only page
            return 1

        except Exception as e:
            logger.error(f"Error determining max pages: {e}")
            return 1

    def _preprocess_html(self, html: str) -> str:
        """Preprocess HTML before converting to Markdown.

        This handles special cases like:
        - Converting <p class="desc-h2"> to <h2>
        - Converting <p class="desc-p"> to <p>
        - Any other custom HTML preprocessing needed

        Args:
            html: Raw HTML string to preprocess

        Returns:
            Preprocessed HTML string ready for Markdown conversion
        """
        soup = BeautifulSoup(html, "html.parser")

        # Convert p.desc-h2 to h2
        for p in soup.find_all("p", class_="desc-h2"):
            p.name = "h2"
            del p["class"]

        # Clean up p.desc-p (just remove the class)
        for p in soup.find_all("p", class_="desc-p"):
            del p["class"]

        return str(soup)

    def read_offer_details(self, offer_id: str) -> dict | None:
        """Read the description details for a specific offer and update the database.

        The description is converted from HTML to Markdown format before storing.
        Uses multiple strategies to find and extract the description with retries.
        """
        self._ensure_driver()
        offer = self.db.get_offer(offer_id)
        if not offer:
            logger.error(
                f"[Scraper] Offer {offer_id} not in database, run `list_offers` first."
            )
            return None

        try:
            offer_url = next(
                url for url, data in self.db.data.items() if data.offer_id == offer_id
            )
            logger.info(
                f"[Scraper] Reading details for offer {offer_id} from {offer_url}..."
            )

            # Try loading the page up to 3 times
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    self.driver.get(offer_url)
                    human_delay(2.0, 3.0)  # Longer delay for page load

                    # Wait for any of the possible containers to be present
                    containers = [
                        "section.mlc-offer__offer-details",
                        "div.mlc-offer__description",
                        ".ml-text-medium.mlc-offer__description",
                        "#app-root main div.mlc-offer section.ml-normalize-section.mlc-offer__offer-details",
                    ]

                    # Try each container selector
                    desc_element = None
                    desc_html = None

                    # First check if we have a parameters-only offer
                    try:
                        # Get page source first for BeautifulSoup parsing
                        page_source = self.driver.page_source
                        soup = BeautifulSoup(page_source, "html.parser")

                        params_table = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located(
                                (By.CSS_SELECTOR, "table.mlc-params__list")
                            )
                        )
                        if params_table and not soup.select_one(
                            "div.mlc-offer__description"
                        ):
                            if self.verbose:
                                logger.debug(
                                    "[Scraper] Found parameters-only offer, no description"
                                )
                            # Store a single space for parameters-only offers
                            self.db.data[offer_url].desc = "-"
                            self.db.save()
                            logger.debug(
                                f"[Scraper] Stored empty description for parameters-only offer {offer_id}"
                            )
                            return self.db.get_offer(offer_id)
                    except Exception:
                        # If we can't find params table, continue with normal description search
                        pass

                    for selector in containers:
                        try:
                            logger.debug(f"[Scraper] Trying selector: {selector}")
                            # Wait up to 15 seconds for element
                            element = WebDriverWait(self.driver, 15).until(
                                EC.presence_of_element_located(
                                    (By.CSS_SELECTOR, selector)
                                )
                            )

                            # If we found the section, look for description inside
                            if "offer-details" in selector:
                                try:
                                    desc_element = element.find_element(
                                        By.CSS_SELECTOR, "div.mlc-offer__description"
                                    )
                                except:
                                    continue
                            else:
                                desc_element = element

                            if desc_element:
                                # Try different methods to get content
                                desc_html = desc_element.get_attribute("innerHTML")
                                if not desc_html:
                                    desc_html = desc_element.get_attribute("outerHTML")
                                if desc_html:
                                    break

                        except Exception as e:
                            if self.verbose:
                                logger.debug(
                                    f"[Scraper] Selector {selector} failed: {e!s}"
                                )
                            continue

                    if not desc_html:
                        # Fallback: try to get the HTML directly from page source
                        page_source = self.driver.page_source
                        soup = BeautifulSoup(page_source, "html.parser")
                        desc_elem = soup.select_one("div.mlc-offer__description")
                        if desc_elem:
                            desc_html = str(desc_elem)

                    if desc_html:
                        if self.verbose:
                            logger.debug(
                                "[Scraper] Successfully found description element"
                            )

                        # Preprocess HTML before conversion
                        desc_html = self._preprocess_html(desc_html)

                        # Convert HTML to Markdown
                        h = html2text.HTML2Text()
                        h.body_width = 0  # Don't wrap lines
                        h.unicode_snob = True  # Use Unicode characters
                        desc_markdown = h.handle(desc_html).strip()

                        if desc_markdown:
                            if self.verbose:
                                logger.debug(
                                    f"[Scraper] Converted description ({len(desc_markdown)} chars)"
                                )
                                logger.debug("First 100 chars of description:")
                                logger.debug(desc_markdown[:100] + "...")

                            # Update the database
                            self.db.data[offer_url].desc = desc_markdown
                            self.db.save()  # Save immediately after reading description
                            logger.debug(
                                f"[Scraper] Read and stored description for offer {offer_id}."
                            )
                            return self.db.get_offer(offer_id)
                        else:
                            logger.warning(
                                "[Scraper] Found element but got empty description"
                            )

                    if attempt < max_retries - 1:
                        logger.warning(
                            f"[Scraper] Attempt {attempt + 1} failed, retrying..."
                        )
                        human_delay(3.0, 5.0)  # Longer delay between retries

                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"[Scraper] Attempt {attempt + 1} failed with error: {e!s}"
                        )
                        logger.warning("[Scraper] Retrying...")
                        human_delay(3.0, 5.0)
                    else:
                        raise  # Re-raise on last attempt

            # If we get here, all attempts failed
            logger.error(
                f"[Scraper] Failed to read description after {max_retries} attempts"
            )

        except Exception as e:
            logger.error(f"[Scraper] Error reading offer {offer_id}: {e}")
            if self.verbose:
                logger.exception("[Scraper] Full error details:")

            # Take a screenshot to help debug the issue
            try:
                # Use Path for screenshot path
                screenshot_path = Path(f"error_screenshot_{offer_id}.png")
                self.driver.save_screenshot(str(screenshot_path))
                logger.warning(f"[Scraper] Saved error screenshot to {screenshot_path}")
            except Exception as screenshot_error:
                logger.error(
                    f"[Scraper] Failed to save error screenshot: {screenshot_error!s}"
                )

        return None

    def _evaluate_template(self, template: str, offer: dict) -> str:
        """Evaluate a template string containing {desc}, {title}, etc. placeholders.

        Args:
            template: The template string to evaluate
            offer: The offer dictionary containing the current values

        Returns:
            The evaluated string with all placeholders replaced
        """
        if not template:
            return template

        # Create a context with all possible variables
        context = {
            "desc": offer.get("desc", ""),
            "title": offer.get("title", ""),
            "title_new": offer.get("title_new", ""),
            "desc_new": offer.get("desc_new", ""),
        }

        try:
            return template.format(**context)
        except KeyError as e:
            logger.error(f"[Template] Unknown placeholder in template: {e}")
            return template
        except Exception as e:
            logger.error(f"[Template] Error evaluating template: {e}")
            return template

    def publish_offer_details(
        self,
        offer_id: str,
        new_title: str | None = None,
        new_desc: str | None = None,
    ) -> bool:
        """
        Publish the title and/or description changes to the offer on the website.
        This involves navigating the multi-step edit process on Allegro Lokalnie.
        """
        self._ensure_driver()
        offer_model = self.db.get_offer(offer_id)
        if not offer_model:
            logger.error(f"[Publish] Offer {offer_id} not in database.")
            return False

        try:
            # Step 1: Navigate to the offer's description edit page
            self._navigate_to_offer_edit_page(offer_id)

            # Step 2: Update title and description fields if changes are pending
            title_to_set, desc_to_set = self._prepare_title_and_desc_for_publish(
                offer_model, new_title, new_desc
            )

            made_title_change = False
            if title_to_set is not None:
                self._fill_offer_title(offer_id, title_to_set)
                made_title_change = True

            made_desc_change = False
            if desc_to_set is not None:
                self._fill_offer_description(offer_id, desc_to_set)
                made_desc_change = True

            # Step 3: Proceed with submission if actual changes were made or attempted
            if made_title_change or made_desc_change:
                if self.dryrun:
                    logger.info(f"[DryRun][Publish] Would proceed with multi-step form submission for offer {offer_id}.")
                    return True # Simulate successful dry run publish

                # Actual multi-step submission
                self._submit_description_form()
                self._submit_details_form()
                self._handle_highlight_page_if_present()
                self._submit_summary_form()

                # Step 4: Finalize: Update database, mark as published, and refresh data
                self._finalize_successful_publish(offer_id)
                logger.info(f"[Publish] Successfully published changes for offer {offer_id}.")
                return True
            else:
                logger.info(f"[Publish] No changes to publish for offer {offer_id}.")
                return True

        except Exception as e:
            logger.error(f"[Publish] Failed to publish offer {offer_id}: {e}")
            if self.verbose:
                logger.exception(f"[Publish] Full error details for offer {offer_id}:")
            self._save_error_screenshot(f"publish_error_{offer_id}")
            return False

    def _navigate_to_offer_edit_page(self, offer_id: str) -> None:
        """Navigates to the description edit page for the given offer."""
        assert self.driver is not None, "WebDriver not initialized"
        logger.debug(f"[Publish] Navigating to edit page for offer {offer_id}...")
        edit_url = f"{BASE_URL}/o/oferta/{offer_id}/edycja/opis"
        self.driver.get(edit_url)
        human_delay()
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='title']"))
        )
        logger.debug(f"[Publish] Reached edit page for offer {offer_id}.")

    def _prepare_title_and_desc_for_publish(
        self, offer: OfferData, new_title_arg: str | None, new_desc_arg: str | None
    ) -> tuple[str | None, str | None]:
        """Determines the actual title and description to set, evaluating templates if needed."""
        title_to_set: str | None = None
        final_title_str = new_title_arg or offer.title_new
        if final_title_str:
            evaluated_title = self._evaluate_template(final_title_str, offer.model_dump())
            if evaluated_title != offer.title:
                logger.info(f"[Publish] Will update title for {offer.offer_id}. Old: '{offer.title}', New: '{evaluated_title}'")
                title_to_set = evaluated_title
            else:
                logger.debug(f"[Publish] Title for {offer.offer_id} is already up-to-date.")

        desc_to_set: str | None = None
        final_desc_str = new_desc_arg or offer.desc_new
        if final_desc_str:
            evaluated_desc = self._evaluate_template(final_desc_str, offer.model_dump())
            current_desc_for_compare = offer.desc if offer.desc != "-" else ""
            if evaluated_desc != current_desc_for_compare:
                logger.info(f"[Publish] Will update description for {offer.offer_id}.")
                if self.verbose:
                    logger.debug(f"Old desc:\n{current_desc_for_compare[:200]}...\nNew desc:\n{evaluated_desc[:200]}...")
                desc_to_set = evaluated_desc
            else:
                logger.debug(f"[Publish] Description for {offer.offer_id} is already up-to-date.")

        return title_to_set, desc_to_set

    def _fill_offer_title(self, offer_id: str, title_to_set: str) -> None:
        """Fills the title field on the offer edit page."""
        assert self.driver is not None, "WebDriver not initialized"
        if self.dryrun:
            logger.info(f"[DryRun][Publish] Would set title for {offer_id} to: '{title_to_set}'")
            return

        logger.debug(f"[Publish] Setting title for {offer_id} to: '{title_to_set}'")
        title_input = self.driver.find_element(By.CSS_SELECTOR, "input[name='title']")
        title_input.clear()
        human_delay(0.3, 0.7)
        title_input.send_keys(title_to_set)

        # Update local DB immediately for title_new (actual value set)
        offer_link_key = next(url for url, data in self.db.data.items() if data.offer_id == offer_id)
        self.db.data[offer_link_key].title_new = title_to_set # Store the evaluated title
        self.db.save()

    def _fill_offer_description(self, offer_id: str, desc_to_set: str) -> None:
        """Fills the description field on the offer edit page."""
        assert self.driver is not None, "WebDriver not initialized"
        if self.dryrun:
            logger.info(f"[DryRun][Publish] Would set description for {offer_id}.")
            if self.verbose: logger.debug(f"Desc content: {desc_to_set[:200]}...")
            return

        logger.debug(f"[Publish] Setting description for {offer_id}.")
        desc_editor = self.driver.find_element(By.CSS_SELECTOR, ".tiptap.ProseMirror")
        desc_editor.clear()
        human_delay(0.3, 0.7)
        desc_editor.send_keys(desc_to_set)

        # Update local DB immediately for desc_new (actual value set)
        offer_link_key = next(url for url, data in self.db.data.items() if data.offer_id == offer_id)
        self.db.data[offer_link_key].desc_new = desc_to_set # Store the evaluated description
        self.db.save()

    def _submit_description_form(self) -> None:
        """Clicks the submit button on the description edit page."""
        assert self.driver is not None, "WebDriver not initialized"
        logger.debug("[Publish] Submitting description page...")
        submit_button = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']._button_00fkJ"))
        )
        submit_button.click()
        human_delay()
        logger.debug("[Publish] Description page submitted.")

    def _submit_details_form(self) -> None:
        """Clicks the submit button on the offer details page (after description)."""
        assert self.driver is not None, "WebDriver not initialized"
        logger.debug("[Publish] Submitting details page...")
        # This page might take a moment to load, ensure selector is specific enough
        submit_button = WebDriverWait(self.driver, 15).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "form[id^='offer-form-details-'] button[type='submit'][data-testid='submit-button']"))
            # Example of a more specific selector if needed:
            # EC.element_to_be_clickable((By.XPATH, "//form[contains(@id, 'offer-form-details-')]//button[@type='submit' and @data-testid='submit-button']"))
        )
        submit_button.click()
        human_delay()
        logger.debug("[Publish] Details page submitted.")

    def _handle_highlight_page_if_present(self) -> None:
        """Handles the 'highlight offer' page if it appears, opting for no highlight."""
        assert self.driver is not None, "WebDriver not initialized"
        current_url = self.driver.current_url
        if "wyroznij" not in current_url:
            logger.debug("[Publish] Highlight page not detected, skipping.")
            return

        logger.debug("[Publish] On highlight selection page. Opting for 'no highlight'.")
        try:
            no_highlight_option = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable( # Ensure it's clickable
                    (By.XPATH, "//div[contains(@class, '_inner_ZruGK') and .//h3[text()='Nie chcę wyróżniać']]")
                )
            )
            no_highlight_option.click()
            human_delay()

            submit_highlight_choice_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit'][data-testid='submit-button']"))
                 # Using a more specific selector for the submit button on this page
                 # (By.XPATH, "//div[contains(@class, 'allegro.wizard.wizard-layout')]//button[@data-testid='submit-button']"))
            )
            submit_highlight_choice_button.click()
            human_delay()
            logger.debug("[Publish] Highlight page handled: 'no highlight' selected and submitted.")
        except Exception as e:
            logger.warning(f"[Publish] Could not fully handle highlight page: {e}. Attempting to continue.")
            self._save_error_screenshot("highlight_page_handling_error")


    def _submit_summary_form(self) -> None:
        """Clicks the final submit button on the offer summary/confirmation page."""
        assert self.driver is not None, "WebDriver not initialized"
        logger.debug("[Publish] Submitting summary page...")
        # This is often the final step. Ensure selector is robust.
        submit_button = WebDriverWait(self.driver, 20).until( # Longer wait for final confirmation page
             EC.element_to_be_clickable((By.CSS_SELECTOR, "div[data-testid='offer-publish-summary-card-desktop'] button[data-testid='submit-button']"))
            # Fallback or alternative:
            # EC.element_to_be_clickable((By.XPATH, "//button[@data-testid='submit-button' and contains(., 'Zapisz zmiany') or contains(., 'Wystaw')]"))
        )
        submit_button.click()
        # No human_delay() here, wait for page to change or show success message
        # Consider adding a wait for a success indicator if one exists.
        logger.debug("[Publish] Summary page submitted.")


    def _finalize_successful_publish(self, offer_id: str) -> None:
        """Updates the database after a successful publish operation."""
        logger.debug(f"[Publish] Finalizing publish for offer {offer_id} in database.")
        offer_link_key = next(url for url, data in self.db.data.items() if data.offer_id == offer_id)

        # Update the main title/desc from title_new/desc_new if they were set
        if self.db.data[offer_link_key].title_new:
             self.db.data[offer_link_key].title = self.db.data[offer_link_key].title_new
        # self.db.data[offer_link_key].title_new = "" # Clear pending title

        if self.db.data[offer_link_key].desc_new:
             self.db.data[offer_link_key].desc = self.db.data[offer_link_key].desc_new
        # self.db.data[offer_link_key].desc_new = "" # Clear pending desc

        # It's better to re-read the offer to get the canonical data from the site
        # But for now, just mark as published and clear pending.
        # The `read_offer_details` call below will refresh it.

        self.db.data[offer_link_key].published = True
        # Clearing title_new and desc_new after successful publish might be good,
        # but read_offer_details should ideally fetch the new state.
        # Let's rely on read_offer_details to update them.
        self.db.save()

        logger.info(f"[Publish] Refreshing data for offer {offer_id} after publish...")
        self.read_offer_details(offer_id) # This will update title and desc from site

    def _save_error_screenshot(self, name_prefix: str) -> None:
        """Saves a screenshot of the current browser page for debugging."""
        if self.driver is None:
            return
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_file = Path(f"{name_prefix}_{timestamp}.png")
            self.driver.save_screenshot(str(screenshot_file))
            logger.warning(f"[Scraper] Saved error screenshot to {screenshot_file}")
        except Exception as e:
            logger.error(f"[Scraper] Failed to save error screenshot: {e}")


    def refresh_offers(self) -> None:
        """Refresh offers by merging new arrivals and removing outdated entries."""
        self._ensure_driver()
        logger.info("Refreshing offers from website...")
        self.driver.get(ALLEGRO_URL)

        # Add manual login wait here
        self._wait_for_login()

        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "my-offer-card"))
        )
        max_pages = self._get_max_pages()
        merged_offers: dict[str, OfferData] = {}

        for page in range(1, max_pages + 1):
            logger.info(f"[Site] Processing page {page} of {max_pages}...")
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            offer_cards = soup.find_all("div", class_="my-offer-card")
            if not offer_cards:
                logger.warning(f"[Site] No offers found on page {page}, stopping.")
                break

            for card_html in offer_cards: # Renamed 'card' to 'card_html' for clarity
                parsed_result = self._extract_offer_card_data(card_html) # Changed from offer_obj to fresh_data_from_card
                if parsed_result:
                    offer_link_key, fresh_data_from_card = parsed_result

                    # Logic for refresh_offers:
                    # If offer exists in DB, update its basic info, preserve desc, desc_new, title_new, published.
                    # If desc is empty, trigger a read.
                    # If offer is new, add it and trigger a read for its description.
                    if offer_link_key in self.db.data:
                        existing_model_in_db = self.db.data[offer_link_key]

                        # Update core fields
                        existing_model_in_db.title = fresh_data_from_card.title
                        existing_model_in_db.price = fresh_data_from_card.price
                        existing_model_in_db.views = fresh_data_from_card.views
                        existing_model_in_db.listing_date = fresh_data_from_card.listing_date
                        existing_model_in_db.image_url = fresh_data_from_card.image_url
                        existing_model_in_db.offer_type = fresh_data_from_card.offer_type

                        merged_offers[offer_link_key] = existing_model_in_db # Add to current live offers

                        # Check if description needs to be (re-)fetched.
                        # Original description might be empty or placeholder like "-".
                        # self.reset flag is not typically used with refresh_offers, but good to be aware.
                        desc_is_missing_or_placeholder = not existing_model_in_db.desc or existing_model_in_db.desc == "-"

                        if desc_is_missing_or_placeholder:
                            logger.info(
                                f"[Scraper] Existing offer {fresh_data_from_card.offer_id} needs description. Reading..."
                            )
                            self.read_offer_details(fresh_data_from_card.offer_id)
                            # After read_offer_details, self.db.data[offer_link_key] is updated.
                            # So, we should reflect that in merged_offers.
                            if offer_link_key in self.db.data: # Check if still exists (should)
                                merged_offers[offer_link_key] = self.db.data[offer_link_key]
                        elif self.verbose:
                            logger.debug(
                                f"[Scraper] Offer {fresh_data_from_card.offer_id} already has description. Skipping read."
                            )
                    else:
                        # This is a new offer not previously in the database.
                        # Initialize editable fields and published status.
                        fresh_data_from_card.title_new = ""
                        fresh_data_from_card.desc = "" # Original description is unknown initially
                        fresh_data_from_card.desc_new = ""
                        fresh_data_from_card.published = False

                        # Add to database first so read_offer_details can find it.
                        self.db.data[offer_link_key] = fresh_data_from_card
                        # self.db.save() # Consider if save is needed before read_offer_details for robustness

                        logger.info(
                            f"[Scraper] New offer {fresh_data_from_card.offer_id} found. Reading its description..."
                        )
                        self.read_offer_details(fresh_data_from_card.offer_id)

                        # After read_offer_details, self.db.data[offer_link_key] is updated.
                        # Reflect this in merged_offers.
                        if offer_link_key in self.db.data: # Check if still exists
                           merged_offers[offer_link_key] = self.db.data[offer_link_key]
                        else: # Should not happen if read_offer_details is successful
                           logger.warning(f"Offer {offer_link_key} disappeared after trying to read its details.")


            if page < max_pages:
                self.driver.get(f"{ALLEGRO_URL}?page={page + 1}")
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "my-offer-card"))
                )
                human_delay()

        # Update database with merged results
        # This preserves all data for existing offers and adds new ones
        self.db.data = merged_offers
        self.db.save()
        logger.info(
            f"[Site] Finished refresh: {len(merged_offers)} live offers stored."
        )

    def __del__(self):
        if self.driver is not None:
            try:
                self.driver.quit()
                logger.info("[Scraper] Chrome WebDriver closed.")
            except Exception as e:
                logger.error(f"[Scraper] Error closing WebDriver: {e}")


# ------------------------------------------------------------------------------
# CLI Wrapper with Fire
# ------------------------------------------------------------------------------
class ScrapeExecutor:
    """Handles actual execution of scraping commands.

    This class is only instantiated when we need to perform real operations,
    not during command introspection or help display.
    """

    def __init__(
        self,
        db: OfferDatabase,
        verbose: bool = False,
        dryrun: bool = False,
        reset: bool = False,
    ):
        self.db = db
        self.verbose = verbose
        self.dryrun = dryrun
        self.reset = reset
        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        if dryrun:
            logger.info("[CLI] Running in dry-run mode - no changes will be made")
        self.scraper = AllegroScraper(db, verbose, dryrun, reset)

    def execute_fetch(self) -> None:
        """Execute the list command."""
        if self.dryrun:
            logger.info("[DryRun] Would fetch offers from Allegrolokalnie")
            return
        self.scraper.fetch_offers()

    def execute_read(self, offer_id: str) -> None:
        """Execute the read command."""
        if self.dryrun:
            logger.info(f"[DryRun] Would read details for offer {offer_id}")
            return
        self.scraper.read_offer_details(offer_id)

    def execute_set_title(self, offer_id: str, new_title: str | None) -> None:
        """Execute the set-title command."""
        if self.dryrun:
            logger.info(
                f"[DryRun] Would set title for offer {offer_id} to: {new_title}"
            )
            return
        self.scraper.publish_offer_details(offer_id, new_title=new_title)

    def execute_set_desc(self, offer_id: str, new_desc: str | None) -> None:
        """Execute the set-desc command."""
        if self.dryrun:
            logger.info(
                f"[DryRun] Would set description for offer {offer_id} to: {new_desc}"
            )
            return
        self.scraper.publish_offer_details(offer_id, new_desc=new_desc)

    def execute_read_all(self) -> None:
        """Execute the read-all command."""
        if self.dryrun:
            logger.info("[DryRun] Would refresh all offers and their descriptions")
            return
        self.scraper.refresh_offers()

    def execute_publish_all(self) -> None:
        """Execute the publish-all command."""
        if self.dryrun:
            changes = []
            for offer in self.db.data.values():
                offer_id = offer.offer_id
                if (
                    offer_id
                    and not offer.published
                    and (offer.title_new or offer.desc_new)
                ):
                    changes.append(offer_id)
            if changes:
                logger.info(
                    f"[DryRun] Would publish changes for offers: {', '.join(changes)}"
                )
                # Let the scraper handle each offer in dry-run mode
                for offer_id in changes:
                    self.scraper.publish_offer_details(offer_id)
            else:
                logger.info("[DryRun] No unpublished changes to publish")
            return

        for offer in list(self.db.data.values()):
            offer_id = offer.offer_id
            if offer_id and not offer.published and (offer.title_new or offer.desc_new):
                self.scraper.publish_offer_details(offer_id)
                human_delay(2.0, 4.0)

    def execute_publish(self, offer_id: str) -> None:
        """Execute the publish command for a specific offer."""
        offer = self.db.get_offer(offer_id)
        if not offer:
            logger.error(f"[CLI] Offer {offer_id} not found in database")
            return
        if not (offer.title_new or offer.desc_new):
            logger.info(f"[CLI] No pending changes for offer {offer_id}")
            return

        # Let the scraper handle dry-run mode to show template evaluation
        self.scraper.publish_offer_details(offer_id)


class VolanteCLI:
    """Command-line interface for managing Allegrolokalnie offers.

    This class provides methods to interact with Allegrolokalnie listings through a CLI.
    It handles fetching, reading, updating and publishing offers while using a local JSON
    database for persistence.

    Global Options:
        --verbose: Enable verbose logging output
        --dryrun: Show what would be done without making actual changes
        --reset: When fetching, reset title_new and desc_new to empty (default: False)

    Methods:
        fetch: Fetch and store active offers from Allegrolokalnie
        read: Get description for a specific offer
        set_title: Update an offer's title
        set_desc: Update an offer's description
        read_all: Refresh all offers and their descriptions
        publish_all: Push pending changes for all modified offers
        publish: Push pending changes for one specific offer
    """

    def __init__(
        self,
        verbose: Doc[bool, "Enable verbose logging"] = False,
        dryrun: Doc[bool, "Show what would be done without making changes"] = False,
        reset: Doc[bool, "Reset pending changes when fetching"] = False,
    ):
        """Initialize CLI with a JSON database matching the script's filename."""
        self._db = OfferDatabase(Path(__file__).with_suffix(".toml"))
        self.verbose = verbose
        self.dryrun = dryrun
        self.reset = reset
        # No browser initialization here - that only happens in ScrapeExecutor

    def fetch(self):
        """Fetch all active offers from Allegrolokalnie and store them in the database.

        This command:
        1. Connects to Allegrolokalnie's active offers page
        2. Scrapes all offer cards across all pages
        3. Extracts offer details (title, price, views, etc.)
        4. Stores the data in a local JSON database
        """
        executor = ScrapeExecutor(self._db, self.verbose, self.dryrun, self.reset)
        executor.execute_fetch()
        if not self.dryrun:
            logger.debug(f"[CLI] Fetched and stored {len(self._db.data)} offers.")

    def read(self, offer_id: Doc[str, "Unique identifier for the offer to read"]):
        """Retrieve and store the detailed description for a specific offer.

        Args:
            offer_id: The offer's unique identifier from its URL

        This command:
        1. Loads the offer's detail page
        2. Extracts the full description
        3. Updates the offer's entry in the database
        """
        executor = ScrapeExecutor(self._db, self.verbose, self.dryrun, self.reset)
        executor.execute_read(offer_id)

    def set_title(
        self,
        offer_id: Doc[str, "Unique identifier for the offer to update"],
        new_title: Doc[str | None, "New title text to set (optional)"] = None,
    ):
        """Update an offer's title on Allegrolokalnie.

        Args:
            offer_id: The offer's unique identifier from its URL
            new_title: The new title to set. If None, uses title_new from database

        This command:
        1. Navigates to the offer's edit page
        2. Updates the title field
        3. Saves the changes on Allegrolokalnie
        4. Updates the local database
        """
        executor = ScrapeExecutor(self._db, self.verbose, self.dryrun, self.reset)
        executor.execute_set_title(offer_id, new_title)

    def set_desc(
        self,
        offer_id: Doc[str, "Unique identifier for the offer to update"],
        new_desc: Doc[str | None, "New description text to set (optional)"] = None,
    ):
        """Update an offer's description on Allegrolokalnie.

        Args:
            offer_id: The offer's unique identifier from its URL
            new_desc: The new description to set. If None, uses desc_new from database

        This command:
        1. Navigates to the offer's edit page
        2. Updates the description field
        3. Saves the changes on Allegrolokalnie
        4. Updates the local database
        """
        executor = ScrapeExecutor(self._db, self.verbose, self.dryrun, self.reset)
        executor.execute_set_desc(offer_id, new_desc)

    def read_all(self):
        """Refresh all offers and their descriptions from Allegrolokalnie.

        This command:
        1. Fetches the current list of active offers
        2. For new offers, retrieves their full descriptions
        3. Removes offers no longer active on the site
        4. Preserves existing descriptions and pending changes for unchanged offers
        5. Updates the database with the merged results
        """
        executor = ScrapeExecutor(self._db, self.verbose, self.dryrun, self.reset)
        executor.execute_read_all()

    def publish_all(self):
        """Publish all pending title and description changes to Allegrolokalnie.

        This command:
        1. Identifies offers with pending changes (title_new or desc_new)
        2. For each modified offer:
           - Navigates to its edit page
           - Updates the relevant fields
           - Saves the changes
        3. Updates the local database to reflect the changes
        """
        executor = ScrapeExecutor(self._db, self.verbose, self.dryrun, self.reset)
        executor.execute_publish_all()

    def publish(self, offer_id: Doc[str, "Unique identifier for the offer to publish"]):
        """Publish pending changes for a specific offer to Allegrolokalnie.

        Args:
            offer_id: The offer's unique identifier from its URL

        This command:
        1. Checks if the offer has pending changes
        2. If changes exist:
           - Navigates to the offer's edit page
           - Updates the modified fields
           - Saves the changes
        3. Updates the local database to reflect the changes
        """
        executor = ScrapeExecutor(self._db, self.verbose, self.dryrun, self.reset)
        executor.execute_publish(offer_id)


# ------------------------------------------------------------------------------
# Main Entrypoint
# ------------------------------------------------------------------------------
def main():
    """Execute the AllegroCLI."""
    fire.Fire(VolanteCLI)


if __name__ == "__main__":
    main()
