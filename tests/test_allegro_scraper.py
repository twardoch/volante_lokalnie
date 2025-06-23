import pytest
from unittest.mock import MagicMock, patch
from bs4 import BeautifulSoup, Tag
from datetime import datetime

from src.volante_lokalnie.volante_lokalnie import AllegroScraper, OfferDatabase
from src.volante_lokalnie.volante_lokalnie import BASE_URL # Import BASE_URL

# Minimal OfferDatabase mock for scraper instantiation
@pytest.fixture
def mock_db():
    db = MagicMock(spec=OfferDatabase)
    db.data = {} # Scraper might try to read this
    return db

@pytest.fixture
def scraper(mock_db):
    # Scraper initialized with verbose=True for easier debugging of test failures if logs are captured
    return AllegroScraper(db=mock_db, verbose=True, dryrun=False, reset=False)

# --- Tests for _extract_offer_card_data ---

def create_mock_card_tag(
    offer_id="123",
    title="Test Title",
    price_str="123,45 zł",
    views_str="Odsłony: 10",
    date_iso="2023-01-01T12:00:00Z",
    img_src="http://example.com/img.jpg",
    offer_type_str="Kup Teraz",
    base_url_in_href=False # If true, href will be full, otherwise relative
) -> Tag:
    """Helper to create a BeautifulSoup Tag object mimicking an offer card."""
    href_val = f"{BASE_URL}/d/oferty/{offer_id}" if base_url_in_href else f"/d/oferty/{offer_id}"

    html = f"""
    <div class="my-offer-card">
        <a itemprop="url" href="{href_val}">
            <img itemprop="image" src="{img_src}" />
        </a>
        <div class="my-offer-card__title">
            <a href="{href_val}">{title}</a>
        </div>
        <div><span itemprop="price">{price_str}</span></div>
        <div class="m-t-1 m-b-1">{views_str}</div>
        <time itemprop="startDate" datetime="{date_iso}"></time>
        <div data-testid="offer-type-test">{offer_type_str}</div>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    return soup.find("div", class_="my-offer-card")

def test_extract_offer_card_data_success(scraper):
    """Test successful extraction of data from a valid offer card."""
    now_iso_utc = datetime.utcnow().isoformat() + "Z" # Ensure Z for UTC
    card_tag = create_mock_card_tag(
        offer_id="test1",
        title="Super Offer",
        price_str="99,99 zł",
        views_str="Odsłony: 123",
        date_iso=now_iso_utc,
        img_src="http://images.com/super.png",
        offer_type_str="Licytacja"
    )

    expected_link = f"{BASE_URL}/d/oferty/test1"
    expected_listing_date = datetime.fromisoformat(now_iso_utc.replace("Z", "+00:00")).isoformat()

    result_link, offer_data = scraper._extract_offer_card_data(card_tag)

    assert result_link == expected_link
    assert offer_data.offer_id == "test1"
    assert offer_data.title == "Super Offer"
    assert offer_data.price == 99.99
    assert offer_data.views == 123
    assert offer_data.listing_date == expected_listing_date
    assert offer_data.image_url == "http://images.com/super.png"
    assert offer_data.offer_type == "Licytacja"

def test_extract_offer_card_data_relative_url_handling(scraper):
    """Test that relative URLs in href are correctly joined with BASE_URL."""
    card_tag = create_mock_card_tag(offer_id="relative123", base_url_in_href=False)
    expected_link = f"{BASE_URL}/d/oferty/relative123"

    result_link, offer_data = scraper._extract_offer_card_data(card_tag)
    assert result_link == expected_link
    assert offer_data.offer_id == "relative123"

def test_extract_offer_card_data_full_url_handling(scraper):
    """Test that full URLs in href are handled correctly (though current create_mock_card_tag uses BASE_URL)."""
    card_tag = create_mock_card_tag(offer_id="fullurl456", base_url_in_href=True) # href will include BASE_URL
    expected_link = f"{BASE_URL}/d/oferty/fullurl456" # urljoin should handle this fine

    result_link, offer_data = scraper._extract_offer_card_data(card_tag)
    assert result_link == expected_link
    assert offer_data.offer_id == "fullurl456"


def test_extract_offer_card_data_missing_elements(scraper, caplog):
    """Test robustness when some optional elements are missing from the card."""
    # Create a card with several missing pieces of information
    html_missing_data = """
    <div class="my-offer-card">
        <a itemprop="url" href="/d/oferty/missing_data_id"> <!-- Link and ID are essential -->
            <!-- No image -->
        </a>
        <div class="my-offer-card__title">
            <a><!-- No title text --></a>
        </div>
        <!-- No price -->
        <!-- No views -->
        <!-- No date -->
        <!-- No offer type -->
    </div>
    """
    soup = BeautifulSoup(html_missing_data, "html.parser")
    card_tag_missing = soup.find("div", class_="my-offer-card")

    result_link, offer_data = scraper._extract_offer_card_data(card_tag_missing)

    assert result_link == f"{BASE_URL}/d/oferty/missing_data_id"
    assert offer_data.offer_id == "missing_data_id"
    assert offer_data.title == "Unknown Title" # Default
    assert offer_data.price == 0.0 # Default due to parsing failure logged
    assert offer_data.views == 0 # Default due to parsing failure logged
    assert isinstance(offer_data.listing_date, str) # Should default to now()
    assert offer_data.image_url == "" # Default
    assert offer_data.offer_type == "Unknown" # Default

    # Check logs for warnings about parsing issues
    assert "Could not parse price '0' for offer missing_data_id" in caplog.text # price_text defaults to "0"
    assert "Could not parse views '0' for offer missing_data_id" in caplog.text # views_text defaults to "0"
    assert "Missing listing date for offer missing_data_id" in caplog.text


def test_extract_offer_card_data_invalid_price_format(scraper, caplog):
    card_tag = create_mock_card_tag(price_str="Not a price")
    _, offer_data = scraper._extract_offer_card_data(card_tag)
    assert offer_data.price == 0.0
    assert "Could not parse price 'Not a price' for offer 123" in caplog.text

def test_extract_offer_card_data_invalid_views_format(scraper, caplog):
    card_tag = create_mock_card_tag(views_str="Odsłony: lots")
    _, offer_data = scraper._extract_offer_card_data(card_tag)
    assert offer_data.views == 0 # Default after failing to parse "lots"
    assert "Could not parse views 'Odsłony: lots' for offer 123" in caplog.text


def test_extract_offer_card_data_invalid_date_format(scraper, caplog):
    card_tag = create_mock_card_tag(date_iso="not-an-iso-date")
    _, offer_data = scraper._extract_offer_card_data(card_tag)
    # listing_date will be datetime.now().isoformat(), so we just check a warning was logged
    assert "Could not parse date 'not-an-iso-date' for offer 123" in caplog.text
    # Verify it's a valid ISO date string (produced by datetime.now().isoformat())
    try:
        datetime.fromisoformat(offer_data.listing_date)
    except ValueError:
        pytest.fail("Default listing_date is not a valid ISO format string.")


def test_extract_offer_card_data_no_link_element(scraper, caplog):
    """Test behavior when the main link element is missing."""
    html_no_link = """<div class="my-offer-card"></div>""" # Card without an <a> tag with itemprop="url"
    soup = BeautifulSoup(html_no_link, "html.parser")
    card_tag_no_link = soup.find("div", class_="my-offer-card")

    result = scraper._extract_offer_card_data(card_tag_no_link)
    assert result is None
    assert "Offer card missing link element; skipping." in caplog.text

def test_extract_offer_card_data_no_offer_id_from_link(scraper, caplog):
    """Test behavior when offer ID cannot be extracted from the link."""
    # Create a card with a link that won't yield an offer ID (e.g., just base_url)
    html_bad_link = f"""
    <div class="my-offer-card">
        <a itemprop="url" href="{BASE_URL}/"></a>
    </div>
    """
    soup = BeautifulSoup(html_bad_link, "html.parser")
    card_tag_bad_link = soup.find("div", class_="my-offer-card")

    result = scraper._extract_offer_card_data(card_tag_bad_link)
    assert result is None
    assert f"Could not extract offer_id from link {BASE_URL}/; skipping." in caplog.text

# More tests can be added for edge cases in specific field extractions if complex logic exists there.
# For example, if offer_type extraction involved more than just .text.strip().
# Current implementation of _extract_offer_card_data is fairly straightforward with defaults.
# TODO: Add tests for _get_max_pages
# TODO: Add tests for _preprocess_html
# TODO: Add tests for _wait_for_login (needs Selenium driver mock)
# TODO: Add tests for fetch_offers, read_offer_details, publish_offer_details (complex, many mocks)
# TODO: Add tests for refresh_offers
# TODO: Add tests for _evaluate_template
# TODO: Add tests for utility functions like ensure_debug_chrome (hard to test reliably)
# TODO: Add tests for _setup_driver, _ensure_driver

# Example for _evaluate_template - can be tested without full scraper setup
def test_evaluate_template(scraper): # scraper fixture just to call the method
    offer_dict_for_template = {
        "title": "Old Title",
        "desc": "Old Description",
        "title_new": "New Title Template {views}", # Example with a placeholder
        "desc_new": "New Desc Template {price}",
        "views": 123, # Need to ensure these are in the dict for format
        "price": 99.99
    }

    # Test with title_new template
    template_str_title = offer_dict_for_template["title_new"]
    evaluated_title = scraper._evaluate_template(template_str_title, offer_dict_for_template)
    assert evaluated_title == "New Title Template 123"

    # Test with desc_new template
    template_str_desc = offer_dict_for_template["desc_new"]
    evaluated_desc = scraper._evaluate_template(template_str_desc, offer_dict_for_template)
    assert evaluated_desc == "New Desc Template 99.99"

    # Test with no template (empty string)
    assert scraper._evaluate_template("", offer_dict_for_template) == ""

    # Test with template using non-existent key (should log error and return template)
    with patch.object(scraper.logger, "error") as mock_log_error: # Assuming scraper uses self.logger
        bad_template = "Template with {non_existent_key}"
        result = scraper._evaluate_template(bad_template, offer_dict_for_template)
        assert result == bad_template
        mock_log_error.assert_called_once()
        assert "Unknown placeholder" in mock_log_error.call_args[0][0]

    # Test with current title/desc if new ones are empty
    offer_dict_no_new = {
        "title": "Current Title", "desc": "Current Desc", "title_new": "", "desc_new": ""
    }
    assert scraper._evaluate_template(offer_dict_no_new["title_new"], offer_dict_no_new) == ""
    assert scraper._evaluate_template(offer_dict_no_new["desc_new"], offer_dict_no_new) == ""

    # Test template using 'title' and 'desc'
    template_using_title = "Based on {title}"
    evaluated = scraper._evaluate_template(template_using_title, offer_dict_for_template)
    assert evaluated == "Based on Old Title"

    template_using_desc = "Based on {desc}"
    evaluated_desc = scraper._evaluate_template(template_using_desc, offer_dict_for_template)
    assert evaluated_desc == "Based on Old Description"

# --- Tests for _preprocess_html ---
def test_preprocess_html_converts_desc_h2(scraper):
    """Test that <p class="desc-h2"> is converted to <h2>."""
    raw_html = '<p class="desc-h2">Heading</p>'
    processed_html = scraper._preprocess_html(raw_html)
    # BeautifulSoup might add html/body tags, so check for the core transformation
    assert "<h2>Heading</h2>" in processed_html.lower().replace(' class="desc-h2"', "") # Class should be removed

def test_preprocess_html_cleans_desc_p(scraper):
    """Test that class is removed from <p class="desc-p">."""
    raw_html = '<p class="desc-p">Paragraph</p>'
    processed_html = scraper._preprocess_html(raw_html)
    assert "<h2>" not in processed_html.lower() # Make sure it's not mistaken for h2
    assert "<p>Paragraph</p>" in processed_html.lower().replace(' class="desc-p"', "") # Class should be removed

def test_preprocess_html_no_change_for_standard_tags(scraper):
    """Test that standard HTML tags are preserved."""
    raw_html = "<div><p>Standard paragraph.</p><h1>Standard H1</h1><ul><li>Item</li></ul></div>"
    processed_html = scraper._preprocess_html(raw_html)
    # Check if the core structure remains, accounting for minor auto-corrections by BeautifulSoup
    # (e.g. lowercase tags, self-closing tags might be expanded)
    # For simplicity, check for key content presence
    assert "<p>Standard paragraph.</p>" in processed_html
    assert "<h1>Standard H1</h1>" in processed_html # Case might change
    assert "<li>Item</li>" in processed_html


pytest_plugins = ["pytester"] # For caplog, etc.
