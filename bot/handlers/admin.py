import html
import logging
from typing import List, Set
from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.types import CallbackQuery, Message
from api_client import ApiClientError, ApiNetworkError, HotelApiClient
from texts import MSG_PERMISSION_DENIED, format_upcoming_admin_item, get_api_unavailable_message

logger = logging.getLogger(__name__)
router = Router(name="admin")


@router.callback_query(F.data.startswith("ok:"), StateFilter("*"))
@router.callback_query(F.data.startswith("no:"), StateFilter("*"))
async def handle_admin_decision(
    callback: CallbackQuery,
    api_client: HotelApiClient,
    admin_ids: Set[int],
):
    """
    Handles inline decision buttons ok:<id> and no:<id> attached to receipt messages sent by the website.
    The bot NEVER sends decision messages to guests.
    """
    user_id = callback.from_user.id
    if user_id not in admin_ids:
        await callback.answer(MSG_PERMISSION_DENIED, show_alert=True)
        return

    data = callback.data or ""
    action_prefix, id_str = data.split(":", 1)
    if not id_str.isdigit():
        await callback.answer("Notoʻgʻri bron ID raqami.", show_alert=True)
        return

    booking_id = int(id_str)
    action = "approve" if action_prefix == "ok" else "reject"

    try:
        await api_client.admin_decision(
            booking_id=booking_id,
            action=action,
            admin_telegram_id=user_id,
        )

        admin_name = callback.from_user.full_name or callback.from_user.username or "Admin"
        status_tag = "✅ TASDIQLANDI" if action == "approve" else "❌ RAD ETILDI"

        if callback.message:
            orig_text = callback.message.caption or callback.message.text or ""
            new_text = f"{html.escape(orig_text)}\n\n{status_tag} ({html.escape(admin_name)})"

            if callback.message.caption is not None:
                await callback.message.edit_caption(
                    caption=new_text,
                    parse_mode="HTML",
                    reply_markup=None,
                )
            else:
                await callback.message.edit_text(
                    text=new_text,
                    parse_mode="HTML",
                    reply_markup=None,
                )

        await callback.answer(
            f"Bron muvaffaqiyatli {'tasdiqlandi' if action == 'approve' else 'rad etildi'}."
        )

    except ApiClientError as exc:
        if exc.code == "already_decided":
            await callback.answer(
                "Ushbu bron boʻyicha allaqachon qaror qabul qilingan.",
                show_alert=True,
            )
            # Remove buttons on already_decided
            if callback.message:
                try:
                    await callback.message.edit_reply_markup(reply_markup=None)
                except Exception:
                    pass
        elif exc.code == "unavailable":
            await callback.answer(
                "Xona boshqa mehmon tomonidan band qilingan.",
                show_alert=True,
            )
        elif exc.code == "forbidden":
            await callback.answer(MSG_PERMISSION_DENIED, show_alert=True)
        else:
            await callback.answer(f"Xatolik: {exc.message}", show_alert=True)

    except ApiNetworkError:
        msg = get_api_unavailable_message(api_client.last_known_hotel_phone)
        await callback.answer(msg, show_alert=True)


@router.message(Command("bronlar"), StateFilter("*"))
async def handle_admin_upcoming(
    message: Message,
    api_client: HotelApiClient,
    admin_ids: Set[int],
):
    """Lists confirmed upcoming bookings for admins."""
    user_id = message.from_user.id
    if user_id not in admin_ids:
        await message.answer(MSG_PERMISSION_DENIED)
        return

    try:
        bookings = await api_client.get_admin_upcoming(admin_telegram_id=user_id)
    except ApiClientError as exc:
        if exc.code == "forbidden":
            await message.answer(MSG_PERMISSION_DENIED)
        else:
            await message.answer(f"Xatolik: {exc.message}")
        return
    except ApiNetworkError:
        msg = get_api_unavailable_message(api_client.last_known_hotel_phone)
        await message.answer(msg)
        return

    if not bookings:
        await message.answer("Hozircha tasdiqlangan kelgusi bronlar yoʻq.")
        return

    lines = ["📅 <b>Kelgusi tasdiqlangan bronlar (maksimal 30):</b>\n"]
    for b in bookings[:30]:
        lines.append(format_upcoming_admin_item(b))

    await message.answer("\n".join(lines), parse_mode="HTML")
