import io
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from api_client import ApiClientError, ApiNetworkError, HotelApiClient
from handlers.booking import (
    BookingState,
    handle_booking_date,
    handle_booking_name,
    handle_booking_nights,
    handle_booking_phone,
    handle_cancel_booking,
    handle_receipt_upload,
    handle_room_selected,
    handle_start_booking_menu,
)
from utils import get_verified_phone


class DummyFSMContext:
    def __init__(self, initial_state=None, initial_data=None):
        self._state = initial_state
        self._data = dict(initial_data or {})

    async def get_state(self):
        return self._state

    async def set_state(self, state):
        self._state = state

    async def get_data(self):
        return dict(self._data)

    async def set_data(self, data):
        self._data = dict(data)

    async def update_data(self, **kwargs):
        self._data.update(kwargs)

    async def clear(self):
        self._state = None
        self._data = {}


@pytest.fixture
def mock_bot():
    bot = MagicMock()
    bot.download = AsyncMock(return_value=io.BytesIO(b"fake_image_bytes"))
    return bot


@pytest.mark.asyncio
async def test_booking_passport_photo():
    state = DummyFSMContext(initial_state=BookingState.waiting_for_name)
    msg = MagicMock()
    msg.photo = [MagicMock(file_id="pass_photo_123")]
    msg.document = None
    msg.text = None
    msg.caption = None
    msg.from_user = MagicMock(full_name="Dilshod Karimov")
    msg.answer = AsyncMock()

    await handle_booking_name(msg, state)
    assert await state.get_state() == BookingState.waiting_for_phone
    data = await state.get_data()
    assert "Dilshod Karimov (Pasport rasmi)" in data["name"]
    assert data["passport_file_id"] == "pass_photo_123"


