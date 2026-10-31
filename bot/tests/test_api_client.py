import time
import httpx
import pytest
import respx
from api_client import ApiClientError, ApiNetworkError, HotelApiClient
from texts import API_ERROR_MESSAGES, get_api_unavailable_message


@pytest.mark.asyncio
async def test_get_hotel_success_and_cache(mock_api_client: HotelApiClient, sample_hotel):
    async with respx.mock(base_url="https://hotel-api.example.com/api") as respx_mock:
        route = respx_mock.get("/hotel").respond(200, json={"hotel": sample_hotel})

        # First call fetches from API
        h1 = await mock_api_client.get_hotel()
        assert h1["name"] == sample_hotel["name"]
        assert route.call_count == 1
        assert mock_api_client.last_known_hotel_phone == sample_hotel["phone"]

        # Second call immediately after should hit cache
        h2 = await mock_api_client.get_hotel()
        assert h2["name"] == sample_hotel["name"]
        assert route.call_count == 1

        # Force refresh fetches again
        h3 = await mock_api_client.get_hotel(force_refresh=True)
        assert route.call_count == 2


@pytest.mark.asyncio
async def test_hotel_cache_fallback_on_refresh_failure(mock_api_client: HotelApiClient, sample_hotel):
    async with respx.mock(base_url="https://hotel-api.example.com/api") as respx_mock:
        route = respx_mock.get("/hotel")
        route.side_effect = [
            httpx.Response(200, json={"hotel": sample_hotel}),
            httpx.ConnectError("Connection refused"),
            httpx.ConnectError("Connection refused"),
        ]

        # First call fills cache
        h1 = await mock_api_client.get_hotel()
        assert h1["name"] == sample_hotel["name"]

        # Expire cache manually
        mock_api_client._hotel_cache_time = 0.0

        # Attempt to get hotel again - network fails, but returns cached data!
        h2 = await mock_api_client.get_hotel()
        assert h2["name"] == sample_hotel["name"]


@pytest.mark.asyncio
async def test_get_rooms_success_and_cache(mock_api_client: HotelApiClient, sample_room):
    async with respx.mock(base_url="https://hotel-api.example.com/api") as respx_mock:
        route = respx_mock.get("/rooms").respond(200, json={"rooms": [sample_room]})

        rooms1 = await mock_api_client.get_rooms()
        assert len(rooms1) == 1
        assert route.call_count == 1

        rooms2 = await mock_api_client.get_rooms()
        assert len(rooms2) == 1
        assert route.call_count == 1


@pytest.mark.asyncio
async def test_rooms_cache_fallback_on_failure(mock_api_client: HotelApiClient, sample_room):
    async with respx.mock(base_url="https://hotel-api.example.com/api") as respx_mock:
        route = respx_mock.get("/rooms")
        route.side_effect = [
            httpx.Response(200, json={"rooms": [sample_room]}),
            httpx.ConnectError("Connection refused"),
            httpx.ConnectError("Connection refused"),
        ]

        rooms1 = await mock_api_client.get_rooms()
        assert len(rooms1) == 1

        # Expire cache
        mock_api_client._rooms_cache_time = 0.0
        rooms2 = await mock_api_client.get_rooms()
        assert len(rooms2) == 1


@pytest.mark.asyncio
async def test_check_availability(mock_api_client: HotelApiClient):
    async with respx.mock(base_url="https://hotel-api.example.com/api") as respx_mock:
        respx_mock.get("/availability").respond(
            200, json={"available": True, "price_per_night": 500000, "total": 1000000}
        )
        res = await mock_api_client.check_availability("deluxe", "2026-11-10", 2)
        assert res["available"] is True
        assert res["total"] == 1000000


@pytest.mark.asyncio
async def test_create_booking_success(mock_api_client: HotelApiClient, sample_booking, sample_payment):
    async with respx.mock(base_url="https://hotel-api.example.com/api") as respx_mock:
        route = respx_mock.post("/bookings").respond(
            201, json={"booking": sample_booking, "payment": sample_payment}
        )
        res = await mock_api_client.create_booking(
            room="deluxe",
            checkin="2026-11-10",
            nights=2,
            name="Aziz Rahimov",
            phone="+998901234567",
            telegram_id=123456,
            username="aziz",
        )
        assert res["booking"]["code"] == sample_booking["code"]
        assert res["payment"]["card_number"] == sample_payment["card_number"]
        assert route.call_count == 1


