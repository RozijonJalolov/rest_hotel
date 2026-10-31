from typing import Any, Dict
import pytest


def validate_hotel_contract(data: Dict[str, Any]):
    required_fields = {
        "name": str,
        "phone": str,
        "address": str,
        "map_link": str,
        "checkin_time": str,
        "checkout_time": str,
        "hours": str,
    }
    for field, expected_type in required_fields.items():
        assert field in data, f"Hotel missing field '{field}'"
        assert isinstance(
            data[field], expected_type
        ), f"Hotel field '{field}' must be {expected_type}, got {type(data[field])}"


def validate_room_contract(data: Dict[str, Any]):
    required_fields = {
        "key": str,
        "name": str,
        "description": str,
        "amenities": list,
        "price_per_night": int,
        "count": int,
    }
    for field, expected_type in required_fields.items():
        assert field in data, f"Room missing field '{field}'"
        assert isinstance(
            data[field], expected_type
        ), f"Room field '{field}' must be {expected_type}"

    assert "cover_960" in data, "Room missing 'cover_960'"
    assert data["cover_960"] is None or isinstance(
        data["cover_960"], str
    ), "cover_960 must be string or None"

    assert "images" in data, "Room missing 'images'"
    assert isinstance(data["images"], list)
    for img in data["images"]:
        assert "id" in img and isinstance(img["id"], int)
        assert "alt" in img and isinstance(img["alt"], str)
        assert "is_cover" in img and isinstance(img["is_cover"], bool)
        assert "urls" in img and isinstance(img["urls"], dict)
        for size in ("480", "960", "1600"):
            assert size in img["urls"], f"Missing image url size '{size}'"
            assert isinstance(img["urls"][size], str)


def validate_booking_contract(data: Dict[str, Any]):
    required_fields = {
        "id": int,
        "code": str,
        "room": str,
        "room_name": str,
        "checkin": str,
        "checkout": str,
        "nights": int,
        "total": int,
        "status": str,
        "source": str,
        "name": str,
        "phone": str,
        "created_at": str,
        "hold_until": str,
    }
    for field, expected_type in required_fields.items():
        assert field in data, f"Booking missing field '{field}'"
        assert isinstance(
            data[field], expected_type
        ), f"Booking field '{field}' must be {expected_type}, got {type(data[field])}"

    assert data["status"] in {
        "pending",
        "waiting_admin",
        "confirmed",
        "rejected",
        "cancelled",
        "expired",
    }
    assert data["source"] in {"bot", "web"}
    assert data["created_at"].endswith("+05:00")
    assert data["hold_until"].endswith("+05:00")


def validate_payment_contract(data: Dict[str, Any]):
    required_fields = {
        "card_number": str,
        "card_owner": str,
    }
    for field, expected_type in required_fields.items():
        assert field in data, f"Payment missing field '{field}'"
        assert isinstance(data[field], expected_type)


def test_contract_fixtures_shape(sample_hotel, sample_room, sample_room_no_photo, sample_booking, sample_payment):
    validate_hotel_contract(sample_hotel)
    validate_room_contract(sample_room)
    validate_room_contract(sample_room_no_photo)
    validate_booking_contract(sample_booking)
    validate_payment_contract(sample_payment)
