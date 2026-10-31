import logging
from typing import Any, Dict, List
from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InputMediaPhoto,
    Message,
)
import httpx
from api_client import ApiClientError, ApiNetworkError, HotelApiClient
from keyboards import get_main_menu_keyboard, get_room_inline_keyboard
from texts import (
    BTN_ROOMS,
    format_room_caption,
    get_api_unavailable_message,
)

logger = logging.getLogger(__name__)
router = Router(name="rooms")


async def _download_image(url: str, timeout: float = 5.0) -> bytes | None:
    """Downloads image bytes from URL if Telegram server cannot fetch it directly."""
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.is_success and resp.content:
                return resp.content
    except Exception as exc:
        logger.debug("Failed to download image from %s: %s", url, exc)
    return None


@router.message(F.text == BTN_ROOMS, StateFilter("*"))
async def handle_rooms_list(message: Message, state: FSMContext, api_client: HotelApiClient):
    await state.clear()
    try:
        rooms = await api_client.get_rooms()
    except (ApiClientError, ApiNetworkError):
        msg = get_api_unavailable_message(api_client.last_known_hotel_phone)
        await message.answer(msg, reply_markup=get_main_menu_keyboard())
        return

    if not rooms:
        await message.answer(
            "Hozircha faol xonalar mavjud emas.",
            reply_markup=get_main_menu_keyboard(),
        )
        return

    for room in rooms:
        key = room.get("key", "")
        caption = format_room_caption(room)
        cover_url = room.get("cover_960")
        kb = get_room_inline_keyboard(key)

        if not cover_url:
            try:
                await message.answer(caption, parse_mode="HTML", reply_markup=kb)
            except Exception as e:
                logger.error("Failed to send room text: %s", e)
            continue

        sent = False
        # 1. Try URL directly
        try:
            await message.answer_photo(photo=cover_url, caption=caption, parse_mode="HTML", reply_markup=kb)
            sent = True
        except Exception as exc:
            logger.info("Telegram failed to fetch image URL directly (%s), trying download", exc)

        # 2. Try downloading bytes
        if not sent:
            img_bytes = await _download_image(cover_url)
            if img_bytes:
                try:
                    file = BufferedInputFile(img_bytes, filename=f"room_{key}.jpg")
                    await message.answer_photo(photo=file, caption=caption, parse_mode="HTML", reply_markup=kb)
                    sent = True
                except Exception as exc:
                    logger.warning("Failed to send downloaded photo: %s", exc)

        # 3. Fallback to text caption
        if not sent:
            try:
                await message.answer(caption, parse_mode="HTML", reply_markup=kb)
            except Exception as exc:
                logger.error("Failed to send room fallback message: %s", exc)


@router.callback_query(F.data.startswith("photos:"))
async def handle_room_photos(callback: CallbackQuery, api_client: HotelApiClient):
    await callback.answer()
    room_key = callback.data.split(":", 1)[1]

    try:
        room = await api_client.get_room(room_key)
    except Exception:
        room = {}

    images = room.get("images") or []
    # Collect 960px URLs (or fallback to any URL) up to 10
    photo_urls: List[str] = []
    for img in images:
        urls = img.get("urls") or {}
        url = urls.get("960") or urls.get("480") or urls.get("1600")
        if url:
            photo_urls.append(url)
        if len(photo_urls) == 10:
            break

    # If no images in images array, check cover_960
    if not photo_urls and room.get("cover_960"):
        photo_urls.append(room["cover_960"])

    if not photo_urls:
        if callback.message:
            await callback.message.answer("Ushbu xona uchun qoʻshimcha rasmlar topilmadi.")
        return

    # Try sending as media group with URLs
    sent = False
    media_url_group = [InputMediaPhoto(media=u) for u in photo_urls]
    try:
        if callback.message:
            await callback.message.answer_media_group(media=media_url_group)
            sent = True
    except Exception as exc:
        logger.info("Direct media group by URL failed (%s), downloading bytes", exc)

    if not sent:
        # Download bytes
        media_bytes_group = []
        for idx, u in enumerate(photo_urls):
            b = await _download_image(u)
            if b:
                media_bytes_group.append(
                    InputMediaPhoto(media=BufferedInputFile(b, filename=f"photo_{idx}.jpg"))
                )

        if media_bytes_group and callback.message:
            try:
                await callback.message.answer_media_group(media=media_bytes_group)
                sent = True
            except Exception as exc:
                logger.warning("Failed to send media group with bytes: %s", exc)

    if not sent and callback.message:
        await callback.message.answer("Rasmlarni yuklab boʻlmadi.")
