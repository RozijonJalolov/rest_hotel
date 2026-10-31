import hmac
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

app = FastAPI(title="Sam Rest Hotel API & Website", docs_url="/docs")

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

UZB_TZ = timezone(timedelta(hours=5))
API_KEY = os.getenv("API_KEY", "hotel_secret_api_key_123")

# Hotel information with exact location on Shohi Zinda street
HOTEL_DATA = {
    "name": "SAM REST HOTEL (Sam Rest Mehmonxonasi)",
    "phone": "+998880110055",
    "address": "Samarqand shahri, Shohi Zinda koʻchasi (BURHAN oshi yonida)",
    "map_link": "https://www.google.com/maps/search/?api=1&query=SAM+REST+HOTEL+Samarkand",
    "checkin_time": "14:00",
    "checkout_time": "12:00",
    "hours": "24/7",
    "image_url": "http://127.0.0.1:8000/static/images/exterior_night.jpg",
}

# 2 ta 2 kishilik, 1 ta 3 kishilik xona (hammasi real fotosuratlar va kelishilgan narxlar bilan)
ROOMS_DATA = [
    {
        "key": "double_room_1",
        "name": "2 kishilik shinam xona (№1)",
        "description": "2 kishilik zamonaviy va shinam xona. Qulay alohida yotoqlar, Smart TV, konditsioner, alohida toza dush xonasi bilan jihozlangan. Narxi 400 000 soʻm (kelishilgan holda arzonlashtirib ham beramiz).",
        "amenities": ["Wi-Fi", "Smart TV", "Konditsioner", "Alohida dush va hojatxona", "Kelishiladi", "24/7 Xizmat"],
        "price_per_night": 400000,
        "count": 1,
        "cover_960": "http://127.0.0.1:8000/static/images/room_beds.png",
        "images": [
            {
                "id": 1,
                "alt": "2 kishilik yotoqlar (№1 xona)",
                "is_cover": True,
                "urls": {
                    "480": "http://127.0.0.1:8000/static/images/room_beds.png",
                    "960": "http://127.0.0.1:8000/static/images/room_beds.png",
                    "1600": "http://127.0.0.1:8000/static/images/room_beds.png",
                },
            },
            {
                "id": 2,
                "alt": "Smart TV va xona koʻrinishi",
                "is_cover": False,
                "urls": {
                    "480": "http://127.0.0.1:8000/static/images/room_tv.jpg",
                    "960": "http://127.0.0.1:8000/static/images/room_tv.jpg",
                    "1600": "http://127.0.0.1:8000/static/images/room_tv.jpg",
                },
            },
            {
                "id": 3,
                "alt": "Xonaning toʻliq koʻrinishi",
                "is_cover": False,
                "urls": {
                    "480": "http://127.0.0.1:8000/static/images/room_full.png",
                    "960": "http://127.0.0.1:8000/static/images/room_full.png",
                    "1600": "http://127.0.0.1:8000/static/images/room_full.png",
                },
            },
            {
                "id": 4,
                "alt": "Zamonaviy dush va hojatxona",
                "is_cover": False,
                "urls": {
                    "480": "http://127.0.0.1:8000/static/images/bathroom.jpg",
                    "960": "http://127.0.0.1:8000/static/images/bathroom.jpg",
                    "1600": "http://127.0.0.1:8000/static/images/bathroom.jpg",
                },
            },
        ],
    },
    {
        "key": "double_room_2",
        "name": "2 kishilik shinam xona (№2)",
        "description": "2 kishilik qulay xona. Zamonaviy yoritgichlar, konditsioner, Smart TV, alohida toza dush xonasi. Narxi 400 000 soʻm (kelishilgan holda arzonlashtirib ham beramiz).",
        "amenities": ["Wi-Fi", "Smart TV", "Konditsioner", "Alohida dush va hojatxona", "Kelishiladi", "24/7 Xizmat"],
        "price_per_night": 400000,
        "count": 1,
        "cover_960": "http://127.0.0.1:8000/static/images/room2_beds.png",
        "images": [
            {
                "id": 5,
                "alt": "2 kishilik yotoqlar va bra (№2 xona)",
                "is_cover": True,
                "urls": {
                    "480": "http://127.0.0.1:8000/static/images/room2_beds.png",
                    "960": "http://127.0.0.1:8000/static/images/room2_beds.png",
                    "1600": "http://127.0.0.1:8000/static/images/room2_beds.png",
                },
            },
            {
                "id": 6,
                "alt": "Smart TV va lyustra",
                "is_cover": False,
                "urls": {
                    "480": "http://127.0.0.1:8000/static/images/room2_tv.png",
                    "960": "http://127.0.0.1:8000/static/images/room2_tv.png",
                    "1600": "http://127.0.0.1:8000/static/images/room2_tv.png",
                },
            },
            {
                "id": 7,
                "alt": "Xonaning kirish qismidan koʻrinishi",
                "is_cover": False,
                "urls": {
                    "480": "http://127.0.0.1:8000/static/images/room2_view.png",
                    "960": "http://127.0.0.1:8000/static/images/room2_view.png",
                    "1600": "http://127.0.0.1:8000/static/images/room2_view.png",
                },
            },
            {
                "id": 8,
                "alt": "Alohida dush va vanna xonasi",
                "is_cover": False,
                "urls": {
                    "480": "http://127.0.0.1:8000/static/images/room2_bathroom.jpg",
                    "960": "http://127.0.0.1:8000/static/images/room2_bathroom.jpg",
                    "1600": "http://127.0.0.1:8000/static/images/room2_bathroom.jpg",
                },
            },
        ],
    },
    {
        "key": "triple_room",
        "name": "3 kishilik shinam xona",
        "description": "3 kishilik keng va shinam xona. 3 ta alohida toza yotoq, sochiqlar, Smart TV, konditsioner, fen, garderob va alohida dush xonasi. Narxi 500 000 soʻm (kelishilgan holda arzonlashtirib ham beramiz).",
        "amenities": ["3 ta yotoq", "Wi-Fi", "Smart TV", "Konditsioner", "Fen va garderob", "Alohida dush", "Kelishiladi", "24/7 Xizmat"],
        "price_per_night": 500000,
        "count": 1,
        "cover_960": "http://127.0.0.1:8000/static/images/room3_beds.jpg",
        "images": [
            {
                "id": 9,
                "alt": "3 ta alohida yotoq va parda",
                "is_cover": True,
                "urls": {
                    "480": "http://127.0.0.1:8000/static/images/room3_beds.jpg",
                    "960": "http://127.0.0.1:8000/static/images/room3_beds.jpg",
                    "1600": "http://127.0.0.1:8000/static/images/room3_beds.jpg",
                },
            },
            {
                "id": 10,
                "alt": "Xonaning yotoqlar va lyustra bilan koʻrinishi",
                "is_cover": False,
                "urls": {
                    "480": "http://127.0.0.1:8000/static/images/room3_full.jpg",
                    "960": "http://127.0.0.1:8000/static/images/room3_full.jpg",
                    "1600": "http://127.0.0.1:8000/static/images/room3_full.jpg",
                },
            },
            {
                "id": 11,
                "alt": "Alohida zamonaviy dush xonasi",
                "is_cover": False,
                "urls": {
                    "480": "http://127.0.0.1:8000/static/images/room3_bathroom.png",
                    "960": "http://127.0.0.1:8000/static/images/room3_bathroom.png",
                    "1600": "http://127.0.0.1:8000/static/images/room3_bathroom.png",
                },
            },
            {
                "id": 12,
                "alt": "Kiyim javoni va fen",
                "is_cover": False,
                "urls": {
                    "480": "http://127.0.0.1:8000/static/images/room3_wardrobe.png",
                    "960": "http://127.0.0.1:8000/static/images/room3_wardrobe.png",
                    "1600": "http://127.0.0.1:8000/static/images/room3_wardrobe.png",
                },
            },
        ],
    },
]

