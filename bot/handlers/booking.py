import html
import io
import logging
from typing import Optional
from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    ContentType,
    Message,
    ReplyKeyboardRemove,
)
from api_client import ApiClientError, ApiNetworkError, HotelApiClient
from keyboards import (
    get_cancel_keyboard,
    get_date_keyboard,
    get_main_menu_keyboard,
    get_nights_keyboard,
    get_payment_inline_keyboard,
    get_room_selection_keyboard,
)
from texts import (
    BTN_MAKE_BOOKING,
    MSG_PERMISSION_DENIED,
    format_payment_message,
    get_api_unavailable_message,
)
from utils import (
    normalize_phone,
    parse_date_input,
    parse_nights_input,
    save_verified_phone,
)

logger = logging.getLogger(__name__)
router = Router(name="booking")


class BookingState(StatesGroup):
    choosing_room = State()
    waiting_for_date = State()
    waiting_for_nights = State()
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_receipt = State()


@router.message(F.text == BTN_MAKE_BOOKING, StateFilter("*"))
async def handle_start_booking_menu(
    message: Message, state: FSMContext, api_client: HotelApiClient
):
    """Entry point from reply keyboard '📅 Bron qilish'."""
    await state.clear()
    try:
        rooms = await api_client.get_rooms()
    except (ApiClientError, ApiNetworkError):
        msg = get_api_unavailable_message(api_client.last_known_hotel_phone)
        await message.answer(msg, reply_markup=get_main_menu_keyboard())
        return

    if not rooms:
        await message.answer(
            "Hozircha boʻsh xonalar mavjud emas.",
            reply_markup=get_main_menu_keyboard(),
        )
        return

    await state.set_state(BookingState.choosing_room)
    await message.answer(
        "Iltimos, oʻzingizga maʼqul kelgan xonani tanlang:",
        reply_markup=get_room_selection_keyboard(rooms),
    )


@router.callback_query(F.data.startswith("book:"), StateFilter("*"))
@router.callback_query(F.data.startswith("sel_room:"), StateFilter("*"))
async def handle_room_selected(
    callback: CallbackQuery, state: FSMContext, api_client: HotelApiClient
):
    """Room selected either from room card or selection keyboard."""
    await callback.answer()
    prefix, room_key = callback.data.split(":", 1)
    await state.clear()

    try:
        room = await api_client.get_room(room_key)
    except Exception:
        room = {"key": room_key, "name": room_key, "price_per_night": 0}

    await state.set_state(BookingState.waiting_for_date)
    await state.update_data(
        room_key=room_key,
        room_name=room.get("name", room_key),
        room_price=room.get("price_per_night", 0),
    )

    room_name_esc = html.escape(room.get("name", room_key))
    if callback.message:
        await callback.message.answer(
            f"🛏 <b>{room_name_esc}</b> xonasi tanlandi.\n\n"
            "⚠️ <b>DIQQAT:</b> Mehmonxonamizga nikoh guvohnomasi (FHDYo) boʻlmagan erkak va ayol qoʻyilmaydi! "
            "2 nafar erkak boʻlsa FHDYo talab etilmaydi.\n\n"
            "Iltimos, mehmonxonaga kelish (kirish) sanangizni kiriting:\n"
            "«Bugun», «Ertaga» tugmalarini bosing yoki sanani <b>DD.MM.YYYY</b> formatida yozing (masalan: 15.11.2026).",
            reply_markup=get_date_keyboard(),
            parse_mode="HTML",
        )


@router.message(
    F.text.in_({"❌ Bekor qilish", "/cancel", "bekor qilish", "Bekor qilish"}),
    StateFilter(
        BookingState.choosing_room,
        BookingState.waiting_for_date,
        BookingState.waiting_for_nights,
        BookingState.waiting_for_name,
        BookingState.waiting_for_phone,
    ),
)
async def handle_cancel_booking_process(message: Message, state: FSMContext):
    """Cancels the ongoing booking process and restores main menu."""
    await state.clear()
    await message.answer(
        "❌ Bron qilish jarayoni bekor qilindi.",
        reply_markup=get_main_menu_keyboard(),
    )


@router.callback_query(F.data == "cancel_booking_flow", StateFilter("*"))
async def handle_cancel_booking_flow_callback(
    callback: CallbackQuery, state: FSMContext
):
    """Cancels booking from inline selection keyboard."""
    await callback.answer("Bron qilish bekor qilindi.")
    await state.clear()
    if callback.message:
        try:
            await callback.message.edit_text(
                "❌ Bron qilish bekor qilindi.", reply_markup=None
            )
        except Exception:
            pass
        await callback.message.answer(
            "Asosiy menyu:",
            reply_markup=get_main_menu_keyboard(),
        )


