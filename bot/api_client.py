import logging
import time
from typing import Any, Dict, List, Optional, Tuple
import httpx
from texts import API_ERROR_MESSAGES, get_api_unavailable_message

logger = logging.getLogger(__name__)


class ApiClientError(Exception):
    """Raised when the API returns an HTTP error status (4xx, 5xx)."""

    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(f"API Error {status_code} [{code}]: {message}")


class ApiNetworkError(Exception):
    """Raised when the API is unreachable, down, or times out."""

    def __init__(self, message: str, hotel_phone: Optional[str] = None):
        self.hotel_phone = hotel_phone
        self.user_message = get_api_unavailable_message(hotel_phone)
        super().__init__(message)


class HotelApiClient:
    """
    Asynchronous client for Hotel REST API.
    Handles caching, timeouts, retries, and error mapping.
    """

    def __init__(self, base_url: str, api_key: str, timeout: float = 15.0):
        # Base path /api
        self.base_url = base_url.rstrip("/")
        if not self.base_url.endswith("/api"):
            self.api_url = f"{self.base_url}/api"
        else:
            self.api_url = self.base_url

        self.api_key = api_key
        self.timeout = timeout

        self._client: Optional[httpx.AsyncClient] = None

        # Caching
        self._cached_hotel: Optional[Dict[str, Any]] = None
        self._hotel_cache_time: float = 0.0
        self.hotel_cache_ttl: float = 300.0  # 5 minutes

        self._cached_rooms: Optional[List[Dict[str, Any]]] = None
        self._rooms_cache_time: float = 0.0
        self.rooms_cache_ttl: float = 60.0  # 60 seconds

        self.last_known_hotel_phone: Optional[str] = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            headers = {
                "X-API-KEY": self.api_key,
                "Accept": "application/json",
            }
            self._client = httpx.AsyncClient(
                base_url=self.api_url,
                headers=headers,
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def _parse_error(self, response: httpx.Response) -> ApiClientError:
        code = "unknown_error"
        try:
            data = response.json()
            if isinstance(data, dict) and "detail" in data:
                code = str(data["detail"])
        except Exception:
            pass

        uz_message = API_ERROR_MESSAGES.get(code, f"Xatolik yuz berdi ({code}).")
        return ApiClientError(response.status_code, code, uz_message)

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
    ) -> Any:
        client = self._get_client()
        url = path if path.startswith("/") else f"/{path}"

        is_get = method.upper() == "GET"
        max_attempts = 2 if is_get else 1

        last_exc: Optional[Exception] = None

        for attempt in range(1, max_attempts + 1):
            try:
                # Do not log sensitive data like api_key or tokens
                logger.debug("API %s %s (attempt %d)", method, url, attempt)
                response = await client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                    data=data,
                    files=files,
                )

                if response.is_success:
                    if response.status_code == 204:
                        return None
                    return response.json()

                # 4xx or 5xx returned by server - do not retry
                raise self._parse_error(response)

            except (httpx.RequestError, httpx.TimeoutException) as exc:
                last_exc = exc
                logger.warning(
                    "Network error on API %s %s (attempt %d/%d): %s",
                    method,
                    url,
                    attempt,
                    max_attempts,
                    exc,
                )
                if attempt < max_attempts:
                    continue
                # All allowed attempts exhausted
                raise ApiNetworkError(str(last_exc), self.last_known_hotel_phone) from last_exc

    # --- Endpoints ---

    async def get_hotel(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        GET /api/hotel -> {"hotel": Hotel}
        Cached for 5 minutes. Retains last good value on refresh failure.
        """
        now = time.time()
        if not force_refresh and self._cached_hotel and (now - self._hotel_cache_time < self.hotel_cache_ttl):
            return self._cached_hotel

        try:
            data = await self._request("GET", "/hotel")
            hotel = data.get("hotel", {})
            self._cached_hotel = hotel
            self._hotel_cache_time = now
            if hotel.get("phone"):
                self.last_known_hotel_phone = hotel["phone"]
            return hotel
        except Exception as exc:
            if self._cached_hotel:
                logger.warning("Failed to refresh hotel info, returning cached: %s", exc)
                return self._cached_hotel
            raise

    async def get_rooms(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        GET /api/rooms -> {"rooms": [Room]}
        Cached for 60 seconds. Retains last good value on refresh failure.
        """
        now = time.time()
        if not force_refresh and self._cached_rooms and (now - self._rooms_cache_time < self.rooms_cache_ttl):
            return self._cached_rooms

        try:
            data = await self._request("GET", "/rooms")
            rooms = data.get("rooms", [])
            self._cached_rooms = rooms
            self._rooms_cache_time = now
            return rooms
        except Exception as exc:
            if self._cached_rooms:
                logger.warning("Failed to refresh rooms list, returning cached: %s", exc)
                return self._cached_rooms
            raise

    async def get_room(self, key: str) -> Dict[str, Any]:
        """GET /api/rooms/{key} -> {"room": Room}"""
        data = await self._request("GET", f"/rooms/{key}")
        return data.get("room", {})

    async def get_calendar(self, key: str, from_date: str, days: int = 90) -> List[Dict[str, Any]]:
        """GET /api/rooms/{key}/calendar?from=YYYY-MM-DD&days=90 -> {"days": [...]}"""
        params = {"from": from_date, "days": days}
        data = await self._request("GET", f"/rooms/{key}/calendar", params=params)
        return data.get("days", [])

    async def check_availability(self, room_key: str, checkin: str, nights: int) -> Dict[str, Any]:
        """
        GET /api/availability?room=&checkin=&nights=
        -> {"available": bool, "price_per_night": int, "total": int}
        """
        params = {"room": room_key, "checkin": checkin, "nights": nights}
        return await self._request("GET", "/availability", params=params)

    async def create_booking(
        self,
        room: str,
        checkin: str,
        nights: int,
        name: str,
        phone: str,
        telegram_id: int,
        username: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        POST /api/bookings
        body {room, checkin, nights, name, phone, source: "bot", telegram_id, username}
        -> 201 {"booking": Booking, "payment": {"card_number", "card_owner"}}
        """
        payload = {
            "room": room,
            "checkin": checkin,
            "nights": nights,
            "name": name,
            "phone": phone,
            "source": "bot",
            "telegram_id": telegram_id,
            "username": username,
        }
        return await self._request("POST", "/bookings", json_data=payload)

    async def get_payment(
        self, code: str, telegram_id: Optional[int] = None, phone: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        GET /api/bookings/{code}/payment?telegram_id= (or ?phone=)
        -> {"booking": Booking, "payment": {...}}
        """
        params: Dict[str, Any] = {}
        if telegram_id is not None:
            params["telegram_id"] = telegram_id
        elif phone is not None:
            params["phone"] = phone
        return await self._request("GET", f"/bookings/{code}/payment", params=params)

    async def upload_receipt(
        self,
        code: str,
        file_bytes: bytes,
        filename: str,
        content_type: str,
        telegram_id: Optional[int] = None,
        phone: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        POST /api/bookings/{code}/receipt
        multipart: file (+ field phone, or field telegram_id)
        -> {"booking": Booking}
        """
        files = {"file": (filename, file_bytes, content_type)}
        form_data: Dict[str, Any] = {}
        if telegram_id is not None:
            form_data["telegram_id"] = str(telegram_id)
        elif phone is not None:
            form_data["phone"] = phone

        return await self._request(
            "POST", f"/bookings/{code}/receipt", data=form_data, files=files
        )

    async def cancel_booking(
        self, code: str, telegram_id: Optional[int] = None, phone: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        POST /api/bookings/{code}/cancel
        body {phone} or {telegram_id}
        -> {"booking": Booking}
        """
        payload: Dict[str, Any] = {}
        if telegram_id is not None:
            payload["telegram_id"] = telegram_id
        elif phone is not None:
            payload["phone"] = phone

        return await self._request("POST", f"/bookings/{code}/cancel", json_data=payload)

    async def lookup_booking(self, code: str, phone: str) -> Dict[str, Any]:
        """
        GET /api/bookings/lookup?code=&phone=
        -> {"booking": Booking}
        """
        params = {"code": code, "phone": phone}
        data = await self._request("GET", "/bookings/lookup", params=params)
        return data.get("booking", {})

    async def get_my_bookings(
        self, telegram_id: int, verified_phone: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        GET /api/bookings/by-telegram/{telegram_id}?phone=
        -> {"bookings": [Booking]} (last 5, newest first)
        """
        params: Dict[str, Any] = {}
        if verified_phone:
            params["phone"] = verified_phone
        data = await self._request("GET", f"/bookings/by-telegram/{telegram_id}", params=params)
        return data.get("bookings", [])

    async def get_admin_upcoming(self, admin_telegram_id: int) -> List[Dict[str, Any]]:
        """
        GET /api/admin/bookings/upcoming?admin_telegram_id=
        -> {"bookings": [Booking]}
        """
        params = {"admin_telegram_id": admin_telegram_id}
        data = await self._request("GET", "/admin/bookings/upcoming", params=params)
        return data.get("bookings", [])

    async def admin_decision(
        self, booking_id: int, action: str, admin_telegram_id: int
    ) -> Dict[str, Any]:
        """
        POST /api/admin/bookings/{id}/decision
        body {"action": "approve"|"reject", "admin_telegram_id": int}
        -> {"booking": Booking}
        """
        payload = {"action": action, "admin_telegram_id": admin_telegram_id}
        return await self._request(
            "POST", f"/admin/bookings/{booking_id}/decision", json_data=payload
        )
