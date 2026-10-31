import html
from keyboards import (
    get_admin_decision_keyboard,
    get_contact_request_keyboard,
    get_date_keyboard,
    get_main_menu_keyboard,
    get_my_booking_actions_keyboard,
    get_nights_keyboard,
    get_payment_inline_keyboard,
    get_room_inline_keyboard,
    get_room_selection_keyboard,
    get_share_contact_lookup_keyboard,
)
from texts import (
    BTN_ADMIN_APPROVE,
    BTN_ADMIN_REJECT,
    BTN_CANCEL_BOOKING,
    BTN_HOTEL_INFO,
    BTN_LOOKUP,
    BTN_MAKE_BOOKING,
    BTN_MY_BOOKINGS,
    BTN_PAYMENT_DETAILS,
    BTN_ROOM_BOOK,
    BTN_ROOM_MORE_PHOTOS,
    BTN_ROOMS,
    BTN_SEND_PHONE,
    BTN_SHARE_PHONE_LOOKUP,
    format_booking_summary,
    format_hotel_info,
    format_payment_message,
    format_room_caption,
    format_upcoming_admin_item,
)


def test_payment_message_exact_template(sample_booking, sample_payment, sample_hotel):
    msg = format_payment_message(sample_booking, sample_payment, sample_hotel)

    # Check key phrases and exact styling
    assert "💳 <b>Toʻlovni amalga oshirish</b>" in msg
    assert "🏨 Xona: Deluxe Double Room" in msg
    assert "📅 Kirish: 10.11.2026 (14:00)" in msg
    assert "📅 Chiqish: 12.11.2026 (12:00)" in msg
    assert "🌙 Kechalar: 2" in msg
    assert "💰 <b>Jami: 1 200 000 soʻm</b>" in msg
    assert "🔖 Bron kodi: <code>BR-98765</code>" in msg
    assert "💳 <b>Toʻlov maʼlumotlari:</b>" in msg
    assert "💳 Karta: <code>8600 1234 5678 9012</code>" in msg
    assert "👤 Karta egasi: <b>ALISHER USMONOV</b>" in msg
    assert "⚠️ <b>Koʻrsatma:</b>" in msg
    assert "1. Jami summani kartaga oʻtkazing." in msg
    assert "2. Toʻlov chekini (skrinshot) shu yerga yuboring." in msg
    assert "3. Administrator chekni tekshirib, broningizni tasdiqlaydi. ⚡" in msg
    assert "daqiqa ajratib qoʻyildi." in msg

    # Check dynamic escaping
    evil_booking = dict(sample_booking)
    evil_booking["room_name"] = "<script>alert(1)</script>"
    evil_booking["code"] = "<b>EVIL</b>"
    evil_payment = dict(sample_payment)
    evil_payment["card_owner"] = "Evil & Co <bad>"

    evil_msg = format_payment_message(evil_booking, evil_payment, sample_hotel)
    assert "<script>" not in evil_msg
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in evil_msg
    assert "<b>EVIL</b>" not in evil_msg
    assert "&lt;b&gt;EVIL&lt;/b&gt;" in evil_msg
    assert "Evil &amp; Co &lt;bad&gt;" in evil_msg


def test_typography_uzbek_characters():
    # Verify proper characters U+02BB (ʻ) and U+02BC (ʼ)
    texts_to_check = [
        BTN_MAKE_BOOKING,
        BTN_MY_BOOKINGS,
        BTN_HOTEL_INFO,
        BTN_LOOKUP,
        BTN_ROOM_MORE_PHOTOS,
        BTN_SHARE_PHONE_LOOKUP,
        BTN_PAYMENT_DETAILS,
        BTN_ADMIN_APPROVE,
        BTN_ADMIN_REJECT,
    ]
    for txt in texts_to_check:
        # Should not contain standard straight quote ' or backtick ` for oʻ/gʻ/maʼlumot
        assert "`" not in txt, f"Backtick found in {txt}"


def test_hotel_info_formatting(sample_hotel):
    text = format_hotel_info(sample_hotel)
    assert "Grand Silk Road Hotel" in text
    assert "+998712000000" in text
    assert "Toshkent shahri" in text
    assert "24/7" in text
    assert '<a href="https://maps.google.com/?q=41.311081,69.240562">Xaritada koʻrish</a>' in text


def test_room_caption_formatting(sample_room):
    text = format_room_caption(sample_room)
    assert "Deluxe Double Room" in text
    assert "Wi-Fi" in text
    assert "600 000 soʻm / kecha" in text


def test_booking_summary_formatting(sample_booking):
    text = format_booking_summary(sample_booking)
    assert "BR-98765" in text
    assert "Deluxe Double Room" in text
    assert "10.11.2026 — 12.11.2026" in text
    assert "1 200 000 soʻm" in text
    assert "Aziz Rahimov (+998901234567)" in text


def test_upcoming_admin_formatting(sample_booking):
    text = format_upcoming_admin_item(sample_booking)
    assert "BR-98765" in text
    assert "Deluxe Double Room" in text
    assert "Aziz Rahimov (+998901234567)" in text


def test_keyboards_structure(sample_room):
    menu_kb = get_main_menu_keyboard()
    assert len(menu_kb.keyboard) >= 3

    date_kb = get_date_keyboard()
    assert len(date_kb.keyboard[0]) == 2

    nights_kb = get_nights_keyboard()
    assert len(nights_kb.keyboard) >= 3

    contact_kb = get_contact_request_keyboard()
    assert contact_kb.keyboard[0][0].request_contact is True

    share_kb = get_share_contact_lookup_keyboard()
    assert share_kb.keyboard[0][0].request_contact is True

    room_kb = get_room_inline_keyboard("deluxe")
    assert room_kb.inline_keyboard[0][0].callback_data == "book:deluxe"
    assert room_kb.inline_keyboard[0][1].callback_data == "photos:deluxe"

    room_sel_kb = get_room_selection_keyboard([sample_room])
    assert room_sel_kb.inline_keyboard[0][0].callback_data == "sel_room:deluxe"

    pay_kb = get_payment_inline_keyboard("BR-98765")
    assert pay_kb.inline_keyboard[0][0].callback_data == "cancel:BR-98765"

    my_b_kb = get_my_booking_actions_keyboard("BR-98765")
    assert my_b_kb.inline_keyboard[0][0].callback_data == "pay:BR-98765"
    assert my_b_kb.inline_keyboard[0][1].callback_data == "cancel:BR-98765"

    admin_kb = get_admin_decision_keyboard(101)
    assert admin_kb.inline_keyboard[0][0].callback_data == "ok:101"
    assert admin_kb.inline_keyboard[0][1].callback_data == "no:101"