@pytest.mark.asyncio
async def test_cancel_booking_process():
    from handlers.booking import handle_cancel_booking_process

    state = DummyFSMContext(
        initial_state=BookingState.waiting_for_date,
        initial_data={"room_key": "deluxe"},
    )
    msg = MagicMock()
    msg.text = "❌ Bekor qilish"
    msg.answer = AsyncMock()

    await handle_cancel_booking_process(msg, state)
    assert await state.get_state() is None
    assert await state.get_data() == {}
    assert "bekor qilindi" in msg.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_booking_happy_path(sample_room, sample_booking, sample_payment, sample_hotel, tmp_path):
    mock_api = MagicMock(spec=HotelApiClient)
    mock_api.get_room = AsyncMock(return_value=sample_room)
    mock_api.check_availability = AsyncMock(
        return_value={"available": True, "price_per_night": 600000, "total": 1200000}
    )
    mock_api.create_booking = AsyncMock(
        return_value={"booking": sample_booking, "payment": sample_payment}
    )
    mock_api.get_hotel = AsyncMock(return_value=sample_hotel)
    mock_api.upload_receipt = AsyncMock(
        return_value={"booking": {**sample_booking, "status": "waiting_admin"}}
    )
    mock_api.last_known_hotel_phone = sample_hotel["phone"]

    state = DummyFSMContext()

    # Step 1: Select room
    cb = MagicMock()
    cb.data = "book:deluxe"
    cb.answer = AsyncMock()
    cb.message = MagicMock()
    cb.message.answer = AsyncMock()

    await handle_room_selected(cb, state, mock_api)
    assert await state.get_state() == BookingState.waiting_for_date
    assert (await state.get_data())["room_key"] == "deluxe"

    # Step 2: Date
    msg = MagicMock()
    msg.text = "Bugun"
    msg.answer = AsyncMock()
    await handle_booking_date(msg, state)
    assert await state.get_state() == BookingState.waiting_for_nights
    data = await state.get_data()
    assert "checkin" in data

    # Step 3: Nights
    msg.text = "2"
    await handle_booking_nights(msg, state, mock_api)
    assert await state.get_state() == BookingState.waiting_for_name
    assert (await state.get_data())["nights"] == 2

    # Step 4: Name
    msg.text = "Aziz Rahimov"
    msg.photo = None
    msg.document = None
    msg.caption = None
    await handle_booking_name(msg, state)
    assert await state.get_state() == BookingState.waiting_for_phone
    assert (await state.get_data())["name"] == "Aziz Rahimov"

    # Step 5: Phone via verified Contact
    msg.from_user = MagicMock()
    msg.from_user.id = 555666
    msg.from_user.username = "aziz_uz"
    msg.contact = MagicMock()
    msg.contact.user_id = 555666  # Matches sender -> verified
    msg.contact.phone_number = "+998901234567"
    msg.text = None

    with patch("handlers.booking.save_verified_phone") as mock_save:
        await handle_booking_phone(msg, state, mock_api)
        mock_save.assert_called_once_with(555666, "+998901234567")

    assert await state.get_state() == BookingState.waiting_for_receipt
    assert (await state.get_data())["booking_code"] == sample_booking["code"]

    # Verify payment message sent
    sent_payment_call = msg.answer.call_args[0][0]
    assert "Toʻlovni amalga oshirish" in sent_payment_call
    assert sample_payment["card_owner"] in sent_payment_call

    # Step 6: Send Receipt photo
    mock_bot = MagicMock()
    mock_bot.download = AsyncMock(return_value=io.BytesIO(b"fake_receipt_bytes"))

    receipt_msg = MagicMock()
    receipt_msg.from_user = msg.from_user
    receipt_msg.text = None
    receipt_msg.document = None
    photo_mock = MagicMock()
    photo_mock.file_id = "photo_123"
    photo_mock.file_size = 50000
    receipt_msg.photo = [photo_mock]
    receipt_msg.answer = AsyncMock()

    await handle_receipt_upload(receipt_msg, state, mock_bot, mock_api)
    assert await state.get_state() is None  # State cleared after successful receipt
    assert "Chek qabul qilindi" in receipt_msg.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_booking_unavailable_at_creation(sample_booking):
    mock_api = MagicMock(spec=HotelApiClient)
    mock_api.create_booking = AsyncMock(
        side_effect=ApiClientError(409, "unavailable", "Xona band")
    )
    mock_api.last_known_hotel_phone = "+998712000000"

    state = DummyFSMContext(
        initial_state=BookingState.waiting_for_phone,
        initial_data={
            "room_key": "deluxe",
            "checkin": "2026-11-10",
            "nights": 2,
            "name": "Aziz",
        },
    )

    msg = MagicMock()
    msg.from_user = MagicMock(id=111, username="test")
    msg.contact = None
    msg.text = "901234567"
    msg.answer = AsyncMock()

    await handle_booking_phone(msg, state, mock_api)
    assert await state.get_state() is None  # reset state
    assert "boshqa mehmon tomonidan band qilindi" in msg.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_booking_api_down():
    mock_api = MagicMock(spec=HotelApiClient)
    mock_api.create_booking = AsyncMock(
        side_effect=ApiNetworkError("Down", hotel_phone="+998712000000")
    )
    mock_api.last_known_hotel_phone = "+998712000000"

    state = DummyFSMContext(
        initial_state=BookingState.waiting_for_phone,
        initial_data={
            "room_key": "deluxe",
            "checkin": "2026-11-10",
            "nights": 2,
            "name": "Aziz",
        },
    )

    msg = MagicMock()
    msg.from_user = MagicMock(id=111, username="test")
    msg.contact = None
    msg.text = "901234567"
    msg.answer = AsyncMock()

    await handle_booking_phone(msg, state, mock_api)
    assert await state.get_state() is None
    assert "Tizim vaqtincha ishlamayapti" in msg.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_receipt_restart_recovery(sample_booking):
    """If bot restarted (no FSM state), attach receipt to latest pending booking."""
    mock_api = MagicMock(spec=HotelApiClient)
    mock_api.get_my_bookings = AsyncMock(
        return_value=[
            {**sample_booking, "code": "BR-RECOVERED", "status": "pending"},
        ]
    )
    mock_api.upload_receipt = AsyncMock(
        return_value={"booking": {**sample_booking, "status": "waiting_admin"}}
    )
    mock_bot = MagicMock()
    mock_bot.download = AsyncMock(return_value=io.BytesIO(b"fake_bytes"))

    state = DummyFSMContext()  # Empty state!

    msg = MagicMock()
    msg.from_user = MagicMock(id=999)
    msg.text = None
    msg.document = None
    photo = MagicMock(file_id="p1", file_size=1000)
    msg.photo = [photo]
    msg.answer = AsyncMock()

    await handle_receipt_upload(msg, state, mock_bot, mock_api)
    mock_api.upload_receipt.assert_awaited_once()
    assert mock_api.upload_receipt.call_args[1]["code"] == "BR-RECOVERED"
    assert "BR-RECOVERED" in msg.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_receipt_expired_or_invalid_file(sample_booking):
    mock_api = MagicMock(spec=HotelApiClient)
    mock_bot = MagicMock()
    mock_bot.download = AsyncMock(return_value=io.BytesIO(b"fake_bytes"))

    state = DummyFSMContext(
        initial_state=BookingState.waiting_for_receipt,
        initial_data={"booking_code": "BR-98765"},
    )

    # 1. Invalid file size (> 5MB)
    msg = MagicMock()
    msg.from_user = MagicMock(id=999)
    msg.text = None
    msg.document = None
    photo = MagicMock(file_id="p1", file_size=6 * 1024 * 1024)
    msg.photo = [photo]
    msg.answer = AsyncMock()

    await handle_receipt_upload(msg, state, mock_bot, mock_api)
    assert "maksimal 5 MB" in msg.answer.call_args[0][0]

    # 2. Expired booking on upload
    mock_api.upload_receipt = AsyncMock(
        side_effect=ApiClientError(409, "expired", "Muddati oʻtgan")
    )
    photo.file_size = 50000
    await handle_receipt_upload(msg, state, mock_bot, mock_api)
    assert "ajratilgan vaqt tugagan" in msg.answer.call_args[0][0]
