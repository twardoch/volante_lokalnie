import pytest
from unittest.mock import patch, MagicMock

# Adjust import paths as necessary
from src.volante_lokalnie.volante_lokalnie import VolanteCLI, ScrapeExecutor, OfferDatabase, OfferData

# To test VolanteCLI directly:
# We need to mock OfferDatabase and ScrapeExecutor, or parts of them.

@pytest.fixture
def mock_offer_db_instance():
    """Fixture for a mocked OfferDatabase instance."""
    db_mock = MagicMock(spec=OfferDatabase)
    # Setup any necessary attributes or method return values for db_mock
    # e.g., db_mock.data = {}
    # e.g., db_mock.get_offer.return_value = None or a mock OfferData
    return db_mock

@pytest.fixture
def mock_scrape_executor_instance():
    """Fixture for a mocked ScrapeExecutor instance."""
    executor_mock = MagicMock(spec=ScrapeExecutor)
    # Setup return values for its execute_* methods if needed for specific tests
    # e.g., executor_mock.execute_fetch.return_value = None
    return executor_mock

@patch("src.volante_lokalnie.volante_lokalnie.OfferDatabase")
@patch("src.volante_lokalnie.volante_lokalnie.ScrapeExecutor")
def test_cli_fetch_command(MockScrapeExecutor, MockOfferDatabase, mock_offer_db_instance, mock_scrape_executor_instance):
    """Test the 'fetch' command of VolanteCLI."""
    MockOfferDatabase.return_value = mock_offer_db_instance
    MockScrapeExecutor.return_value = mock_scrape_executor_instance

    cli = VolanteCLI(verbose=True, dryrun=False, reset=True)
    cli.fetch()

    MockOfferDatabase.assert_called_once_with(MagicMock()) # Path(__file__).with_suffix(".toml") is tricky to assert directly without knowing the mock Path's behavior
    # Check that ScrapeExecutor was initialized correctly
    MockScrapeExecutor.assert_called_once_with(
        mock_offer_db_instance,
        verbose=True,
        dryrun=False,
        reset=True
    )
    # Check that the correct method on the executor was called
    mock_scrape_executor_instance.execute_fetch.assert_called_once()

@patch("src.volante_lokalnie.volante_lokalnie.OfferDatabase")
@patch("src.volante_lokalnie.volante_lokalnie.ScrapeExecutor")
def test_cli_read_command(MockScrapeExecutor, MockOfferDatabase, mock_offer_db_instance, mock_scrape_executor_instance):
    """Test the 'read' command."""
    MockOfferDatabase.return_value = mock_offer_db_instance
    MockScrapeExecutor.return_value = mock_scrape_executor_instance

    test_offer_id = "test_id_123"
    cli = VolanteCLI(verbose=False, dryrun=True) # Different global args
    cli.read(offer_id=test_offer_id)

    MockScrapeExecutor.assert_called_once_with(
        mock_offer_db_instance,
        verbose=False,
        dryrun=True,
        reset=False # Default reset value
    )
    mock_scrape_executor_instance.execute_read.assert_called_once_with(test_offer_id)


@patch("src.volante_lokalnie.volante_lokalnie.OfferDatabase")
@patch("src.volante_lokalnie.volante_lokalnie.ScrapeExecutor")
def test_cli_set_title_command(MockScrapeExecutor, MockOfferDatabase, mock_offer_db_instance, mock_scrape_executor_instance):
    """Test the 'set_title' command."""
    MockOfferDatabase.return_value = mock_offer_db_instance
    MockScrapeExecutor.return_value = mock_scrape_executor_instance

    test_offer_id = "id_for_title"
    new_title = "A Brand New Title"
    cli = VolanteCLI() # Defaults for global args
    cli.set_title(offer_id=test_offer_id, new_title=new_title)

    MockScrapeExecutor.assert_called_once_with(
        mock_offer_db_instance,
        verbose=False, dryrun=False, reset=False
    )
    mock_scrape_executor_instance.execute_set_title.assert_called_once_with(test_offer_id, new_title)

@patch("src.volante_lokalnie.volante_lokalnie.OfferDatabase")
@patch("src.volante_lokalnie.volante_lokalnie.ScrapeExecutor")
def test_cli_set_desc_command(MockScrapeExecutor, MockOfferDatabase, mock_offer_db_instance, mock_scrape_executor_instance):
    """Test the 'set_desc' command."""
    MockOfferDatabase.return_value = mock_offer_db_instance
    MockScrapeExecutor.return_value = mock_scrape_executor_instance

    cli = VolanteCLI()
    cli.set_desc(offer_id="id_for_desc", new_desc="A new description.")
    mock_scrape_executor_instance.execute_set_desc.assert_called_once_with("id_for_desc", "A new description.")


@patch("src.volante_lokalnie.volante_lokalnie.OfferDatabase")
@patch("src.volante_lokalnie.volante_lokalnie.ScrapeExecutor")
def test_cli_read_all_command(MockScrapeExecutor, MockOfferDatabase, mock_offer_db_instance, mock_scrape_executor_instance):
    """Test the 'read_all' command."""
    MockOfferDatabase.return_value = mock_offer_db_instance
    MockScrapeExecutor.return_value = mock_scrape_executor_instance

    cli = VolanteCLI()
    cli.read_all()
    mock_scrape_executor_instance.execute_read_all.assert_called_once()