BOOKINGS_STORE: List[Dict[str, Any]] = []
_booking_counter = 100


def verify_key(x_api_key: Optional[str] = Header(None)):
    if not x_api_key or not hmac.compare_digest(x_api_key, API_KEY):
        raise HTTPException(status_code=403, detail="forbidden")


# --- Frontend Web Routes (Multi-Page Architecture) ---

@app.get("/", response_class=HTMLResponse)
def index_page():
    return (TEMPLATES_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/about", response_class=HTMLResponse)
def about_page():
    return (TEMPLATES_DIR / "about.html").read_text(encoding="utf-8")


@app.get("/videos", response_class=HTMLResponse)
def videos_page():
    return (TEMPLATES_DIR / "videos.html").read_text(encoding="utf-8")


@app.get("/rooms", response_class=HTMLResponse)
def rooms_page():
    return (TEMPLATES_DIR / "rooms.html").read_text(encoding="utf-8")


@app.get("/rules", response_class=HTMLResponse)
def rules_page():
    return (TEMPLATES_DIR / "rules.html").read_text(encoding="utf-8")


@app.get("/contact", response_class=HTMLResponse)
def contact_page():
    return (TEMPLATES_DIR / "contact.html").read_text(encoding="utf-8")


# --- REST API Endpoints ---

@app.get("/api/hotel")
def get_hotel():
    return {"hotel": HOTEL_DATA}


@app.get("/api/rooms")
def get_rooms():
    return {"rooms": ROOMS_DATA}


@app.get("/api/rooms/{key}")
def get_room(key: str):
    for r in ROOMS_DATA:
        if r["key"] == key:
            return {"room": r}
    raise HTTPException(status_code=404, detail="not_found")


@app.get("/api/rooms/{key}/calendar")
def get_calendar(key: str, from_date: str = Query(..., alias="from"), days: int = 90):
    start = datetime.strptime(from_date, "%Y-%m-%d").date()
    result = []
    for i in range(days):
        d = start + timedelta(days=i)
        result.append({"date": d.strftime("%Y-%m-%d"), "free": 1})
    return {"days": result}


@app.get("/api/availability")
def check_availability(room: str, checkin: str, nights: int):
    found = None
    for r in ROOMS_DATA:
        if r["key"] == room:
            found = r
            break
    if not found:
        return {"available": False, "price_per_night": 0, "total": 0}

    price = found["price_per_night"]
    return {"available": True, "price_per_night": price, "total": price * nights}


class CreateBookingRequest(BaseModel):
    room: str
    checkin: str
    nights: int
    name: str
    phone: str
    source: str = "bot"
    telegram_id: Optional[int] = None
    username: Optional[str] = None


@app.post("/api/bookings", status_code=201)
def create_booking(req: CreateBookingRequest, x_api_key: Optional[str] = Header(None)):
    verify_key(x_api_key)
    global _booking_counter
    _booking_counter += 1

    room_obj = next((r for r in ROOMS_DATA if r["key"] == req.room), None)
    if not room_obj:
        raise HTTPException(status_code=422, detail="validation_error")

    now = datetime.now(UZB_TZ)
    hold_until = now + timedelta(minutes=15)
    checkin_dt = datetime.strptime(req.checkin, "%Y-%m-%d").date()
    checkout_dt = checkin_dt + timedelta(days=req.nights)

    total = room_obj["price_per_night"] * req.nights
    code = f"BR-{_booking_counter}"

    booking = {
        "id": _booking_counter,
        "code": code,
        "room": req.room,
        "room_name": room_obj["name"],
        "checkin": req.checkin,
        "checkout": checkout_dt.strftime("%Y-%m-%d"),
        "nights": req.nights,
        "total": total,
        "status": "pending",
        "source": req.source,
        "name": req.name,
        "phone": req.phone,
        "telegram_id": req.telegram_id,
        "created_at": now.isoformat(),
        "hold_until": hold_until.isoformat(),
    }
    BOOKINGS_STORE.append(booking)

    payment = {
        "card_number": "8600123456789012",
        "card_owner": "SAM REST HOSTEL MCHJ",
    }
    return {"booking": booking, "payment": payment}


@app.get("/api/bookings/{code}/payment")
def get_payment(code: str, telegram_id: Optional[int] = None, phone: Optional[str] = None):
    b = next((x for x in BOOKINGS_STORE if x["code"] == code), None)
    if not b:
        raise HTTPException(status_code=404, detail="not_found")
    if b["status"] != "pending":
        raise HTTPException(status_code=409, detail="wrong_status")

    payment = {
        "card_number": "8600123456789012",
        "card_owner": "SAM REST HOSTEL MCHJ",
    }
    return {"booking": b, "payment": payment}


@app.post("/api/bookings/{code}/receipt")
async def upload_receipt(
    code: str,
    file: UploadFile = File(...),
    telegram_id: Optional[int] = Form(None),
    phone: Optional[str] = Form(None),
):
    b = next((x for x in BOOKINGS_STORE if x["code"] == code), None)
    if not b:
        raise HTTPException(status_code=404, detail="not_found")
    if b["status"] != "pending":
        raise HTTPException(status_code=409, detail="wrong_status")

    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=422, detail="invalid_file")

    b["status"] = "waiting_admin"
    return {"booking": b}


