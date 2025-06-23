import pytest
from pydantic import ValidationError
from src.volante_lokalnie.volante_lokalnie import OfferData # Assuming OfferData is accessible here
from datetime import datetime

def test_offer_data_creation_valid():
    """Test successful creation of OfferData with valid data."""
    now_iso = datetime.now().isoformat()
    data = {
        "title": "Test Offer",
        "price": 100.50,
        "views": 10,
        "listing_date": now_iso,
        "image_url": "http://example.com/image.jpg",
        "offer_type": "Buy Now",
        "offer_id": "12345",
        "title_new": "New Test Offer",
        "desc": "Original description",
        "desc_new": "New description",
        "published": False,
    }
    offer = OfferData(**data)
    for key, value in data.items():
        assert getattr(offer, key) == value

def test_offer_data_defaults():
    """Test default values for optional fields."""
    now_iso = datetime.now().isoformat()
    required_data = {
        "title": "Test Offer",
        "price": 100.50,
        "views": 10,
        "listing_date": now_iso,
        "image_url": "http://example.com/image.jpg",
        "offer_type": "Buy Now",
        "offer_id": "12345",
    }
    offer = OfferData(**required_data)
    assert offer.title_new == ""
    assert offer.desc == ""
    assert offer.desc_new == ""
    assert offer.published is False

def test_offer_data_invalid_price_type():
    """Test ValidationError when price is not a float."""
    now_iso = datetime.now().isoformat()
    with pytest.raises(ValidationError):
        OfferData(
            title="Test Offer",
            price="not-a-float", # Invalid type
            views=10,
            listing_date=now_iso,
            image_url="http://example.com/image.jpg",
            offer_type="Buy Now",
            offer_id="12345",
        )

def test_offer_data_missing_title():
    """Test ValidationError when a required field (e.g., title) is missing."""
    now_iso = datetime.now().isoformat()
    with pytest.raises(ValidationError) as excinfo:
        OfferData(
            # title is missing
            price=100.50,
            views=10,
            listing_date=now_iso,
            image_url="http://example.com/image.jpg",
            offer_type="Buy Now",
            offer_id="12345",
        )
    assert "title" in str(excinfo.value).lower()


def test_offer_data_price_can_be_int():
    """Test that price can be an integer (Pydantic will convert to float)."""
    now_iso = datetime.now().isoformat()
    offer = OfferData(
        title="Test Offer",
        price=100, # Integer price
        views=10,
        listing_date=now_iso,
        image_url="http://example.com/image.jpg",
        offer_type="Buy Now",
        offer_id="12345",
    )
    assert offer.price == 100.0
    assert isinstance(offer.price, float)

def test_offer_data_views_can_be_float_if_whole_number():
    """Test that views can be a float if it's a whole number (Pydantic will convert to int)."""
    # This behavior depends on Pydantic's strict mode or type coercion rules.
    # By default, Pydantic v2 is more strict. Let's test if 'int' type allows float if it's whole.
    # For `views: int`, Pydantic v2 in strict mode would reject 10.0.
    # In non-strict (default), it might coerce if it's a whole number.
    now_iso = datetime.now().isoformat()

    # Test with a whole float
    offer = OfferData(
        title="Test Offer",
        price=100.0,
        views=10.0, # Float but whole number
        listing_date=now_iso,
        image_url="http://example.com/image.jpg",
        offer_type="Buy Now",
        offer_id="12345",
    )
    assert offer.views == 10
    assert isinstance(offer.views, int)

    # Test with a non-whole float - this should fail for `views: int`
    with pytest.raises(ValidationError):
        OfferData(
            title="Test Offer",
            price=100.0,
            views=10.5, # Non-whole float
            listing_date=now_iso,
            image_url="http://example.com/image.jpg",
            offer_type="Buy Now",
            offer_id="12345",
        )

# TODO: Add more tests if there are specific validation rules in OfferData,
# e.g., for offer_id format, image_url format, date string format (though Pydantic handles ISO well).
# For now, OfferData is straightforward.