@router.message(BookingState.waiting_for_date)
async def handle_booking_date(message: Message, state: FSMContext):
    text = message.text or ""
    parsed_date, err = parse_date_input(text)
    if err:
        await message.answer(err, reply_markup=get_date_keyboard())
        return

    checkin_str = parsed_date.strftime("%Y-%m-%d")
    await state.update_data(checkin=checkin_str)
    await state.set_state(BookingState.waiting_for_nights)

    await message.answer(
        f"📅 Kirish sanasi: <b>{parsed_date.strftime('%d.%m.%Y')}</b> qabul qilindi.\n\n"
        "Necha kecha qolasiz? (1 dan 30 gacha son kiriting yoki tugmalardan birini tanlang):",
        reply_markup=get_nights_keyboard(),
        parse_mode="HTML",
    )


@router.message(BookingState.waiting_for_nights)
async def handle_booking_nights(
    message: Message, state: FSMContext, api_client: HotelApiClient
):
    text = message.text or ""
    nights, err = parse_nights_input(text)
    if err:
        await message.answer(err, reply_markup=get_nights_keyboard())
        return

    data = await state.get_data()
    room_key = data.get("room_key")
    checkin = data.get("checkin")

    # Check availability
    try:
        avail = await api_client.check_availability(room_key, checkin, nights)
    except (ApiClientError, ApiNetworkError):
        msg = get_api_unavailable_message(api_client.last_known_hotel_phone)
        await message.answer(msg, reply_markup=get_main_menu_keyboard())
        return

    if not avail.get("available"):
        phone = api_client.last_known_hotel_phone
        phone_txt = f"\n\n📞 Qoʻshimcha maʼlumot uchun: {phone}" if phone else ""
        await state.set_state(BookingState.waiting_for_date)
        await message.answer(
            f"Afsuski, tanlangan sanalarda bu xona band.{phone_txt}\n\n"
            "Iltimos, boshqa kirish sanasini tanlang:",
            reply_markup=get_date_keyboard(),
        )
        return

    await state.update_data(
        nights=nights,
        price_per_night=avail.get("price_per_night"),
        total=avail.get("total"),
    )
    await state.set_state(BookingState.waiting_for_name)

    await message.answer(
        "📷 <b>Pasport rasmini yuboring:</b>\n\n"
        "Iltimos, pasportingiz yoki ID-kartangiz <b>fotosuratini</b> toʻgʻridan-toʻgʻri rasm tarzida yuboring 📸\n\n"
        "⚠️ <b>Tartib-qoida:</b>\n"
        "• Nikohsiz (FHDYo guvohnomasisiz) erkak va ayol birga qoʻyilmaydi!\n"
        "• 2 nafar erkak boʻlsa, FHDYo talab etilmaydi (ikkala mehmonning ham pasport rasmi yuboriladi).\n\n"
        "<i>(Agar fotosurat boʻlmasa, maʼlumotlarni yozma tarzda kiritishingiz ham mumkin: F.I.O., tugʻilgan sanasi, manzili, millati)</i>",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML",
    )


@router.message(BookingState.waiting_for_name, F.photo | F.document | F.text)
async def handle_booking_name(message: Message, state: FSMContext):
    passport_file_id = None
    photo_list = getattr(message, "photo", None)
    doc_obj = getattr(message, "document", None)

    if photo_list and isinstance(photo_list, list) and len(photo_list) > 0:
        photo = photo_list[-1]
        passport_file_id = getattr(photo, "file_id", None)
        sender_title = (
            message.from_user.full_name
            if getattr(message, "from_user", None)
            else "Mehmon"
        )
        caption = getattr(message, "caption", None)
        name = caption.strip() if caption else f"{sender_title} (Pasport rasmi)"
    elif doc_obj and getattr(doc_obj, "file_id", None):
        passport_file_id = doc_obj.file_id
        sender_title = (
            message.from_user.full_name
            if getattr(message, "from_user", None)
            else "Mehmon"
        )
        caption = getattr(message, "caption", None)
        name = caption.strip() if caption else f"{sender_title} (Pasport hujjati)"
    else:
        name = (message.text or "").strip()
        if len(name) < 2 or len(name) > 250:
            await message.answer(
                "Iltimos, pasport rasmini yuboring yoki maʼlumotni toʻliqroq yozing:"
            )
            return

    await state.update_data(name=name)
    if passport_file_id:
        await state.update_data(passport_file_id=passport_file_id)

    await state.set_state(BookingState.waiting_for_phone)

    from keyboards import get_contact_request_keyboard

    await message.answer(
        "✅ Pasport qabul qilindi.\n\n"
        "Endi telefon raqamingizni yuboring.\n"
        "«📞 Raqamimni yuborish» tugmasini bosishingiz yoki raqamingizni yozib yuborishingiz mumkin:\n"
        "<i>(Agar ikkinchi mehmonning pasport rasmi boʻlsa, uni ham hozir yuborishingiz mumkin)</i>",
        reply_markup=get_contact_request_keyboard(),
        parse_mode="HTML",
    )