class CancelRequest(BaseModel):
    phone: Optional[str] = None
    telegram_id: Optional[int] = None


@app.post("/api/bookings/{code}/cancel")
def cancel_booking(code: str, req: CancelRequest):
    b = next((x for x in BOOKINGS_STORE if x["code"] == code), None)
    if not b:
        raise HTTPException(status_code=404, detail="not_found")
    if b["status"] != "pending":
        raise HTTPException(status_code=409, detail="wrong_status")

    b["status"] = "cancelled"
    return {"booking": b}


@app.get("/api/bookings/lookup")
def lookup_booking(code: str, phone: str):
    for b in BOOKINGS_STORE:
        if b["code"].upper() == code.upper() and b["phone"] == phone:
            return {"booking": b}
    raise HTTPException(status_code=404, detail="not_found")


@app.get("/api/bookings/by-telegram/{telegram_id}")
def get_by_telegram(
    telegram_id: int,
    phone: Optional[str] = None,
    x_api_key: Optional[str] = Header(None),
):
    verify_key(x_api_key)
    matches = []
    for b in reversed(BOOKINGS_STORE):
        if b.get("telegram_id") == telegram_id or (phone and b.get("phone") == phone):
            matches.append(b)
        if len(matches) == 5:
            break
    return {"bookings": matches}


@app.get("/api/admin/bookings/upcoming")
def get_admin_upcoming(
    admin_telegram_id: int,
    x_api_key: Optional[str] = Header(None),
):
    verify_key(x_api_key)
    confirmed = [b for b in BOOKINGS_STORE if b.get("status") == "confirmed"]
    return {"bookings": confirmed[:30]}


class DecisionRequest(BaseModel):
    action: str
    admin_telegram_id: int


@app.post("/api/admin/bookings/{id}/decision")
def admin_decision(
    id: int,
    req: DecisionRequest,
    x_api_key: Optional[str] = Header(None),
):
    verify_key(x_api_key)
    b = next((x for x in BOOKINGS_STORE if x["id"] == id), None)
    if not b:
        raise HTTPException(status_code=404, detail="not_found")
    if b["status"] in ("confirmed", "rejected"):
        raise HTTPException(status_code=409, detail="already_decided")

    if req.action == "approve":
        b["status"] = "confirmed"
    else:
        b["status"] = "rejected"

    return {"booking": b}
