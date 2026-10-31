import html
import logging
from typing import Optional
from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from api_client import ApiClientError, ApiNetworkError, HotelApiClient
from keyboards import (
    get_main_menu_keyboard,
    get_my_booking_actions_keyboard,
    get_payment_inline_keyboard,
    get_share_contact_lookup_keyboard,
)
from texts import (
    BTN_MY_BOOKINGS,
    BTN_SHARE_PHONE_LOOKUP,
    STATUS_EMOJI,
    STATUS_LABELS,
    format_payment_message,
    get_api_unavailable_message,
)
from utils import (
    format_date_uz,
    format_money,
    get_verified_phone,
    normalize_phone,
    save_verified_phone,
)

logger = logging.getLogger(__name__)
router = Router(name="my_bookings")


async def _render_my_bookings(
    target_msg: Message,
    telegram_id: int,
    api_client: HotelApiClient,
) -> None:
    verified_phone = get_verified_phone(telegram_id)
    try:
        bookings = await api_client.get_my_bookings(telegram_id, verified_phone)
    except (ApiClientError, ApiNetworkError):
        msg = get_api_unavailable_message(api_client.last_known_hotel_phone)
        await target_msg.answer(msg, reply_markup=get_main_menu_keyboard())
        return

    if not bookings:
        extra_hint = ""
        reply_kb = get_main_menu_keyboard()
        if not verified_phone:
            extra_hint = (
                "\n\n💡 <i>Veb-sayt orqali qilingan bronlaringizni ham koʻrish uchun, "
                "quyidagi tugma orqali telefon raqamingizni ulashing.</i>"
            )
            reply_kb = get_share_contact_lookup_keyboard()

        await target_msg.answer(
            f"📋 Sizda hali hech qanday bron mavjud emas.{extra_hint}",
            parse_mode="HTML",
            reply_markup=reply_kb,
        )
        return

    # User has bookings
    header = "📋 <b>Sizning soʻnggi bronlaringiz:</b>\n"
    await target_msg.answer(header, parse_mode="HTML")

    for b in bookings[:5]:
        code = html.escape(str(b.get("code", "")))
        room_name = html.escape(str(b.get("room_name") or b.get("room") or ""))
        checkin = format_date_uz(b.get("checkin", ""))
        checkout = format_date_uz(b.get("checkout", ""))
        total = format_money(b.get("total", 0))
        status = b.get("status", "pending")

        emoji = STATUS_EMOJI.get(status, "⏳")
        status_label = STATUS_LABELS.get(status, status)

        card_lines = [
            f"{emoji} <b>Bron kodi:</b> <code>{code}</code>",
            f"📌 <b>Holat:</b> {status_label}",
            f"🛏 <b>Xona:</b> {room_name}",
            f"📅 <b>Sana:</b> {checkin} — {checkout}",
            f"💰 <b>Jami:</b> {total} soʻm",
        ]
        text = "\n".join(card_lines)

        if status == "pending":
            await target_msg.answer(
                text,
                parse_mode="HTML",
                reply_markup=get_my_booking_actions_keyboard(code),
            )
        else:
            await target_msg.answer(text, parse_mode="HTML")

    if not verified_phone:
        await target_msg.answer(
            "💡 <b>Eslatma:</b> Mehmonxona veb-saytida rasmiylashtirilgan barcha bronlaringizni "
            "ham shu yerda koʻrish uchun pastdagi tugma orqali telefon raqamingizni ulashing.",
            parse_mode="HTML",
            reply_markup=get_share_contact_lookup_keyboard(),
        )


@router.message(F.text == BTN_MY_BOOKINGS, StateFilter("*"))
async def handle_my_bookings_menu(
    message: Message, state: FSMContext, api_client: HotelApiClient
):
    await state.clear()
    await _render_my_bookings(message, message.from_user.id, api_client)


@router.message(F.contact, StateFilter("*"))
async def handle_share_contact_verified(
    message: Message, state: FSMContext, api_client: HotelApiClient
):
    """Handles shared contact when user presses '📞 Raqamimni ulashish'."""
    if not message.contact:
        return

    # Trust ONLY if contact.user_id == message.from_user.id
    if message.contact.user_id != message.from_user.id:
        await message.answer(
            "⚠️ Faqat oʻzingizning Telegram profilingizga biriktirilgan raqamni ulashishingiz mumkin.",
            reply_markup=get_main_menu_keyboard(),
        )
        return

    phone = normalize_phone(message.contact.phone_number)
    if not phone:
        await message.answer(
            "Telefon raqami formati notoʻgʻri.",
            reply_markup=get_main_menu_keyboard(),
        )
        return

    save_verified_phone(message.from_user.id, phone)
    await message.answer(
        f"✅ Telefon raqamingiz ({phone}) muvaffaqiyatli tasdiqlandi va biriktirildi!\n"
        "Endi veb-saytdagi va botdagi barcha bronlaringiz koʻrinadi.",
        reply_markup=get_main_menu_keyboard(),
    )
    # Refresh and show my bookings
    await _render_my_bookings(message, message.from_user.id, api_client)


@router.callback_query(F.data.startswith("pay:"), StateFilter("*"))
async def handle_payment_details_callback(
    callback: CallbackQuery, state: FSMContext, api_client: HotelApiClient
):
    await callback.answer()
    code = callback.data.split(":", 1)[1]

    try:
        resp = await api_client.get_payment(code, telegram_id=callback.from_user.id)
    except ApiClientError as exc:
        if callback.message:
            await callback.message.answer(exc.message)
        return
    except ApiNetworkError:
        msg = get_api_unavailable_message(api_client.last_known_hotel_phone)
        if callback.message:
            await callback.message.answer(msg)
        return

    booking = resp.get("booking", {})
    payment = resp.get("payment", {})

    hotel = None
    try:
        hotel = await api_client.get_hotel()
    except Exception:
        pass

    # Switch to waiting_for_receipt state for this booking code
    from handlers.booking import BookingState

    await state.set_state(BookingState.waiting_for_receipt)
    await state.update_data(booking_code=code)

    text = format_payment_message(booking, payment, hotel)
    if callback.message:
        await callback.message.answer(
            text,
            parse_mode="HTML",
            reply_markup=get_payment_inline_keyboard(code),
        )
