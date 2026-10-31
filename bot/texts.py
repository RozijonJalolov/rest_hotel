import html
from typing import Any, Dict, List, Optional
from utils import (
    calculate_minutes_left,
    format_card_number,
    format_date_uz,
    format_money,
)

# Shared Uzbek Latin typographic marks:
# ʻ (U+02BB) for oʻ and gʻ
# ʼ (U+02BC) for glottal stop (maʼlumot)

# Main reply menu buttons
BTN_MAKE_BOOKING = "📅 Bron qilish"
BTN_ROOMS = "🛏 Xonalar"
BTN_MY_BOOKINGS = "📋 Mening bronlarim"
BTN_HOTEL_INFO = "📍 Manzil va aloqa"
BTN_LOOKUP = "🔎 Bronni kod bilan topish"

# Inline room buttons
BTN_ROOM_BOOK = "📅 Bron qilish"
BTN_ROOM_MORE_PHOTOS = "📷 Koʻproq rasm"

# Date options
BTN_DATE_TODAY = "Bugun"
BTN_DATE_TOMORROW = "Ertaga"

# Phone options
BTN_SEND_PHONE = "📞 Raqamimni yuborish"
BTN_SHARE_PHONE_LOOKUP = "📞 Raqamimni ulashish"

# Payment inline buttons
BTN_PAYMENT_DETAILS = "💳 Toʻlov maʼlumotlari"
BTN_CANCEL_BOOKING = "❌ Bekor qilish"

# Admin decision buttons
BTN_ADMIN_APPROVE = "✅ Tasdiqlash"
BTN_ADMIN_REJECT = "❌ Rad etish"

# Status badges and labels
STATUS_LABELS = {
    "pending": "⏳ Toʻlov kutilmoqda",
    "waiting_admin": "🔎 Chek tekshirilmoqda",
    "confirmed": "✅ Tasdiqlangan",
    "rejected": "❌ Rad etilgan",
    "cancelled": "🚫 Bekor qilingan",
    "expired": "⌛ Muddati oʻtgan",
}

STATUS_EMOJI = {
    "pending": "⏳",
    "waiting_admin": "🔎",
    "confirmed": "✅",
    "rejected": "❌",
    "cancelled": "🚫",
    "expired": "⌛",
}

# API error message mappings
API_ERROR_MESSAGES = {
    "validation_error": "Yuborilgan maʼlumotlarda xatolik bor. Iltimos, qaytadan tekshirib koʻring.",
    "unavailable": "Afsuski, tanlangan sanalarda bu xona band. Iltimos, boshqa sanalarni yoki boshqa xonani tanlang.",
    "not_found": "Maʼlumot topilmadi.",
    "forbidden": "Ushbu amalni bajarish uchun sizda yetarli ruxsat yoʻq.",
    "wrong_status": "Bron hozirgi holatida bu amalni bajarib boʻlmaydi.",
    "expired": "Bron muddati oʻtib ketgan va xona boʻshatilgan.",
    "already_decided": "Ushbu bron boʻyicha allaqachon qaror qabul qilingan.",
    "rate_limited": "Soʻrovlar juda koʻp. Iltimos, birozdan keyin urinib koʻring.",
    "invalid_file": "Chek fayli notoʻgʻri. Faqat JPG, PNG yoki PDF formatdagi, hajmi 5 MB gacha boʻlgan fayl yuboring.",
}

# General messages
MSG_START_WELCOME = (
    "Assalomu alaykum! Mehmonxonamizning rasmiy botiga xush kelibsiz.\n\n"
    "Quyidagi menyu orqali xonalarni koʻrishingiz, bron qilishingiz yoki mavjud bronlaringizni tekshirishingiz mumkin."
)

MSG_API_UNAVAILABLE = (
    "Tizim vaqtincha ishlamayapti. Birozdan keyin urinib koʻring"
)

MSG_GLOBAL_ERROR = "Xatolik yuz berdi, qayta urinib koʻring."

MSG_PERMISSION_DENIED = "Ruxsat yoʻq"


def get_api_unavailable_message(hotel_phone: Optional[str] = None) -> str:
    """Returns fallback message with hotel phone if known."""
    if hotel_phone:
        return f"{MSG_API_UNAVAILABLE}.\n\n📞 Aloqa uchun: {html.escape(hotel_phone)}"
    return MSG_API_UNAVAILABLE


