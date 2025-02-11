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
from typing import Dict, Optional, cast
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


def find_chrome_debug_process() -> Optional[psutil.Process]:
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
        self.data = {url: data for url, data in sorted_items}

    def load(self) -> None:
        """Load data from a TOML file and convert to OfferData models."""
        try:
            if self.file_path.exists():
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
            else:
                logger.warning(
                    f"[DB] Database {self.file_path} not found, started empty."
                )
                self.data = {}
        except Exception as e:
            logger.error(
                f"[DB] Failed to load database: {e}. Starting with an empty database."
            )
            self.data = {}

    def save(self) -> None:
        """Convert OfferData models to dicts and save to TOML file."""
        try:
            self._sort_data()
            # Convert OfferData models to dicts for TOML serialization
            data_dict = {url: offer.model_dump() for url, offer in self.data.items()}
            with open(self.file_path, "wb") as f:
                tomli_w.dump(data_dict, f)
            logger.debug(f"[DB] Saved {len(self.data)} offers to {self.file_path}")
        except Exception as e:
            logger.error(f"[DB] Failed to save database: {e}")

    def get_offer(self, offer_id: str) -> Optional[OfferData]:
        """Retrieve an offer by its offer_id."""
        for url, offer in self.data.items():
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
        offers_data: Dict[str, dict] = {}

        for page in range(1, max_pages + 1):
            logger.info(f"[Site] Processing page {page} of {max_pages}...")
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            offer_cards = soup.find_all("div", class_="my-offer-card")
            if not offer_cards:
                logger.warning(f"[Site] No offers found on page {page}, stopping.")
                break

            # Process all offers on the current page.
            for card in offer_cards:
                result = self._extract_offer_data(card)
                if result:
                    offer_link, offer_obj = result
                    if offer_link in self.db.data:
                        # Preserve existing data while updating basic info
                        existing = self.db.data[offer_link]
                        offer_dict = offer_obj.model_dump()
                        offer_dict["desc"] = existing.get("desc", "")
                        offer_dict["desc_new"] = (
                            "" if self.reset else existing.get("desc_new", "")
                        )
                        offer_dict["title_new"] = (
                            "" if self.reset else existing.get("title_new", "")
                        )
                        offer_dict["published"] = (
                            False if self.reset else existing.get("published", False)
                        )
                        offers_data[offer_link] = offer_dict
                    else:
                        # New offer: initialize with empty edits and unpublished
                        offer_dict = offer_obj.model_dump()
                        offer_dict["published"] = False
                        offers_data[offer_link] = offer_dict

            # Save progress after each page.
            self.db.data = offers_data
            self.db.save()
            logger.debug(
                f"[Site] Saved progress after page {page} ({len(offers_data)} offers so far)"
            )

            # Navigate to next page if applicable.
            if page < max_pages:
                self.driver.get(f"{ALLEGRO_URL}?page={page + 1}")
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "my-offer-card"))
                )
                human_delay()

        logger.info(
            f"[Site] Finished fetching all {len(offers_data)} offers from website."
        )

    def _extract_offer_data(self, card: Tag) -> Optional[tuple[str, OfferData]]:
        """Extract offer data from a card element on the page."""
        try:
            if self.verbose:
                logger.debug("[Scraper] Starting to extract offer data from card")

            link_elem = card.select_one("a[itemprop='url']")
            if not link_elem or not isinstance(link_elem.get("href"), str):
                logger.debug("Offer card missing link element; skipping.")
                return None

            href = cast(str, link_elem["href"])
            offer_link = urljoin(BASE_URL, href)
            offer_id = offer_link.split("/")[-1]

            if self.verbose:
                logger.debug(f"[Scraper] Processing offer {offer_id} at {offer_link}")

            title_elem = card.select_one(".my-offer-card__title a")
            title = title_elem.text.strip() if title_elem else "Unknown Title"

            price_elem = card.select_one("span[itemprop='price']")
            price_text = price_elem.text.strip() if price_elem else "0"
            price = float(price_text.replace(",", ".").replace("zł", "").strip())

            views_elem = card.select_one(".m-t-1.m-b-1")
            views_text = views_elem.text if views_elem else "0"
            views = int("".join(filter(str.isdigit, views_text)))

            date_elem = card.select_one("time[itemprop='startDate']")
            date_str = date_elem.get("datetime") if date_elem else None
            listing_date = (
                datetime.fromisoformat(
                    cast(str, date_str).replace("Z", "+00:00")
                ).isoformat()
                if date_str
                else datetime.now().isoformat()
            )

            img_elem = card.select_one("img[itemprop='image']")
            image_url = cast(str, img_elem.get("src")) if img_elem else ""

            type_elem = card.select_one("[data-testid^='offer-type-']")
            offer_type = type_elem.text.strip() if type_elem else "Unknown"

            if self.verbose:
                logger.debug(
                    f"[Scraper] Successfully extracted data for offer {offer_id}"
                )
                logger.debug(f"[Scraper] Title: {title}")
                logger.debug(f"[Scraper] Price: {price}")
                logger.debug(f"[Scraper] Views: {views}")
                logger.debug(f"[Scraper] Type: {offer_type}")

            if offer_link in self.db.data:
                existing = self.db.data[offer_link]
                # Update only basic fields while preserving all others
                existing.title = title
                existing.price = price
                existing.views = views
                existing.listing_date = listing_date
                existing.image_url = image_url
                existing.offer_type = offer_type
                self.db.data[offer_link] = existing
                if self.verbose:
                    logger.debug(f"[Scraper] Updated existing offer {offer_id}")
                return offer_link, existing
            else:
                # New offer: initialize with empty edits
                offer = OfferData(
                    title=title,
                    price=price,
                    views=views,
                    listing_date=listing_date,
                    image_url=image_url,
                    offer_type=offer_type,
                    offer_id=offer_id,
                )
                self.db.data[offer_link] = offer
                self.db.save()
                if self.verbose:
                    logger.debug(f"[Scraper] Created new offer {offer_id}")
                return offer_link, offer

        except Exception as e:
            logger.error(f"Error extracting offer data: {e}")
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

    def read_offer_details(self, offer_id: str) -> Optional[dict]:
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
                                    f"[Scraper] Selector {selector} failed: {str(e)}"
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
                            f"[Scraper] Attempt {attempt + 1} failed with error: {str(e)}"
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
                screenshot_path = f"error_screenshot_{offer_id}.png"
                self.driver.save_screenshot(screenshot_path)
                logger.warning(f"[Scraper] Saved error screenshot to {screenshot_path}")
            except Exception as screenshot_error:
                logger.error(
                    f"[Scraper] Failed to save error screenshot: {str(screenshot_error)}"
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
        new_title: Optional[str] = None,
        new_desc: Optional[str] = None,
    ) -> bool:
        """
        Publish the title and/or description changes to the offer on the website and update the database.
        """
        self._ensure_driver()
        offer = self.db.get_offer(offer_id)
        if not offer:
            logger.error(
                f"[Scraper] Offer {offer_id} not in database, run `list_offers` first."
            )
            return False

        try:
            logger.debug(f"[Scraper] Navigating to edit page for offer {offer_id}...")
            edit_url = f"{BASE_URL}/o/oferta/{offer_id}/edycja/opis"
            self.driver.get(edit_url)
            human_delay()

            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='title']"))
            )

            # Update title if needed
            title_new = new_title or offer.title_new
            title_new_evaluated = None
            if title_new:
                title_new_evaluated = self._evaluate_template(
                    title_new, offer.model_dump()
                )
                current_title = offer.title
                if title_new_evaluated != current_title:
                    if self.verbose:
                        logger.debug(f"[Scraper] Current title: {current_title}")
                        logger.debug(f"[Scraper] Template title: {title_new}")
                        logger.debug(
                            f"[Scraper] Evaluated title: {title_new_evaluated}"
                        )

                    if not self.dryrun:
                        title_input = self.driver.find_element(
                            By.CSS_SELECTOR, "input[name='title']"
                        )
                        title_input.clear()
                        human_delay(0.5, 1.0)
                        title_input.send_keys(title_new_evaluated)
                        key = next(
                            url
                            for url, data in self.db.data.items()
                            if data.offer_id == offer_id
                        )
                        self.db.data[key].title_new = title_new_evaluated
                        self.db.save()  # Save after title update
                        logger.debug(f"[Scraper] Title set to: {title_new_evaluated}")
                    else:
                        logger.debug(
                            f"[DryRun] Would set title to: {title_new_evaluated}"
                        )

            # Update description if needed
            desc_new = new_desc or offer.desc_new
            desc_new_evaluated = None
            if desc_new:
                desc_new_evaluated = self._evaluate_template(
                    desc_new, offer.model_dump()
                )
                current_desc = offer.desc
                if current_desc == "-":
                    current_desc = ""
                if desc_new_evaluated != current_desc:
                    if self.verbose:
                        logger.debug(f"[Scraper] Current description: {current_desc}")
                        logger.debug(f"[Scraper] Template description: {desc_new}")
                        logger.debug(
                            f"[Scraper] Evaluated description: {desc_new_evaluated}"
                        )

                    if not self.dryrun:
                        desc_elem = self.driver.find_element(
                            By.CSS_SELECTOR, ".tiptap.ProseMirror"
                        )
                        desc_elem.clear()
                        human_delay(0.5, 1.0)
                        desc_elem.send_keys(desc_new_evaluated)
                        key = next(
                            url
                            for url, data in self.db.data.items()
                            if data.offer_id == offer_id
                        )
                        self.db.data[key].desc_new = desc_new_evaluated
                        self.db.save()  # Save after description update
                        logger.debug(
                            f"[Scraper] Description set to: {desc_new_evaluated}"
                        )
                    else:
                        logger.debug(
                            f"[DryRun] Would set description to: {desc_new_evaluated}"
                        )

            if (title_new and title_new_evaluated != offer.title) or (
                desc_new and desc_new_evaluated != offer.desc
            ):
                if not self.dryrun:
                    human_delay()
                    try:
                        # First, click the submit button on the description page
                        desc_submit_btn = WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable(
                                (By.CSS_SELECTOR, "button[type='submit']._button_00fkJ")
                            )
                        )
                        desc_submit_btn.click()
                        logger.debug("[Scraper] Clicked submit on description page")
                        human_delay()

                        # Now we should be on the details page
                        logger.debug("[Scraper] Waiting for details page to load...")
                        details_submit_btn = WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable(
                                (By.CSS_SELECTOR, "[data-testid='submit-button']")
                            )
                        )
                        details_submit_btn.click()
                        logger.debug("[Scraper] Clicked submit on details page")
                        human_delay()

                        # We may land on the highlight selection page
                        current_url = self.driver.current_url
                        if "wyroznij" in current_url:
                            logger.debug("[Scraper] On highlight selection page...")

                            # Find and click the "no highlight" option
                            no_highlight_div = WebDriverWait(self.driver, 10).until(
                                EC.presence_of_element_located(
                                    (
                                        By.XPATH,
                                        "//div[contains(@class, '_inner_ZruGK') and .//h3[text()='Nie chcę wyróżniać']]",
                                    )
                                )
                            )
                            no_highlight_div.click()
                            logger.debug("[Scraper] Selected 'no highlight' option")
                            human_delay()

                            # Click the next step button after selection
                            highlight_submit_btn = WebDriverWait(self.driver, 10).until(
                                EC.element_to_be_clickable(
                                    (By.CSS_SELECTOR, "[data-testid='submit-button']")
                                )
                            )
                            highlight_submit_btn.click()
                            logger.debug("[Scraper] Clicked submit on highlight page")
                            human_delay()

                        # Finally, on the summary page, click the save changes button
                        logger.debug(
                            "[Scraper] Waiting for summary page submit button..."
                        )
                        final_submit_btn = WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable(
                                (By.CSS_SELECTOR, "[data-testid='submit-button']")
                            )
                        )
                        final_submit_btn.click()
                        logger.debug("[Scraper] Clicked final submit button")

                        self.db.save()
                        logger.debug(
                            f"[Scraper] Successfully published changes to offer {offer_id}."
                        )

                        # After successful publish, mark as published and refresh the data
                        key = next(
                            url
                            for url, data in self.db.data.items()
                            if data.offer_id == offer_id
                        )
                        self.db.data[key].published = True
                        self.db.save()

                        # Refresh the offer data to get updated title/desc
                        self.read_offer_details(offer_id)
                        return True
                    except Exception as e:
                        logger.error(
                            f"[Scraper] Error during form submission: {str(e)}"
                        )
                        # Take a screenshot to help debug the issue
                        try:
                            screenshot_path = f"error_screenshot_{offer_id}.png"
                            self.driver.save_screenshot(screenshot_path)
                            logger.warning(
                                f"[Scraper] Saved error screenshot to {screenshot_path}"
                            )
                        except Exception as screenshot_error:
                            logger.error(
                                f"[Scraper] Failed to save error screenshot: {str(screenshot_error)}"
                            )
                        return False
                else:
                    logger.debug("[DryRun] Would click submit on description page")
                    logger.debug("[DryRun] Would click submit on details page")
                    logger.debug("[DryRun] Would handle highlight selection if needed")
                    logger.debug("[DryRun] Would click final submit on summary page")
                return True
            else:
                logger.debug(f"[Scraper] No changes needed for offer {offer_id}.")
                return True

        except Exception as e:
            logger.error(f"[Scraper] Error publishing offer {offer_id}: {e}")
            return False

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

            for card in offer_cards:
                result = self._extract_offer_data(card)
                if result:
                    offer_link, offer_obj = result
                    if offer_link in self.db.data:
                        # For existing offers: update only basic fields
                        # Keep all other fields from existing data
                        existing = self.db.data[offer_link]
                        existing.title = offer_obj.title
                        existing.price = offer_obj.price
                        existing.views = offer_obj.views
                        existing.listing_date = offer_obj.listing_date
                        existing.image_url = offer_obj.image_url
                        existing.offer_type = offer_obj.offer_type
                        merged_offers[offer_link] = existing

                        # Only read description if it's missing or empty
                        # A single space desc means details have been fetched
                        desc = existing.desc
                        needs_desc = bool(not desc or desc == "")
                        if desc == "-":
                            needs_desc = False
                        if needs_desc:
                            logger.info(
                                f"[Scraper] Reading missing description for {offer_obj.offer_id}"
                            )
                            self.read_offer_details(offer_obj.offer_id)
                            # Update from db after reading description
                            merged_offers[offer_link] = self.db.data[offer_link]
                        else:
                            if self.verbose:
                                logger.debug(
                                    f"[Scraper] Skipping description fetch for {offer_obj.offer_id} - already have details"
                                )
                    else:
                        # New offer: initialize with empty edits
                        offer_obj.desc = ""
                        offer_obj.desc_new = ""
                        offer_obj.title_new = ""
                        offer_obj.published = False
                        merged_offers[offer_link] = offer_obj
                        self.db.data[offer_link] = offer_obj
                        self.db.save()  # Save before reading details

                        if self.verbose:
                            logger.debug(
                                f"[Scraper] Reading description for new offer {offer_obj.offer_id}"
                            )
                        self.read_offer_details(offer_obj.offer_id)
                        # Update from db after reading description
                        merged_offers[offer_link] = self.db.data[offer_link]

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
