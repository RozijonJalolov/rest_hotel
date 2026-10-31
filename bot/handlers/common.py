import html
import logging
from pathlib import Path
from typing import Optional
from aiogram import F, Router
from aiogram.filters import Command, CommandStart, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardRemove,
)
from api_client import ApiClientError, ApiNetworkError, HotelApiClient
from keyboards import (
    get_cancel_keyboard,
    get_date_keyboard,
    get_main_menu_keyboard,
    get_room_selection_keyboard,
)
from texts import (
    BTN_HOTEL_INFO,
    BTN_LOOKUP,
    MSG_START_WELCOME,
    format_booking_summary,
    format_hotel_info,
    get_api_unavailable_message,
)
from utils import normalize_phone, parse_deep_link

logger = logging.getLogger(__name__)
router = Router(name="common")


class LookupState(StatesGroup):
    waiting_for_code = State()
    waiting_for_phone = State()


@router.message(CommandStart(), StateFilter("*"))
async def handle_start(
    message: Message,
    command: CommandObject,
    state: FSMContext,
    api_client: HotelApiClient,
):
    await state.clear()
    payload = command.args

    if payload:
        parsed = parse_deep_link(payload)
        if parsed:
            action, data = parsed
            if action == "room":
                # Forward to date selection for this room
                room_key = data["key"]
                try:
                    room = await api_client.get_room(room_key)
                    if not room:
                        # Unknown room, fallback to menu
                        await message.answer(
                            "Tanlangan xona topilmadi. Marhamat, roʻyxatdan tanlang:",
                            reply_markup=get_main_menu_keyboard(),
                        )
                        return

                    from handlers.booking import BookingState

                    await state.set_state(BookingState.waiting_for_date)
                    await state.update_data(
                        room_key=room_key,
                        room_name=room.get("name", room_key),
                        room_price=room.get("price_per_night", 0),
                    )
                    await message.answer(
                        f"🛏 <b>{html.escape(room.get('name', room_key))}</b> xonasi tanlandi.\n\n"
                        "Iltimos, mehmonxonaga kelish (kirish) sanangizni kiriting:\n"
                        "«Bugun», «Ertaga» tugmalarini bosing yoki sanani <b>DD.MM.YYYY</b> formatida yozing (masalan: 15.11.2026).",
                        reply_markup=get_date_keyboard(),
                        parse_mode="HTML",
                    )
                    return
                except (ApiClientError, ApiNetworkError):
                    # In case of API failure fallback to menu
                    pass

            elif action == "booking":
                room_key = data["key"]
                checkin = data["checkin"]
                nights = data["nights"]
                try:
                    # Check room and availability
                    avail = await api_client.check_availability(room_key, checkin, nights)
                    if avail.get("available"):
                        room = await api_client.get_room(room_key)
                        from handlers.booking import BookingState

                        await state.set_state(BookingState.waiting_for_name)
                        await state.update_data(
                            room_key=room_key,
                            room_name=room.get("name", room_key),
                            checkin=checkin,
                            nights=nights,
                            price_per_night=avail.get("price_per_night"),
                            total=avail.get("total"),
                        )
                        await message.answer(
                            f"🛏 <b>{html.escape(room.get('name', room_key))}</b> xonasi tanlandi.\n"
                            f"📅 Kirish sanasi: {checkin}\n"
                            f"🌙 Kechalar soni: {nights}\n\n"
                            "Xona boʻsh! Bron qilish uchun pasportingiz rasmini yuboring (yoki maʼlumotlarni yozing):",
                            reply_markup=get_cancel_keyboard(),
                            parse_mode="HTML",
                        )
                        return
                    else:
                        hotel = None
                        try:
                            hotel = await api_client.get_hotel()
                        except Exception:
                            pass
                        hotel_phone = (hotel or {}).get("phone", "")
                        phone_suffix = f"\n\n📞 Aloqa: {hotel_phone}" if hotel_phone else ""
                        await message.answer(
                            f"Afsuski, tanlangan sanalarda ({checkin}, {nights} kecha) bu xona band.{phone_suffix}\n"
                            "Iltimos, boshqa sanani yoki boshqa xonani tanlang.",
                            reply_markup=get_main_menu_keyboard(),
                        )
                        return
                except (ApiClientError, ApiNetworkError):
                    pass

    # Default fallback welcome
    await message.answer(MSG_START_WELCOME, reply_markup=get_main_menu_keyboard())


