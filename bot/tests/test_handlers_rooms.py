from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.exceptions import TelegramAPIError
import httpx
import pytest
from api_client import HotelApiClient
from handlers.rooms import handle_room_photos, handle_rooms_list


class DummyFSMContext:
    async def clear(self):
        pass


@pytest.mark.asyncio
async def test_rooms_list_direct_photo_url(sample_room):
    mock_api = MagicMock(spec=HotelApiClient)
    mock_api.get_rooms = AsyncMock(return_value=[sample_room])

    msg = MagicMock()
    msg.answer_photo = AsyncMock()
    msg.answer = AsyncMock()

    await handle_rooms_list(msg, DummyFSMContext(), mock_api)
    mock_api.get_rooms.assert_awaited_once()
    msg.answer_photo.assert_awaited_once()
    assert msg.answer_photo.call_args[1]["photo"] == sample_room["cover_960"]


@pytest.mark.asyncio
async def test_rooms_list_failing_photo_url_fallback_to_bytes(sample_room):
    mock_api = MagicMock(spec=HotelApiClient)
    mock_api.get_rooms = AsyncMock(return_value=[sample_room])

    msg = MagicMock()
    # First attempt (URL) raises TelegramAPIError
    msg.answer_photo = AsyncMock(side_effect=[TelegramAPIError(method="sendPhoto", message="Bad URL"), None])
    msg.answer = AsyncMock()

    with patch("handlers.rooms._download_image", new=AsyncMock(return_value=b"fake_image_bytes")):
        await handle_rooms_list(msg, DummyFSMContext(), mock_api)

    # answer_photo called twice: 1st with URL, 2nd with BufferedInputFile
    assert msg.answer_photo.call_count == 2
    assert msg.answer_photo.call_args_list[1][1]["photo"].filename == "room_deluxe.jpg"


@pytest.mark.asyncio
async def test_rooms_list_failing_photo_and_download_fallback_to_text(sample_room):
    mock_api = MagicMock(spec=HotelApiClient)
    mock_api.get_rooms = AsyncMock(return_value=[sample_room])

    msg = MagicMock()
    # URL fails
    msg.answer_photo = AsyncMock(side_effect=TelegramAPIError(method="sendPhoto", message="Failed"))
    msg.answer = AsyncMock()

    with patch("handlers.rooms._download_image", new=AsyncMock(return_value=None)):
        await handle_rooms_list(msg, DummyFSMContext(), mock_api)

    # Sent caption as text
    msg.answer.assert_awaited_once()
    assert "Deluxe Double Room" in msg.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_rooms_list_without_photo(sample_room_no_photo):
    mock_api = MagicMock(spec=HotelApiClient)
    mock_api.get_rooms = AsyncMock(return_value=[sample_room_no_photo])

    msg = MagicMock()
    msg.answer_photo = AsyncMock()
    msg.answer = AsyncMock()

    await handle_rooms_list(msg, DummyFSMContext(), mock_api)
    msg.answer_photo.assert_not_called()
    msg.answer.assert_awaited_once()
    assert "Standard Single Room" in msg.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_rooms_more_photos_media_group(sample_room):
    mock_api = MagicMock(spec=HotelApiClient)
    mock_api.get_room = AsyncMock(return_value=sample_room)

    cb = MagicMock()
    cb.data = "photos:deluxe"
    cb.answer = AsyncMock()
    cb.message = MagicMock()
    cb.message.answer_media_group = AsyncMock()
    cb.message.answer = AsyncMock()

    await handle_room_photos(cb, mock_api)
    cb.answer.assert_awaited_once()
    cb.message.answer_media_group.assert_awaited_once()
