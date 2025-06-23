import pytest
from unittest.mock import mock_open, patch
import tomli
import tomli_w

# Adjust the import path based on your project structure
from src.volante_lokalnie.volante_lokalnie import OfferDatabase, OfferData
from datetime import datetime

TEST_DB_PATH_STR = "test_db_file.toml" # In-memory path for tests

@pytest.fixture
def mock_offer_data_list(tmp_path):
    """Provides a list of OfferData objects for testing."""
    now_iso = datetime.now().isoformat()
    return [
        OfferData(title="Offer 1", price=10.0, views=1, listing_date=now_iso, image_url="img1.jpg", offer_type="t1", offer_id="id1"),
        OfferData(title="Offer 2", price=20.0, views=2, listing_date=datetime(2023, 1, 1).isoformat(), image_url="img2.jpg", offer_type="t2", offer_id="id2"),
    ]

@pytest.fixture
def sample_toml_content_dict(mock_offer_data_list):
    """Provides a dictionary representation of offer data, similar to how it's stored in TOML."""
    return {
        f"http://example.com/offer/{offer.offer_id}": offer.model_dump(mode="json")
        for offer in mock_offer_data_list
    }

@pytest.fixture
def db_path_mock(tmp_path):
    """ Mocks the Path object passed to OfferDatabase to use tmp_path """
    # Create a dummy file path object that OfferDatabase will use
    # OfferDatabase itself appends .toml, so provide the base name
    return tmp_path / "test_volante_data"