@pytest.mark.asyncio
async def test_post_never_retries_on_error(mock_api_client: HotelApiClient):
    """NEVER retry POST requests (it could duplicate a booking)."""
    async with respx.mock(base_url="https://hotel-api.example.com/api") as respx_mock:
        route = respx_mock.post("/bookings")
        route.side_effect = httpx.ConnectTimeout("Timeout connecting")

        with pytest.raises(ApiNetworkError):
            await mock_api_client.create_booking(
                room="deluxe",
                checkin="2026-11-10",
                nights=2,
                name="Aziz",
                phone="+998901234567",
                telegram_id=12345,
            )

        assert route.call_count == 1, "POST request was retried!"


@pytest.mark.asyncio
async def test_get_retries_once_on_network_error(mock_api_client: HotelApiClient, sample_hotel):
    """GET requests may retry once on network errors."""
    async with respx.mock(base_url="https://hotel-api.example.com/api") as respx_mock:
        route = respx_mock.get("/rooms/deluxe")
        # First attempt fails with ConnectError, second attempt succeeds
        route.side_effect = [
            httpx.ConnectError("Network blip"),
            httpx.Response(200, json={"room": {"key": "deluxe", "name": "Deluxe Room"}}),
        ]

        room = await mock_api_client.get_room("deluxe")
        assert room["name"] == "Deluxe Room"
        assert route.call_count == 2


@pytest.mark.asyncio
async def test_api_network_error_message_with_hotel_phone(mock_api_client: HotelApiClient):
    mock_api_client.last_known_hotel_phone = "+998712000000"
    async with respx.mock(base_url="https://hotel-api.example.com/api") as respx_mock:
        route = respx_mock.get("/rooms/deluxe")
        route.side_effect = [
            httpx.ConnectTimeout("Timed out"),
            httpx.ConnectTimeout("Timed out again"),
        ]

        with pytest.raises(ApiNetworkError) as exc_info:
            await mock_api_client.get_room("deluxe")

        assert "+998712000000" in exc_info.value.user_message
        assert "Tizim vaqtincha ishlamayapti" in exc_info.value.user_message


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status_code,code",
    [
        (422, "validation_error"),
        (409, "unavailable"),
        (404, "not_found"),
        (403, "forbidden"),
        (409, "wrong_status"),
        (409, "expired"),
        (409, "already_decided"),
        (429, "rate_limited"),
        (422, "invalid_file"),
    ],
)
async def test_every_error_code_mapping(mock_api_client: HotelApiClient, status_code: int, code: str):
    async with respx.mock(base_url="https://hotel-api.example.com/api") as respx_mock:
        respx_mock.get("/rooms/deluxe").respond(status_code, json={"detail": code})

        with pytest.raises(ApiClientError) as exc_info:
            await mock_api_client.get_room("deluxe")

        err = exc_info.value
        assert err.status_code == status_code
        assert err.code == code
        assert err.message == API_ERROR_MESSAGES[code]


@pytest.mark.asyncio
async def test_upload_receipt(mock_api_client: HotelApiClient, sample_booking):
    async with respx.mock(base_url="https://hotel-api.example.com/api") as respx_mock:
        respx_mock.post("/bookings/BR-98765/receipt").respond(
            200, json={"booking": {**sample_booking, "status": "waiting_admin"}}
        )

        res = await mock_api_client.upload_receipt(
            code="BR-98765",
            file_bytes=b"sample_image_data",
            filename="receipt.jpg",
            content_type="image/jpeg",
            telegram_id=12345,
        )
        assert res["booking"]["status"] == "waiting_admin"


@pytest.mark.asyncio
async def test_cancel_booking(mock_api_client: HotelApiClient, sample_booking):
    async with respx.mock(base_url="https://hotel-api.example.com/api") as respx_mock:
        respx_mock.post("/bookings/BR-98765/cancel").respond(
            200, json={"booking": {**sample_booking, "status": "cancelled"}}
        )

        res = await mock_api_client.cancel_booking("BR-98765", telegram_id=12345)
        assert res["booking"]["status"] == "cancelled"


@pytest.mark.asyncio
async def test_admin_endpoints(mock_api_client: HotelApiClient, sample_booking):
    async with respx.mock(base_url="https://hotel-api.example.com/api") as respx_mock:
        # Upcoming
        respx_mock.get("/admin/bookings/upcoming").respond(
            200, json={"bookings": [sample_booking]}
        )
        upcoming = await mock_api_client.get_admin_upcoming(admin_telegram_id=999)
        assert len(upcoming) == 1

        # Decision
        respx_mock.post("/admin/bookings/101/decision").respond(
            200, json={"booking": {**sample_booking, "status": "confirmed"}}
        )
        decision = await mock_api_client.admin_decision(101, "approve", admin_telegram_id=999)
        assert decision["booking"]["status"] == "confirmed"