@router.message(BookingState.waiting_for_phone, F.photo | F.document)
async def handle_additional_passport(message: Message, state: FSMContext):
    """Allows uploading 2nd guest's passport photo during phone step."""
    from keyboards import get_contact_request_keyboard

    photo_list = getattr(message, "photo", None)
    doc_obj = getattr(message, "document", None)
    sec_id = None
    if photo_list and isinstance(photo_list, list) and len(photo_list) > 0:
        sec_id = photo_list[-1].file_id
    elif doc_obj:
        sec_id = getattr(doc_obj, "file_id", None)

    if sec_id:
        data = await state.get_data()
        photos = data.get("passport_photos", [])
        photos.append(sec_id)
        await state.update_data(passport_photos=photos)

    await message.answer(
        "📸 Ikkinchi pasport ham qabul qilindi!\n\n"
        "Iltimos, bronni yakunlash uchun telefon raqamingizni yuboring:",
        reply_markup=get_contact_request_keyboard(),
    )


@router.message(BookingState.waiting_for_phone, F.contact | F.text)
async def handle_booking_phone(
    message: Message, state: FSMContext, api_client: HotelApiClient
):
    data = await state.get_data()
    # Guard against double submission
    if data.get("_submitting"):
        return

    verified = False
    phone: Optional[str] = None

    if message.contact:
        # Verified ONLY if user_id == message.from_user.id
        raw_phone = message.contact.phone_number
        phone = normalize_phone(raw_phone)
        if message.contact.user_id == message.from_user.id:
            verified = True
            if phone:
                save_verified_phone(message.from_user.id, phone)
    else:
        raw_text = message.text or ""
        phone = normalize_phone(raw_text)

    if not phone:
        await message.answer(
            "Telefon raqami notoʻgʻri. Iltimos, 9 ta raqam yoki +998 bilan kiriting (masalan: 901234567):"
        )
        return

    await state.update_data(_submitting=True)

    room_key = data["room_key"]
    checkin = data["checkin"]
    nights = data["nights"]
    name = data["name"]

    try:
        resp = await api_client.create_booking(
            room=room_key,
            checkin=checkin,
            nights=nights,
            name=name,
            phone=phone,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
        )
    except ApiClientError as exc:
        await state.clear()
        if exc.code == "unavailable":
            await message.answer(
                "Afsuski, xona hozirgina boshqa mehmon tomonidan band qilindi. Iltimos, boshqa sanani yoki xonani tanlang.",
                reply_markup=get_main_menu_keyboard(),
            )
        elif exc.code == "validation_error":
            await message.answer(
                "Yuborilgan maʼlumotlarda xatolik aniqlandi. Iltimos, boshidan qaytadan urinib koʻring.",
                reply_markup=get_main_menu_keyboard(),
            )
        else:
            await message.answer(exc.message, reply_markup=get_main_menu_keyboard())
        return
    except ApiNetworkError:
        await state.clear()
        msg = get_api_unavailable_message(api_client.last_known_hotel_phone)
        await message.answer(msg, reply_markup=get_main_menu_keyboard())
        return

    # Clear previous FSM state and switch to waiting_for_receipt
    await state.clear()

    booking = resp.get("booking", {})
    payment = resp.get("payment", {})
    code = booking.get("code", "")

    # Set state waiting_for_receipt with booking_code
    await state.set_state(BookingState.waiting_for_receipt)
    await state.update_data(booking_code=code)

    hotel = None
    try:
        hotel = await api_client.get_hotel()
    except Exception:
        pass

    payment_text = format_payment_message(booking, payment, hotel)
    await message.answer(
        payment_text,
        parse_mode="HTML",
        reply_markup=get_payment_inline_keyboard(code),
    )