class TestOfferDatabase:

    def test_init_loads_data_if_file_exists(self, db_path_mock, sample_toml_content_dict):
        """Test database loads data from existing TOML file on init."""
        toml_file_path = db_path_mock.with_suffix(".toml")
        with open(toml_file_path, "wb") as f:
            tomli_w.dump(sample_toml_content_dict, f)

        db = OfferDatabase(db_path_mock)
        assert len(db.data) == len(sample_toml_content_dict)
        for url, offer_dict in sample_toml_content_dict.items():
            assert url in db.data
            assert db.data[url].offer_id == offer_dict["offer_id"]

    def test_init_empty_if_file_not_exists(self, db_path_mock):
        """Test database is empty if TOML file does not exist."""
        # Ensure file does not exist (tmp_path is clean)
        db = OfferDatabase(db_path_mock)
        assert len(db.data) == 0

    def test_init_handles_toml_decode_error(self, db_path_mock, caplog):
        """Test database handles TOMLDecodeError during load."""
        toml_file_path = db_path_mock.with_suffix(".toml")
        with open(toml_file_path, "w") as f:
            f.write("this is not valid toml content {{{{")

        db = OfferDatabase(db_path_mock)
        assert len(db.data) == 0
        assert f"Failed to parse database {toml_file_path}" in caplog.text
        assert "Starting with an empty database" in caplog.text

    def test_init_handles_pydantic_validation_error_on_load(self, db_path_mock, sample_toml_content_dict, caplog):
        """Test database handles Pydantic ValidationError if data in TOML is invalid for OfferData."""
        # Make one entry invalid (e.g., price as string)
        first_key = next(iter(sample_toml_content_dict.keys()))
        sample_toml_content_dict[first_key]["price"] = "not-a-price"

        toml_file_path = db_path_mock.with_suffix(".toml")
        with open(toml_file_path, "wb") as f:
            tomli_w.dump(sample_toml_content_dict, f)

        db = OfferDatabase(db_path_mock)
        # Depending on Pydantic behavior (raises on first or tries all),
        # db.data might be empty or partially filled if it skips bad records.
        # Current implementation seems to empty DB on any validation error during load.
        assert len(db.data) == 0
        assert f"Failed to parse database {toml_file_path}" in caplog.text # Pydantic error is caught by ValueError
        assert "Starting with an empty database" in caplog.text


    def test_save_data(self, db_path_mock, mock_offer_data_list):
        """Test saving data to TOML file."""
        db = OfferDatabase(db_path_mock) # Starts empty

        # Populate db.data
        for offer in mock_offer_data_list:
            db.data[f"http://example.com/offer/{offer.offer_id}"] = offer

        db.save()

        toml_file_path = db_path_mock.with_suffix(".toml")
        assert toml_file_path.exists()

        with open(toml_file_path, "rb") as f:
            loaded_data_raw = tomli.load(f)

        assert len(loaded_data_raw) == len(mock_offer_data_list)
        # Check if one item is correctly saved (implies others are too)
        first_offer = mock_offer_data_list[0]
        first_offer_url = f"http://example.com/offer/{first_offer.offer_id}"
        assert loaded_data_raw[first_offer_url]["title"] == first_offer.title

    def test_save_data_handles_io_error(self, db_path_mock, mock_offer_data_list, caplog):
        """Test that save handles IOErrors gracefully."""
        db = OfferDatabase(db_path_mock)
        for offer in mock_offer_data_list:
            db.data[f"http://example.com/offer/{offer.offer_id}"] = offer

        # Patch open to raise an IOError
        with patch("builtins.open", mock_open()) as mocked_open:
            mocked_open.side_effect = OSError("Disk full")
            db.save()

        assert "File I/O error saving database" in caplog.text
        assert "Disk full" in caplog.text


    def test_get_offer_found(self, db_path_mock, mock_offer_data_list):
        """Test get_offer when the offer exists."""
        db = OfferDatabase(db_path_mock) # Empty

        target_offer = mock_offer_data_list[0]
        db.data[f"http://example.com/offer/{target_offer.offer_id}"] = target_offer

        found_offer = db.get_offer(target_offer.offer_id)
        assert found_offer is not None
        assert found_offer.offer_id == target_offer.offer_id
        assert found_offer.title == target_offer.title

    def test_get_offer_not_found(self, db_path_mock, mock_offer_data_list):
        """Test get_offer when the offer does not exist."""
        db = OfferDatabase(db_path_mock) # Empty
        for offer in mock_offer_data_list: # Populate with some data
            db.data[f"http://example.com/offer/{offer.offer_id}"] = offer

        found_offer = db.get_offer("non_existent_id_123")
        assert found_offer is None

    def test_data_sorting_on_load_and_save(self, db_path_mock):
        """Test that data is sorted by listing_date (desc) after load and before save."""
        offer_old = OfferData(title="Old", price=1, views=1, listing_date=datetime(2022,1,1).isoformat(), image_url="old.jpg", offer_type="t", offer_id="old_id")
        offer_new = OfferData(title="New", price=1, views=1, listing_date=datetime(2023,1,1).isoformat(), image_url="new.jpg", offer_type="t", offer_id="new_id")
        offer_mid = OfferData(title="Mid", price=1, views=1, listing_date=datetime(2022,6,1).isoformat(), image_url="mid.jpg", offer_type="t", offer_id="mid_id")

        # Data to be written to file (unsorted by date)
        data_to_write = {
            "url_old": offer_old.model_dump(mode="json"),
            "url_new": offer_new.model_dump(mode="json"),
            "url_mid": offer_mid.model_dump(mode="json"),
        }
        toml_file_path = db_path_mock.with_suffix(".toml")
        with open(toml_file_path, "wb") as f:
            tomli_w.dump(data_to_write, f)

        # Test sorting on load
        db_loaded = OfferDatabase(db_path_mock)
        loaded_ids_in_order = [offer.offer_id for offer in db_loaded.data.values()]
        assert loaded_ids_in_order == ["new_id", "mid_id", "old_id"] # Newest first

        # Test sorting on save
        # Create a new DB, add data in a different order
        db_to_save = OfferDatabase(db_path_mock.parent / "save_test_db") # Use a different path to avoid load
        db_to_save.data = {
            "url_mid": offer_mid,
            "url_old": offer_old,
            "url_new": offer_new,
        }

        # Mock tomli_w.dump to inspect the data passed to it
        with patch("src.volante_lokalnie.volante_lokalnie.tomli_w.dump") as mock_tomli_dump:
            db_to_save.save()
            mock_tomli_dump.assert_called_once()
            args, _ = mock_tomli_dump.call_args
            data_dumped = args[0] # This is the dict passed to tomli_w.dump

            # Check the order of keys in the dumped dictionary
            dumped_ids_in_order = [offer_dict["offer_id"] for offer_dict in data_dumped.values()]
            assert dumped_ids_in_order == ["new_id", "mid_id", "old_id"]

    def test_load_empty_file(self, db_path_mock, caplog):
        """Test loading an empty TOML file."""
        toml_file_path = db_path_mock.with_suffix(".toml")
        with open(toml_file_path, "w") as f:
            f.write("") # Empty file

        db = OfferDatabase(db_path_mock)
        assert len(db.data) == 0
        # An empty file is valid TOML (empty table) but might log a parse error if tomli expects non-empty.
        # tomli.loads("") results in {}, so this should be fine.
        # No error should be logged for an empty file if it's valid TOML.
        # Let's check if any error IS logged.
        assert not any(level in caplog.text for level in ["ERROR", "CRITICAL"])
        assert f"Loaded 0 offers from {toml_file_path}" in caplog.text # or similar debug message for 0 items

    # TODO: Test case for when file_path.exists() is true but reading it fails for other IO reasons (permissions?)
    # This is harder to mock reliably without more specific mocks of Path object methods.
    # The current FileNotFoundError and general Exception catch-alls in load() provide some coverage.

    # TODO: Test case for save() when tomli_w.dump itself raises an unexpected error.
    # The current general Exception catch-all in save() provides some coverage.
pytest_plugins = ["pytester"]