@patch("src.volante_lokalnie.volante_lokalnie.OfferDatabase")
@patch("src.volante_lokalnie.volante_lokalnie.ScrapeExecutor")
def test_cli_publish_all_command(MockScrapeExecutor, MockOfferDatabase, mock_offer_db_instance, mock_scrape_executor_instance):
    """Test the 'publish_all' command."""
    MockOfferDatabase.return_value = mock_offer_db_instance
    MockScrapeExecutor.return_value = mock_scrape_executor_instance

    cli = VolanteCLI()
    cli.publish_all()
    mock_scrape_executor_instance.execute_publish_all.assert_called_once()

@patch("src.volante_lokalnie.volante_lokalnie.OfferDatabase")
@patch("src.volante_lokalnie.volante_lokalnie.ScrapeExecutor")
def test_cli_publish_command(MockScrapeExecutor, MockOfferDatabase, mock_offer_db_instance, mock_scrape_executor_instance):
    """Test the 'publish' command for a specific offer."""
    MockOfferDatabase.return_value = mock_offer_db_instance
    MockScrapeExecutor.return_value = mock_scrape_executor_instance

    cli = VolanteCLI()
    cli.publish(offer_id="publish_this_one")
    mock_scrape_executor_instance.execute_publish.assert_called_once_with("publish_this_one")


# It might also be useful to test the __main__.py entry point using fire.Fire direct invocation
# or by subprocess, but that's more of an integration test for the CLI parsing itself.
# The tests above focus on VolanteCLI class logic.

# To test ScrapeExecutor, one would mock AllegroScraper and OfferDatabase.
# Example test structure for ScrapeExecutor:

@patch("src.volante_lokalnie.volante_lokalnie.AllegroScraper")
def test_scrape_executor_execute_fetch(MockAllegroScraper):
    """Test ScrapeExecutor's execute_fetch method."""
    mock_db = MagicMock(spec=OfferDatabase)
    mock_scraper_instance = MockAllegroScraper.return_value # Get the instance mock

    executor = ScrapeExecutor(db=mock_db, verbose=True, dryrun=False, reset=False)
    executor.execute_fetch()

    MockAllegroScraper.assert_called_once_with(mock_db, True, False, False)
    mock_scraper_instance.fetch_offers.assert_called_once()

@patch("src.volante_lokalnie.volante_lokalnie.AllegroScraper")
def test_scrape_executor_execute_fetch_dryrun(MockAllegroScraper, caplog):
    """Test ScrapeExecutor's execute_fetch method in dryrun mode."""
    mock_db = MagicMock(spec=OfferDatabase)
    mock_scraper_instance = MockAllegroScraper.return_value

    executor = ScrapeExecutor(db=mock_db, dryrun=True)
    executor.execute_fetch()

    assert "[DryRun] Would fetch offers from Allegrolokalnie" in caplog.text
    mock_scraper_instance.fetch_offers.assert_not_called()


# Similar tests would be written for other execute_* methods of ScrapeExecutor,
# checking that they call the correct AllegroScraper methods or log dryrun messages.
# For publish_all, one might need to set up mock_db.data with some offers
# to test the looping and conditional calls.
# For example:
@patch("src.volante_lokalnie.volante_lokalnie.AllegroScraper")
def test_scrape_executor_publish_all_with_changes(MockAllegroScraper, caplog):
    mock_db = MagicMock(spec=OfferDatabase)
    mock_scraper_instance = MockAllegroScraper.return_value

    offer1_mock = MagicMock(spec=OfferData)
    offer1_mock.offer_id = "id1"
    offer1_mock.published = False
    offer1_mock.title_new = "New Title"
    offer1_mock.desc_new = ""

    offer2_mock = MagicMock(spec=OfferData)
    offer2_mock.offer_id = "id2"
    offer2_mock.published = True # Already published
    offer2_mock.title_new = "Another New Title"
    offer2_mock.desc_new = ""

    offer3_mock = MagicMock(spec=OfferData)
    offer3_mock.offer_id = "id3"
    offer3_mock.published = False
    offer3_mock.title_new = "" # No changes
    offer3_mock.desc_new = ""


    mock_db.data = {"url1": offer1_mock, "url2": offer2_mock, "url3": offer3_mock}
    # When ScrapeExecutor iterates through db.data.values()
    mock_db.data.values.return_value = [offer1_mock, offer2_mock, offer3_mock]


    executor = ScrapeExecutor(db=mock_db, dryrun=False)
    executor.execute_publish_all()

    # Should only call publish_offer_details for offer1
    mock_scraper_instance.publish_offer_details.assert_called_once_with("id1")

    # Test dry run for publish_all
    executor_dryrun = ScrapeExecutor(db=mock_db, dryrun=True)
    executor_dryrun.execute_publish_all()
    assert "[DryRun] Would publish changes for offers: id1" in caplog.text
    # In dryrun, publish_offer_details is still called on the scraper,
    # but the scraper's method itself should handle the dryrun.
    # So, if scraper.publish_offer_details is called, it's up to its own dryrun logic.
    # The current ScrapeExecutor dryrun for publish_all logs AND calls scraper.publish_offer_details.
    # This means the scraper's publish_offer_details also needs to respect dryrun.
    # The test above checks the ScrapeExecutor log.
    # If scraper.publish_offer_details also logs, that would appear too.
    # This implies that scraper.publish_offer_details should be called, and it has its own dryrun logic.
    # Let's verify calls on the mock_scraper_instance for the dryrun case.
    # It should be called once for "id1" even in dryrun, to allow template evaluation logging.
    calls = [call for call in mock_scraper_instance.publish_offer_details.call_args_list if call[0][0] == "id1"]
    assert len(calls) == 2 # Once for non-dryrun, once for dryrun. Or adjust if mock is reset.

pytest_plugins = ["pytester"]
