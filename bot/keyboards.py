from typing import Any, Dict, List
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from texts import (
    BTN_ADMIN_APPROVE,
    BTN_ADMIN_REJECT,
    BTN_CANCEL_BOOKING,
    BTN_DATE_TODAY,
    BTN_DATE_TOMORROW,
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
)
from utils import format_money


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Returns the persistent main menu reply keyboard."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_MAKE_BOOKING), KeyboardButton(text=BTN_ROOMS)],
            [KeyboardButton(text=BTN_MY_BOOKINGS)],
            [KeyboardButton(text=BTN_HOTEL_INFO), KeyboardButton(text=BTN_LOOKUP)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def get_date_keyboard() -> ReplyKeyboardMarkup:
    """Quick selection keyboard for check-in date."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_DATE_TODAY), KeyboardButton(text=BTN_DATE_TOMORROW)],
            [KeyboardButton(text="❌ Bekor qilish")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def get_nights_keyboard() -> ReplyKeyboardMarkup:
    """Quick selection keyboard for nights (1-7)."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=str(i)) for i in range(1, 4)],
            [KeyboardButton(text=str(i)) for i in range(4, 7)],
            [KeyboardButton(text="7")],
            [KeyboardButton(text="❌ Bekor qilish")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Simple keyboard with cancel button."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Bekor qilish")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def get_contact_request_keyboard() -> ReplyKeyboardMarkup:
    """Keyboard prompting user to share their contact."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_SEND_PHONE, request_contact=True)],
            [KeyboardButton(text="❌ Bekor qilish")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def get_share_contact_lookup_keyboard() -> ReplyKeyboardMarkup:
    """Keyboard prompting user to share their contact to link website bookings."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_SHARE_PHONE_LOOKUP, request_contact=True)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def get_room_inline_keyboard(room_key: str) -> InlineKeyboardMarkup:
    """Inline buttons under each room card."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=BTN_ROOM_BOOK, callback_data=f"book:{room_key}"),
                InlineKeyboardButton(text=BTN_ROOM_MORE_PHOTOS, callback_data=f"photos:{room_key}"),
            ]
        ]
    )


def get_room_selection_keyboard(rooms: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Inline keyboard listing all rooms to choose from when starting booking."""
    buttons = []
    for r in rooms:
        key = r.get("key", "")
        name = r.get("name", key)
        price = format_money(r.get("price_per_night", 0))
        label = f"{name} — {price} soʻm"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"sel_room:{key}")])
    buttons.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_booking_flow")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_payment_inline_keyboard(booking_code: str) -> InlineKeyboardMarkup:
    """Inline keyboard for a freshly generated or pending payment."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=BTN_CANCEL_BOOKING, callback_data=f"cancel:{booking_code}"
                )
            ]
        ]
    )


def get_my_booking_actions_keyboard(booking_code: str) -> InlineKeyboardMarkup:
    """Inline keyboard for an existing pending booking in my-bookings list."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=BTN_PAYMENT_DETAILS, callback_data=f"pay:{booking_code}"
                ),
                InlineKeyboardButton(
                    text=BTN_CANCEL_BOOKING, callback_data=f"cancel:{booking_code}"
                ),
            ]
        ]
    )


def get_admin_decision_keyboard(booking_id: int) -> InlineKeyboardMarkup:
    """Inline keyboard attached to receipts sent to admins."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=BTN_ADMIN_APPROVE, callback_data=f"ok:{booking_id}"
                ),
                InlineKeyboardButton(
                    text=BTN_ADMIN_REJECT, callback_data=f"no:{booking_id}"
                ),
            ]
        ]
    )
