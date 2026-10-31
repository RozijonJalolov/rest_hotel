from datetime import date, timedelta
from pathlib import Path
import pytest
from utils import (
    calculate_minutes_left,
    format_card_number,
    format_date_uz,
    format_money,
    get_current_date,
    get_verified_phone,
    normalize_phone,
    parse_date_input,
    parse_deep_link,
    parse_nights_input,
    save_verified_phone,
)


def test_normalize_phone():
    # 9 digits -> prefix 998
    assert normalize_phone("901234567") == "+998901234567"
    assert normalize_phone("90 123 45 67") == "+998901234567"

    # 12 digits starting with 998
    assert normalize_phone("998901234567") == "+998901234567"
    assert normalize_phone("+998 90 123 45 67") == "+998901234567"

    # Invalid cases
    assert normalize_phone("12345") is None
    assert normalize_phone("9989012345") is None  # 10 digits
    assert normalize_phone("+79001234567") is None  # starts with 7
    assert normalize_phone("") is None
    assert normalize_phone(None) is None


def test_parse_date_input():
    ref = date(2026, 11, 1)

    # Bugun / Ertaga
    d, err = parse_date_input("Bugun", reference_date=ref)
    assert d == date(2026, 11, 1) and err is None

    d, err = parse_date_input("Ertaga", reference_date=ref)
    assert d == date(2026, 11, 2) and err is None

    # Delimiters ., /, -
    d, err = parse_date_input("15.11.2026", reference_date=ref)
    assert d == date(2026, 11, 15) and err is None

    d, err = parse_date_input("15/11/2026", reference_date=ref)
    assert d == date(2026, 11, 15) and err is None

    d, err = parse_date_input("15-11-2026", reference_date=ref)
    assert d == date(2026, 11, 15) and err is None

    # 2-digit year (DD.MM.YY)
    d, err = parse_date_input("15.11.26", reference_date=ref)
    assert d == date(2026, 11, 15) and err is None

    # Past date
    d, err = parse_date_input("31.10.2026", reference_date=ref)
    assert d is None and "Oʻtib ketgan" in err

    # > 365 days
    d, err = parse_date_input("05.12.2027", reference_date=ref)
    assert d is None and "365 kun" in err

    # Invalid format / impossible date
    d, err = parse_date_input("invalid", reference_date=ref)
    assert d is None and "notoʻgʻri format" in err

    d, err = parse_date_input("31.02.2026", reference_date=ref)
    assert d is None and "mavjud emas" in err


def test_parse_nights_input():
    # Valid
    n, err = parse_nights_input("1")
    assert n == 1 and err is None

    n, err = parse_nights_input("7")
    assert n == 7 and err is None

    n, err = parse_nights_input("30")
    assert n == 30 and err is None

    # Invalid range
    n, err = parse_nights_input("0")
    assert n is None and "1 dan 30 gacha" in err

    n, err = parse_nights_input("31")
    assert n is None and "1 dan 30 gacha" in err

    # Non-digit
    n, err = parse_nights_input("uch")
    assert n is None and "butun son" in err


def test_parse_deep_link():
    ref = get_current_date()
    future = ref + timedelta(days=10)
    future_str = future.strftime("%Y%m%d")

    # room_<key>
    res = parse_deep_link("room_deluxe")
    assert res == ("room", {"key": "deluxe"})

    res = parse_deep_link("room_standard_plus")
    assert res == ("room", {"key": "standard_plus"})

    # b_<key>_<YYYYMMDD>_<nights>
    res = parse_deep_link(f"b_deluxe_{future_str}_3")
    assert res == (
        "booking",
        {
            "key": "deluxe",
            "checkin": future.strftime("%Y-%m-%d"),
            "nights": 3,
        },
    )

    # b_ with underscore in key
    res = parse_deep_link(f"b_deluxe_vip_{future_str}_2")
    assert res == (
        "booking",
        {
            "key": "deluxe_vip",
            "checkin": future.strftime("%Y-%m-%d"),
            "nights": 2,
        },
    )

    # Past date deep link
    past = ref - timedelta(days=2)
    res = parse_deep_link(f"b_deluxe_{past.strftime('%Y%m%d')}_2")
    assert res is None

    # Invalid nights
    res = parse_deep_link(f"b_deluxe_{future_str}_35")
    assert res is None

    # Random payload
    assert parse_deep_link("random_junk") is None
    assert parse_deep_link("") is None


def test_formatting_helpers():
    assert format_money(1200000) == "1 200 000"
    assert format_money(0) == "0"
    assert format_money(50000) == "50 000"

    assert format_card_number("8600123456789012") == "8600 1234 5678 9012"
    assert format_card_number("9860 1111 2222 3333") == "9860 1111 2222 3333"

    assert format_date_uz("2026-11-15") == "15.11.2026"

    # minutes left
    assert calculate_minutes_left("2099-01-01T00:00:00+05:00") > 0
    assert calculate_minutes_left("2020-01-01T00:00:00+05:00") == 0


def test_atomic_users_json(tmp_path: Path):
    test_file = tmp_path / "users.json"
    assert get_verified_phone(12345, test_file) is None

    save_verified_phone(12345, "+998901234567", test_file)
    assert get_verified_phone(12345, test_file) == "+998901234567"

    save_verified_phone(67890, "+998991112233", test_file)
    assert get_verified_phone(12345, test_file) == "+998901234567"
    assert get_verified_phone(67890, test_file) == "+998991112233"

    # Overwrite existing
    save_verified_phone(12345, "+998939998877", test_file)
    assert get_verified_phone(12345, test_file) == "+998939998877"