@router.message(F.text == BTN_HOTEL_INFO, StateFilter("*"))
async def handle_hotel_info(message: Message, state: FSMContext, api_client: HotelApiClient):
    await state.clear()
    try:
        hotel = await api_client.get_hotel()
        text = format_hotel_info(hotel)
        cover_url = hotel.get("image_url")
        video_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🎬 Video sayohatni koʻrish",
                        callback_data="view_hotel_video",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📸 Instagram sahifamiz",
                        url="https://www.instagram.com/sam_rest_hotel/",
                    )
                ],
            ]
        )
        if cover_url:
            from handlers.rooms import _download_image

            sent = False
            try:
                await message.answer_photo(
                    photo=cover_url,
                    caption=text,
                    parse_mode="HTML",
                    reply_markup=video_kb,
                )
                sent = True
            except Exception:
                pass

            if not sent:
                img_bytes = await _download_image(cover_url)
                if img_bytes:
                    try:
                        file = BufferedInputFile(img_bytes, filename="hotel_exterior.jpg")
                        await message.answer_photo(
                            photo=file,
                            caption=text,
                            parse_mode="HTML",
                            reply_markup=video_kb,
                        )
                        sent = True
                    except Exception:
                        pass

            if not sent:
                await message.answer(
                    text, parse_mode="HTML", reply_markup=video_kb
                )
        else:
            await message.answer(
                text, parse_mode="HTML", reply_markup=video_kb
            )
    except (ApiClientError, ApiNetworkError):
        msg = get_api_unavailable_message(api_client.last_known_hotel_phone)
        await message.answer(msg, reply_markup=get_main_menu_keyboard())


@router.message(F.text == BTN_LOOKUP, StateFilter("*"))
async def handle_lookup_start(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(LookupState.waiting_for_code)
    await message.answer(
        "🔎 <b>Bronni topish</b>\n\n"
        "Iltimos, bron kodini kiriting (masalan: <code>BR-12345</code>):",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML",
    )


@router.message(LookupState.waiting_for_code)
async def handle_lookup_code(message: Message, state: FSMContext):
    code = (message.text or "").strip().upper()
    if not code or len(code) < 3:
        await message.answer("Iltimos, toʻgʻri bron kodini kiriting:")
        return

    await state.update_data(lookup_code=code)
    await state.set_state(LookupState.waiting_for_phone)
    await message.answer(
        "Endi bron paytida koʻrsatilgan telefon raqamini kiriting (masalan: <code>+998901234567</code>):",
        parse_mode="HTML",
    )


@router.message(LookupState.waiting_for_phone)
async def handle_lookup_phone(
    message: Message,
    state: FSMContext,
    api_client: HotelApiClient,
):
    phone = normalize_phone(message.text or "")
    if not phone:
        await message.answer(
            "Telefon raqami notoʻgʻri. Iltimos, 9 ta raqam yoki +998 bilan kiriting (masalan: 901234567):"
        )
        return

    data = await state.get_data()
    code = data.get("lookup_code", "")
    await state.clear()

    try:
        booking = await api_client.lookup_booking(code, phone)
        summary = format_booking_summary(booking)
        await message.answer(
            f"✅ <b>Bron maʼlumotlari:</b>\n\n{summary}",
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard(),
        )
    except ApiClientError as err:
        if err.code == "not_found":
            await message.answer(
                "❌ Bunday bron topilmadi. Kod va telefon raqamini tekshirib, qayta urinib koʻring.",
                reply_markup=get_main_menu_keyboard(),
            )
        else:
            await message.answer(err.message, reply_markup=get_main_menu_keyboard())
    except ApiNetworkError:
        msg = get_api_unavailable_message(api_client.last_known_hotel_phone)
        await message.answer(msg, reply_markup=get_main_menu_keyboard())


@router.callback_query(F.data == "view_hotel_video")
async def handle_callback_video(callback: CallbackQuery):
    await callback.answer()
    video_path = Path(__file__).resolve().parent.parent / "data" / "videos" / "hotel_tour.mp4"
    if video_path.exists() and callback.message:
        file = FSInputFile(str(video_path), filename="sam_rest_hotel.mp4")
        await callback.message.answer_video(
            video=file,
            caption=(
                "🎬 <b>Sam Rest Mehmonxonasi boʻylab video sayohat</b>\n\n"
                "📍 Samarqand shahri, Shohi Zinda koʻchasi\n"
                "📞 Bron qilish: +998 88 011 00 55\n"
                "🤝 Narxlar kelishiladi va arzonlashtirib beriladi!"
            ),
            parse_mode="HTML",
        )
    elif callback.message:
        await callback.message.answer("Video hozircha mavjud emas.")


@router.message(Command("video"), StateFilter("*"))
@router.message(F.text.in_({"🎥 Video", "🎬 Video", "video", "Video"}), StateFilter("*"))
async def handle_command_video(message: Message):
    video_path = Path(__file__).resolve().parent.parent / "data" / "videos" / "hotel_tour.mp4"
    if video_path.exists():
        file = FSInputFile(str(video_path), filename="sam_rest_hotel.mp4")
        await message.answer_video(
            video=file,
            caption=(
                "🎬 <b>Sam Rest Mehmonxonasi boʻylab video sayohat</b>\n\n"
                "📍 Samarqand shahri, Shohi Zinda koʻchasi\n"
                "📞 Bron qilish: +998 88 011 00 55\n"
                "🤝 Narxlar kelishiladi va arzonlashtirib beriladi!"
            ),
            parse_mode="HTML",
        )
    else:
        await message.answer("Video hozircha mavjud emas.")
