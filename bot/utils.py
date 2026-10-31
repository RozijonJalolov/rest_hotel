import html
import json
import os
import re
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

UZB_TZ = timezone(timedelta(hours=5))
DATA_DIR = Path(__file__).resolve().parent / "data"
USERS_FILE = DATA_DIR / "users.json"


def get_current_date() -> date:
    """Returns today's date in Uzbekistan time (+05:00)."""
    return datetime.now(UZB_TZ).date()


def get_current_datetime() -> datetime:
    """Returns current datetime in Uzbekistan time (+05:00)."""
    return datetime.now(UZB_TZ)


def normalize_phone(phone_input: str) -> Optional[str]:
    """
    Keep digits; 9 digits -> prefix 998; 12 digits starting with 998 -> ok;
    otherwise invalid; send and display as +998XXXXXXXXX.
    """
    if not phone_input or not isinstance(phone_input, str):
        return None
    digits = re.sub(r"\D", "", phone_input)
    if len(digits) == 9:
        digits = "998" + digits
    if len(digits) == 12 and digits.startswith("998"):
        return f"+{digits}"
    return None


def parse_date_input(text: str, reference_date: Optional[date] = None) -> Tuple[Optional[date], Optional[str]]:
    """
    Parses date input from text: "bugun", "ertaga", or typed DD.MM.YYYY, DD.MM.YY, DD/MM/YYYY, DD-MM-YYYY.
    Returns (parsed_date, error_message).
    Validates: not in past, not more than 365 days ahead.
    """
    ref = reference_date or get_current_date()
    t = text.strip().lower()

    target_date: Optional[date] = None

    if t in ("bugun", "today"):
        target_date = ref
    elif t in ("ertaga", "tomorrow"):
        target_date = ref + timedelta(days=1)
    else:
        # Match delimiters ., /, -
        match = re.match(r"^(\d{1,2})[./\-](\d{1,2})[./\-](\d{2,4})$", t)
        if not match:
            return None, "Sana notoʻgʻri formatda kiritildi. Masalan: 25.12.2026 yoki «Bugun», «Ertaga» tugmalaridan foydalaning."
        day, month, year_str = int(match.group(1)), int(match.group(2)), match.group(3)
        if len(year_str) == 2:
            year = 2000 + int(year_str)
        else:
            year = int(year_str)

        try:
            target_date = date(year, month, day)
        except ValueError:
            return None, "Bunday sana mavjud emas. Iltimos, toʻgʻri sanani kiriting."

    if target_date < ref:
        return None, "Oʻtib ketgan sanani tanlab boʻlmaydi. Iltimos, bugungi yoki kelgusi sanani tanlang."

    if target_date > ref + timedelta(days=365):
        return None, "Bron faqat 1 yil (365 kun) ichidagi sanalar uchun qabul qilinadi."

    return target_date, None


def parse_nights_input(text: str) -> Tuple[Optional[int], Optional[str]]:
    """
    Parses nights input (integer between 1 and 30).
    Returns (nights, error_message).
    """
    t = text.strip()
    if not t.isdigit():
        return None, "Kechalar sonini butun son sifatida kiriting (masalan, 1 yoki 3)."
    nights = int(t)
    if nights < 1 or nights > 30:
        return None, "Kechalar soni 1 dan 30 gacha boʻlishi kerak."
    return nights, None


def parse_deep_link(payload: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """
    Parses deep link payloads:
    1) room_<key> -> ("room", {"key": key})
    2) b_<key>_<YYYYMMDD>_<nights> -> ("booking", {"key": key, "checkin": "YYYY-MM-DD", "nights": nights})
    Returns None if payload is unrecognized or invalid.
    """
    if not payload:
        return None

    # Check room_<key>
    if payload.startswith("room_"):
        key = payload[len("room_") :].strip()
        if key:
            return "room", {"key": key}
        return None

    # Check b_<key>_<YYYYMMDD>_<nights>
    match = re.match(r"^b_(.+)_(\d{8})_(\d+)$", payload)
    if match:
        key = match.group(1).strip()
        date_str = match.group(2)
        nights_str = match.group(3)

        if not key or not nights_str.isdigit():
            return None

        nights = int(nights_str)
        if nights < 1 or nights > 30:
            return None

        try:
            year = int(date_str[0:4])
            month = int(date_str[4:6])
            day = int(date_str[6:8])
            d = date(year, month, day)
        except (ValueError, IndexError):
            return None

        ref = get_current_date()
        if d < ref or d > ref + timedelta(days=365):
            return None

        return "booking", {
            "key": key,
            "checkin": d.strftime("%Y-%m-%d"),
            "nights": nights,
        }

    return None


def format_money(amount: int) -> str:
    """Formats amount with space as thousands separator: 1200000 -> 1 200 000"""
    return f"{amount:,}".replace(",", " ")


def format_card_number(card: str) -> str:
    """Formats card number into groups of 4 digits: 8600123456789012 -> 8600 1234 5678 9012"""
    digits = re.sub(r"\D", "", card or "")
    chunks = [digits[i : i + 4] for i in range(0, len(digits), 4)]
    return " ".join(chunks)


def format_date_uz(date_iso: str) -> str:
    """Formats ISO date YYYY-MM-DD into DD.MM.YYYY"""
    try:
        parts = date_iso.split("-")
        if len(parts) == 3:
            return f"{parts[2]}.{parts[1]}.{parts[0]}"
    except Exception:
        pass
    return date_iso


def calculate_minutes_left(hold_until_iso: str) -> int:
    """Calculates remaining minutes until hold_until."""
    try:
        # Replace Z with +00:00 if present
        iso_str = hold_until_iso.replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso_str)
        now = datetime.now(dt.tzinfo or UZB_TZ)
        diff = (dt - now).total_seconds()
        return max(0, int(round(diff / 60)))
    except Exception:
        return 15


def get_verified_phone(telegram_id: int, file_path: Optional[Path] = None) -> Optional[str]:
    """Retrieves verified phone from users.json if present."""
    path = file_path or USERS_FILE
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get(str(telegram_id))
    except Exception:
        return None


def save_verified_phone(telegram_id: int, phone: str, file_path: Optional[Path] = None) -> None:
    """
    Atomically writes telegram_id -> verified phone mapping to users.json.
    """
    path = file_path or USERS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)

    data: Dict[str, str] = {}
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

    data[str(telegram_id)] = phone

    # Atomic write using temp file in the same directory
    dir_path = path.parent
    fd, tmp_path = tempfile.mkstemp(dir=dir_path, prefix="users_", suffix=".tmp")
    try:
        with open(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        raise
