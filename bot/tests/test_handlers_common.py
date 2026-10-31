from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock
import pytest
from api_client import ApiClientError, ApiNetworkError, HotelApiClient
from handlers.booking import BookingState
from handlers.common import (
    LookupState,
    handle_hotel_info,
    handle_lookup_code,
    handle_lookup_phone,
    handle_lookup_start,
    handle_start,
)
from utils import get_current_date


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

    async def update_data(self, **kwargs):
        self._data.update(kwargs)

    async def clear(self):
        self._state = None
        self._data = {}


@pytest.mark.asyncio
async def test_start_command_default():
    mock_api = MagicMock(spec=HotelApiClient)
    state = DummyFSMContext()

    msg = MagicMock()
    msg.answer = AsyncMock()

    cmd = MagicMock()
    cmd.args = None

    await handle_start(msg, cmd, state, mock_api)
    assert await state.get_state() is None
    msg.answer.assert_awaited_once()
    assert "xush kelibsiz" in msg.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_start_room_deep_link(sample_room):
    mock_api = MagicMock(spec=HotelApiClient)
    mock_api.get_room = AsyncMock(return_value=sample_room)
    state = DummyFSMContext()

    msg = MagicMock()
    msg.answer = AsyncMock()

    cmd = MagicMock()
    cmd.args = "room_deluxe"

    await handle_start(msg, cmd, state, mock_api)
    assert await state.get_state() == BookingState.waiting_for_date
    assert (await state.get_data())["room_key"] == "deluxe"
    assert "Deluxe Double Room" in msg.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_start_booking_deep_link_available(sample_room):
    mock_api = MagicMock(spec=HotelApiClient)
    mock_api.check_availability = AsyncMock(
        return_value={"available": True, "price_per_night": 600000, "total": 1200000}
    )
    mock_api.get_room = AsyncMock(return_value=sample_room)
    state = DummyFSMContext()

    future = get_current_date() + timedelta(days=5)
    future_str = future.strftime("%Y%m%d")

    msg = MagicMock()
    msg.answer = AsyncMock()

    cmd = MagicMock()
    cmd.args = f"b_deluxe_{future_str}_2"

    await handle_start(msg, cmd, state, mock_api)
    assert await state.get_state() == BookingState.waiting_for_name
    assert (await state.get_data())["nights"] == 2
    assert "Xona boʻsh" in msg.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_start_booking_deep_link_unavailable():
    mock_api = MagicMock(spec=HotelApiClient)
    mock_api.check_availability = AsyncMock(
        return_value={"available": False, "price_per_night": 600000, "total": 1200000}
    )
    mock_api.get_hotel = AsyncMock(return_value={"phone": "+998712000000"})
    state = DummyFSMContext()

    future = get_current_date() + timedelta(days=5)
    future_str = future.strftime("%Y%m%d")

    msg = MagicMock()
    msg.answer = AsyncMock()

    cmd = MagicMock()
    cmd.args = f"b_deluxe_{future_str}_2"

    await handle_start(msg, cmd, state, mock_api)
    assert "bu xona band" in msg.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_hotel_info_handler(sample_hotel):
    mock_api = MagicMock(spec=HotelApiClient)
    mock_api.get_hotel = AsyncMock(return_value=sample_hotel)

    msg = MagicMock()
    msg.answer = AsyncMock()

    await handle_hotel_info(msg, DummyFSMContext(), mock_api)
    res = msg.answer.call_args[0][0]
    assert sample_hotel["name"] in res
    assert sample_hotel["phone"] in res


@pytest.mark.asyncio
async def test_lookup_flow_success(sample_booking):
    mock_api = MagicMock(spec=HotelApiClient)
    mock_api.lookup_booking = AsyncMock(return_value=sample_booking)

    state = DummyFSMContext()

    # Step 1: Click menu
    msg = MagicMock()
    msg.answer = AsyncMock()
    await handle_lookup_start(msg, state)
    assert await state.get_state() == LookupState.waiting_for_code

    # Step 2: Enter code
    msg.text = "BR-98765"
    await handle_lookup_code(msg, state)
    assert await state.get_state() == LookupState.waiting_for_phone
    assert (await state.get_data())["lookup_code"] == "BR-98765"

    # Step 3: Enter phone
    msg.text = "+998901234567"
    await handle_lookup_phone(msg, state, mock_api)
    assert await state.get_state() is None
    mock_api.lookup_booking.assert_awaited_once_with("BR-98765", "+998901234567")
    res = msg.answer.call_args[0][0]
    assert "BR-98765" in res
    assert "Deluxe Double Room" in res


@pytest.mark.asyncio
async def test_lookup_flow_not_found():
    mock_api = MagicMock(spec=HotelApiClient)
    mock_api.lookup_booking = AsyncMock(
        side_effect=ApiClientError(404, "not_found", "Topilmadi")
    )

    state = DummyFSMContext(
        initial_state=LookupState.waiting_for_phone,
        initial_data={"lookup_code": "BR-98765"},
    )

    msg = MagicMock()
    msg.text = "901234567"
    msg.answer = AsyncMock()

    await handle_lookup_phone(msg, state, mock_api)
    assert "Bunday bron topilmadi" in msg.answer.call_args[0][0]
