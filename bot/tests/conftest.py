import os
import sys
from pathlib import Path
from typing import Any, Dict
import pytest

# Ensure bot/ directory is on sys.path
BOT_DIR = Path(__file__).resolve().parent.parent
if str(BOT_DIR) not in sys.path:
    sys.path.insert(0, str(BOT_DIR))

from api_client import HotelApiClient


@pytest.fixture
def sample_hotel() -> Dict[str, Any]:
    return {
        "name": "Grand Silk Road Hotel",
        "phone": "+998712000000",
        "address": "Toshkent shahri, Amir Temur koʻchasi, 15",
        "map_link": "https://maps.google.com/?q=41.311081,69.240562",
        "checkin_time": "14:00",
        "checkout_time": "12:00",
        "hours": "24/7",
    }


@pytest.fixture
def sample_room() -> Dict[str, Any]:
    return {
        "key": "deluxe",
        "name": "Deluxe Double Room",
        "description": "Keng va qulay xona barcha qulayliklar bilan.",
        "amenities": ["Wi-Fi", "Nonushta", "Konditsioner", "Smart TV"],
        "price_per_night": 600000,
        "count": 5,
        "cover_960": "https://example.com/images/deluxe_cover.jpg",
        "images": [
            {
                "id": 1,
                "alt": "Deluxe Room Bed",
                "is_cover": True,
                "urls": {
                    "480": "https://example.com/images/deluxe_480.jpg",
                    "960": "https://example.com/images/deluxe_960.jpg",
                    "1600": "https://example.com/images/deluxe_1600.jpg",
                },
            }
        ],
    }


@pytest.fixture
def sample_room_no_photo() -> Dict[str, Any]:
    return {
        "key": "standard",
        "name": "Standard Single Room",
        "description": "Bir kishilik qulay standart xona.",
        "amenities": ["Wi-Fi", "Konditsioner"],
        "price_per_night": 350000,
        "count": 10,
        "cover_960": None,
        "images": [],
    }


@pytest.fixture
def sample_payment() -> Dict[str, Any]:
    return {
        "card_number": "8600123456789012",
        "card_owner": "ALISHER USMONOV",
    }


@pytest.fixture
def sample_booking() -> Dict[str, Any]:
    return {
        "id": 101,
        "code": "BR-98765",
        "room": "deluxe",
        "room_name": "Deluxe Double Room",
        "checkin": "2026-11-10",
        "checkout": "2026-11-12",
        "nights": 2,
        "total": 1200000,
        "status": "pending",
        "source": "bot",
        "name": "Aziz Rahimov",
        "phone": "+998901234567",
        "created_at": "2026-10-31T20:00:00+05:00",
        "hold_until": "2026-10-31T20:30:00+05:00",
    }


@pytest.fixture
def mock_api_client():
    return HotelApiClient(
        base_url="https://hotel-api.example.com",
        api_key="test_secret_key_xyz",
        timeout=5.0,
    )
