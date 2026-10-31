from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from api_client import HotelApiClient
from handlers.booking import BookingState
from handlers.my_bookings import (
    handle_my_bookings_menu,
    handle_payment_details_callback,
    handle_share_contact_verified,
)


class DummyFSMContext:
    def __init__(self):
        self._state = None
        self._data = {}

    async def clear(self):
        self._state = None
        self._data = {}

    async def set_state(self, s):
        self._state = s

    async def update_data(self, **kwargs):
        self._data.update(kwargs)

    async def get_state(self):
        return self._state

    async def get_data(self):
        return dict(self._data)


@pytest.mark.asyncio
async def test_my_bookings_without_verified_phone(sample_booking):
    mock_api = MagicMock(spec=HotelApiClient)
    mock_api.get_my_bookings = AsyncMock(return_value=[sample_booking])

    msg = MagicMock()
    msg.from_user = MagicMock(id=12345)
    msg.answer = AsyncMock()

    with patch("handlers.my_bookings.get_verified_phone", return_value=None):
        await handle_my_bookings_menu(msg, DummyFSMContext(), mock_api)

    mock_api.get_my_bookings.assert_awaited_once_with(12345, None)
    # Check that hint for sharing contact was sent
    all_answers = [call[0][0] for call in msg.answer.call_args_list]
    assert any("BR-98765" in ans for ans in all_answers)
    assert any("Veb-sayt" in ans or "telefon raqamingizni ulashing" in ans for ans in all_answers)


@pytest.mark.asyncio
async def test_my_bookings_with_verified_phone(sample_booking):
    mock_api = MagicMock(spec=HotelApiClient)
    mock_api.get_my_bookings = AsyncMock(return_value=[sample_booking])

    msg = MagicMock()
    msg.from_user = MagicMock(id=12345)
    msg.answer = AsyncMock()

    with patch("handlers.my_bookings.get_verified_phone", return_value="+998901234567"):
        await handle_my_bookings_menu(msg, DummyFSMContext(), mock_api)

    mock_api.get_my_bookings.assert_awaited_once_with(12345, "+998901234567")
    all_answers = [call[0][0] for call in msg.answer.call_args_list]
    assert any("BR-98765" in ans for ans in all_answers)
    # No hint to share contact since already verified
    assert not any("telefon raqamingizni ulashing" in ans for ans in all_answers)


@pytest.mark.asyncio
async def test_share_contact_verification():
    mock_api = MagicMock(spec=HotelApiClient)
    mock_api.get_my_bookings = AsyncMock(return_value=[])

    msg = MagicMock()
    msg.from_user = MagicMock(id=12345)
    msg.answer = AsyncMock()

    # Case A: user_id mismatch (someone else's contact forwarded)
    msg.contact = MagicMock(user_id=99999, phone_number="+998901112233")
    with patch("handlers.my_bookings.save_verified_phone") as mock_save:
        await handle_share_contact_verified(msg, DummyFSMContext(), mock_api)
        mock_save.assert_not_called()
        assert "Faqat oʻzingizning Telegram" in msg.answer.call_args[0][0]

    # Case B: user_id match
    msg.contact = MagicMock(user_id=12345, phone_number="901112233")
    with patch("handlers.my_bookings.save_verified_phone") as mock_save:
        await handle_share_contact_verified(msg, DummyFSMContext(), mock_api)
        mock_save.assert_called_once_with(12345, "+998901112233")


@pytest.mark.asyncio
async def test_payment_details_callback(sample_booking, sample_payment, sample_hotel):
    mock_api = MagicMock(spec=HotelApiClient)
    mock_api.get_payment = AsyncMock(
        return_value={"booking": sample_booking, "payment": sample_payment}
    )
    mock_api.get_hotel = AsyncMock(return_value=sample_hotel)

    state = DummyFSMContext()
    cb = MagicMock()
    cb.data = "pay:BR-98765"
    cb.from_user = MagicMock(id=12345)
    cb.answer = AsyncMock()
    cb.message = MagicMock()
    cb.message.answer = AsyncMock()

    await handle_payment_details_callback(cb, state, mock_api)
    cb.answer.assert_awaited_once()
    assert await state.get_state() == BookingState.waiting_for_receipt
    assert (await state.get_data())["booking_code"] == "BR-98765"
    assert "Toʻlovni amalga oshirish" in cb.message.answer.call_args[0][0]