@router.message(F.photo | F.document, StateFilter("*"))
async def handle_receipt_upload(
    message: Message,
    state: FSMContext,
    bot: Bot,
    api_client: HotelApiClient,
):
    """
    Handles receipt upload (photo or document).
    Works in waiting_for_receipt state or recovers latest pending booking if state was lost.
    """
    data = await state.get_data()
    code = data.get("booking_code")

    # If no active booking_code in state (e.g. after restart), search latest pending booking
    if not code:
        try:
            bookings = await api_client.get_my_bookings(message.from_user.id)
            for b in bookings:
                if b.get("status") == "pending":
                    code = b.get("code")
                    break
        except Exception as exc:
            logger.warning("Failed to lookup pending bookings on restart recovery: %s", exc)

    if not code:
        await message.answer(
            "Sizda toʻlov kutilayotgan faol bron topilmadi. Yangi bron yaratish uchun quyidagi menyudan foydalaning.",
            reply_markup=get_main_menu_keyboard(),
        )
        return

    file_id: Optional[str] = None
    filename = "receipt.jpg"
    content_type = "image/jpeg"
    file_size = 0

    if message.photo:
        photo = message.photo[-1]
        file_id = photo.file_id
        file_size = photo.file_size or 0
        filename = f"receipt_{code}.jpg"
        content_type = "image/jpeg"
    elif message.document:
        doc = message.document
        file_id = doc.file_id
        file_size = doc.file_size or 0
        filename = doc.file_name or f"receipt_{code}.pdf"
        content_type = doc.mime_type or "application/octet-stream"

        # Validate allowed extensions / mime types
        lower_name = filename.lower()
        is_allowed = (
            lower_name.endswith((".jpg", ".jpeg", ".png", ".pdf"))
            or content_type in ("image/jpeg", "image/png", "application/pdf")
        )
        if not is_allowed:
            await message.answer(
                "Chek fayli notoʻgʻri. Faqat JPG, PNG yoki PDF formatdagi, hajmi 5 MB gacha boʻlgan fayl yuboring."
            )
            return

    if file_size > 5 * 1024 * 1024:
        await message.answer(
            "Fayl hajmi juda katta (maksimal 5 MB). Iltimos, kichikroq oʻlchamdagi fayl yuboring."
        )
        return

    # Download file bytes
    try:
        downloaded = await bot.download(file_id)
        if isinstance(downloaded, io.BytesIO):
            file_bytes = downloaded.getvalue()
        elif hasattr(downloaded, "read"):
            file_bytes = downloaded.read()
        else:
            file_bytes = bytes(downloaded)
    except Exception as exc:
        logger.error("Failed to download file from Telegram: %s", exc)
        await message.answer(
            "Chekni yuklab olishda xatolik yuz berdi. Iltimos, faylni qaytadan yuboring."
        )
        return

    # Upload to API
    try:
        await api_client.upload_receipt(
            code=code,
            file_bytes=file_bytes,
            filename=filename,
            content_type=content_type,
            telegram_id=message.from_user.id,
        )
        await state.clear()
        await message.answer(
            f"✅ Chek qabul qilindi. Bron {code} administrator tomonidan tekshirilmoqda, tasdiqlanishi bilan sizga xabar yuboramiz.",
            reply_markup=get_main_menu_keyboard(),
        )
    except ApiClientError as exc:
        if exc.code == "invalid_file":
            await message.answer(
                "Chek fayli notoʻgʻri. Faqat JPG, PNG yoki PDF formatdagi, hajmi 5 MB gacha boʻlgan fayl yuboring."
            )
        elif exc.code == "expired":
            await state.clear()
            await message.answer(
                "Afsuski, ushbu bron uchun ajratilgan vaqt tugagan va xona boʻshatilgan.",
                reply_markup=get_main_menu_keyboard(),
            )
        elif exc.code == "wrong_status":
            await state.clear()
            await message.answer(
                "Ushbu bron uchun chek qabul qilib boʻlmaydi (holat oʻzgargan).",
                reply_markup=get_main_menu_keyboard(),
            )
        else:
            await message.answer(exc.message, reply_markup=get_main_menu_keyboard())
    except ApiNetworkError:
        msg = get_api_unavailable_message(api_client.last_known_hotel_phone)
        await message.answer(msg, reply_markup=get_main_menu_keyboard())


@router.callback_query(F.data.startswith("cancel:"), StateFilter("*"))
async def handle_cancel_booking(
    callback: CallbackQuery, state: FSMContext, api_client: HotelApiClient
):
    await callback.answer()
    code = callback.data.split(":", 1)[1]

    try:
        await api_client.cancel_booking(code, telegram_id=callback.from_user.id)
        await state.clear()
        if callback.message:
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.message.answer(
                f"🚫 <b>{code}</b> kodi ostidagi bron muvaffaqiyatli bekor qilindi.",
                parse_mode="HTML",
                reply_markup=get_main_menu_keyboard(),
            )
    except ApiClientError as exc:
        if callback.message:
            await callback.message.answer(
                exc.message, reply_markup=get_main_menu_keyboard()
            )
    except ApiNetworkError:
        if callback.message:
            msg = get_api_unavailable_message(api_client.last_known_hotel_phone)
            await callback.message.answer(msg, reply_markup=get_main_menu_keyboard())
