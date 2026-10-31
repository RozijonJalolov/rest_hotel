from unittest.mock import AsyncMock, MagicMock
import pytest
from api_client import ApiClientError, HotelApiClient
from handlers.admin import handle_admin_decision, handle_admin_upcoming


@pytest.mark.asyncio
async def test_admin_approve_decision(sample_booking):
    mock_api = MagicMock(spec=HotelApiClient)
    mock_api.admin_decision = AsyncMock(
        return_value={"booking": {**sample_booking, "status": "confirmed"}}
    )
    admin_ids = {1001, 1002}

    cb = MagicMock()
    cb.data = "ok:101"
    cb.from_user = MagicMock(id=1001, full_name="Admin Sanjar", username="sanjar")
    cb.answer = AsyncMock()
    cb.message = MagicMock()
    cb.message.caption = "Yangi toʻlov cheki: BR-98765"
    cb.message.text = None
    cb.message.edit_caption = AsyncMock()

    await handle_admin_decision(cb, mock_api, admin_ids)

    mock_api.admin_decision.assert_awaited_once_with(
        booking_id=101, action="approve", admin_telegram_id=1001
    )
    cb.message.edit_caption.assert_awaited_once()
    new_caption = cb.message.edit_caption.call_args[1]["caption"]
    assert "Yangi toʻlov cheki: BR-98765" in new_caption
    assert "✅ TASDIQLANDI (Admin Sanjar)" in new_caption
    assert cb.message.edit_caption.call_args[1]["reply_markup"] is None


@pytest.mark.asyncio
async def test_admin_reject_decision(sample_booking):
    mock_api = MagicMock(spec=HotelApiClient)
    mock_api.admin_decision = AsyncMock(
        return_value={"booking": {**sample_booking, "status": "rejected"}}
    )
    admin_ids = {1001}

    cb = MagicMock()
    cb.data = "no:101"
    cb.from_user = MagicMock(id=1001, full_name="Admin Sanjar", username="sanjar")
    cb.answer = AsyncMock()
    cb.message = MagicMock()
    cb.message.caption = "Toʻlov cheki: BR-98765"
    cb.message.edit_caption = AsyncMock()

    await handle_admin_decision(cb, mock_api, admin_ids)

    mock_api.admin_decision.assert_awaited_once_with(
        booking_id=101, action="reject", admin_telegram_id=1001
    )
    new_caption = cb.message.edit_caption.call_args[1]["caption"]
    assert "❌ RAD ETILDI (Admin Sanjar)" in new_caption


@pytest.mark.asyncio
async def test_non_admin_blocked():
    mock_api = MagicMock(spec=HotelApiClient)
    admin_ids = {1001}

    # Callback non-admin
    cb = MagicMock()
    cb.data = "ok:101"
    cb.from_user = MagicMock(id=777)  # Not in admin_ids
    cb.answer = AsyncMock()

    await handle_admin_decision(cb, mock_api, admin_ids)
    cb.answer.assert_awaited_once()
    assert "Ruxsat yoʻq" in cb.answer.call_args[0][0]
    assert cb.answer.call_args[1]["show_alert"] is True
    mock_api.admin_decision.assert_not_called()

    # /bronlar non-admin
    msg = MagicMock()
    msg.from_user = MagicMock(id=777)
    msg.answer = AsyncMock()

    await handle_admin_upcoming(msg, mock_api, admin_ids)
    assert "Ruxsat yoʻq" in msg.answer.call_args[0][0]
    mock_api.get_admin_upcoming.assert_not_called()


@pytest.mark.asyncio
async def test_admin_already_decided():
    mock_api = MagicMock(spec=HotelApiClient)
    mock_api.admin_decision = AsyncMock(
        side_effect=ApiClientError(409, "already_decided", "Qaror qabul qilingan")
    )
    admin_ids = {1001}

    cb = MagicMock()
    cb.data = "ok:101"
    cb.from_user = MagicMock(id=1001)
    cb.answer = AsyncMock()
    cb.message = MagicMock()
    cb.message.edit_reply_markup = AsyncMock()

    await handle_admin_decision(cb, mock_api, admin_ids)
    assert "allaqachon qaror qabul qilingan" in cb.answer.call_args[0][0]
    cb.message.edit_reply_markup.assert_awaited_once_with(reply_markup=None)


@pytest.mark.asyncio
async def test_admin_unavailable_on_approve():
    mock_api = MagicMock(spec=HotelApiClient)
    mock_api.admin_decision = AsyncMock(
        side_effect=ApiClientError(409, "unavailable", "Xona band")
    )
    admin_ids = {1001}

    cb = MagicMock()
    cb.data = "ok:101"
    cb.from_user = MagicMock(id=1001)
    cb.answer = AsyncMock()

    await handle_admin_decision(cb, mock_api, admin_ids)
    assert "boshqa mehmon tomonidan band qilingan" in cb.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_admin_upcoming_list(sample_booking):
    mock_api = MagicMock(spec=HotelApiClient)
    mock_api.get_admin_upcoming = AsyncMock(return_value=[sample_booking])
    admin_ids = {1001}

    msg = MagicMock()
    msg.from_user = MagicMock(id=1001)
    msg.answer = AsyncMock()

    await handle_admin_upcoming(msg, mock_api, admin_ids)
    mock_api.get_admin_upcoming.assert_awaited_once_with(admin_telegram_id=1001)
    res_text = msg.answer.call_args[0][0]
    assert "BR-98765" in res_text
    assert "Aziz Rahimov" in res_text