def format_payment_message(
    booking: Dict[str, Any],
    payment: Dict[str, Any],
    hotel: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Formats the exact payment instructions message as specified in the contract.
    Dynamic fields are HTML-escaped.
    """
    room_name = html.escape(str(booking.get("room_name") or booking.get("room") or ""))
    checkin_iso = booking.get("checkin", "")
    checkout_iso = booking.get("checkout", "")
    checkin_formatted = format_date_uz(checkin_iso)
    checkout_formatted = format_date_uz(checkout_iso)

    checkin_time = (hotel or {}).get("checkin_time", "14:00")
    checkout_time = (hotel or {}).get("checkout_time", "12:00")

    nights = booking.get("nights", 1)
    total_val = booking.get("total", 0)
    total_formatted = format_money(total_val)
    code = html.escape(str(booking.get("code", "")))

    raw_card = payment.get("card_number", "")
    card_formatted = html.escape(format_card_number(raw_card))
    card_owner = html.escape(str(payment.get("card_owner", "")))

    hold_until = booking.get("hold_until", "")
    minutes_left = calculate_minutes_left(hold_until)

    return (
        "💳 <b>Toʻlovni amalga oshirish</b>\n\n"
        f"🏨 Xona: {room_name}\n"
        f"📅 Kirish: {checkin_formatted} ({checkin_time})\n"
        f"📅 Chiqish: {checkout_formatted} ({checkout_time})\n"
        f"🌙 Kechalar: {nights}\n"
        f"💰 <b>Jami: {total_formatted} soʻm</b>\n"
        f"🔖 Bron kodi: <code>{code}</code>\n\n"
        "💳 <b>Toʻlov maʼlumotlari:</b>\n"
        f"💳 Karta: <code>{card_formatted}</code>\n"
        f"👤 Karta egasi: <b>{card_owner}</b>\n\n"
        "⚠️ <b>Koʻrsatma:</b>\n"
        "1. Jami summani kartaga oʻtkazing.\n"
        "2. Toʻlov chekini (skrinshot) shu yerga yuboring.\n"
        "3. Administrator chekni tekshirib, broningizni tasdiqlaydi. ⚡\n\n"
        f"⏳ Xona sizga {minutes_left} daqiqa ajratib qoʻyildi."
    )


def format_room_caption(room: Dict[str, Any]) -> str:
    """Formats HTML caption for a room item."""
    name = html.escape(str(room.get("name", "")))
    description = html.escape(str(room.get("description", "")))
    price = format_money(room.get("price_per_night", 0))

    amenities = room.get("amenities") or []
    amenities_text = ""
    if amenities:
        escaped_amenities = [f"• {html.escape(str(a))}" for a in amenities]
        amenities_text = "\n<b>Qulayliklar:</b>\n" + "\n".join(escaped_amenities) + "\n"

    return (
        f"🛏 <b>{name}</b>\n\n"
        f"{description}\n"
        f"{amenities_text}\n"
        f"💵 <b>Narxi:</b> {price} soʻm / kecha"
    )


def format_hotel_info(hotel: Dict[str, Any]) -> str:
    """Formats HTML representation of hotel contact info."""
    name = html.escape(str(hotel.get("name", "Mehmonxona")))
    phone = html.escape(str(hotel.get("phone", "")))
    address = html.escape(str(hotel.get("address", "")))
    checkin_time = html.escape(str(hotel.get("checkin_time", "14:00")))
    checkout_time = html.escape(str(hotel.get("checkout_time", "12:00")))
    hours = html.escape(str(hotel.get("hours", "24/7")))
    map_link = hotel.get("map_link", "")

    map_section = ""
    if map_link:
        map_section = f'\n\n📍 <a href="{html.escape(map_link)}">Xaritada koʻrish</a>'

    return (
        f"🏨 <b>{name}</b>\n\n"
        f"📍 <b>Manzil:</b> {address}\n"
        f"📞 <b>Bron qilish uchun telefon:</b> {phone}\n"
        f"⏰ <b>Ish vaqti:</b> {hours}\n"
        f"🕒 <b>Kirish (check-in):</b> {checkin_time}\n"
        f"🕛 <b>Chiqish (check-out):</b> {checkout_time}\n\n"
        "⚠️ <b>Muhim tartib-qoidalar:</b>\n"
        "• Nikohsiz (FHDYo guvohnomasisiz) erkak va ayol birga qoʻyilmaydi!\n"
        "• 2 nafar erkak boʻlsa FHDYo talab etilmaydi (faqat pasport maʼlumotlari kerak boʻladi)."
        f"{map_section}"
    )


def format_booking_summary(b: Dict[str, Any]) -> str:
    """Formats a single booking item for the list or lookup."""
    code = html.escape(str(b.get("code", "")))
    room_name = html.escape(str(b.get("room_name") or b.get("room") or ""))
    checkin = format_date_uz(b.get("checkin", ""))
    checkout = format_date_uz(b.get("checkout", ""))
    nights = b.get("nights", 1)
    total = format_money(b.get("total", 0))
    status_raw = b.get("status", "pending")
    status_text = STATUS_LABELS.get(status_raw, status_raw)

    guest_name = html.escape(str(b.get("name", "")))
    guest_phone = html.escape(str(b.get("phone", "")))

    lines = [
        f"🔖 <b>Bron kodi:</b> <code>{code}</code>",
        f"📌 <b>Holat:</b> {status_text}",
        f"🛏 <b>Xona:</b> {room_name}",
        f"📅 <b>Sana:</b> {checkin} — {checkout} ({nights} kecha)",
        f"💰 <b>Jami:</b> {total} soʻm",
    ]
    if guest_name:
        lines.append(f"👤 <b>Mehmon:</b> {guest_name} ({guest_phone})")

    return "\n".join(lines)


def format_upcoming_admin_item(b: Dict[str, Any]) -> str:
    """Formats an upcoming confirmed booking for admins (/bronlar)."""
    code = html.escape(str(b.get("code", "")))
    room_name = html.escape(str(b.get("room_name") or b.get("room") or ""))
    checkin = format_date_uz(b.get("checkin", ""))
    checkout = format_date_uz(b.get("checkout", ""))
    name = html.escape(str(b.get("name", "")))
    phone = html.escape(str(b.get("phone", "")))

    return (
        f"🔖 <code>{code}</code> | 🛏 {room_name}\n"
        f"📅 {checkin} — {checkout}\n"
        f"👤 {name} ({phone})\n"
    )
