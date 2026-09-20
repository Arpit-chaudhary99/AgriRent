from fastapi import FastAPI, APIRouter, HTTPException, Query, Request, Header, Depends, UploadFile, File, Response
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import uuid
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Literal
import razorpay
import httpx
import requests
from datetime import datetime, timezone, timedelta, date


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]
razorpay_client = razorpay.Client(auth=(os.environ['RAZORPAY_KEY_ID'], os.environ['RAZORPAY_KEY_SECRET']))
ADMIN_EMAIL = (os.environ.get('ADMIN_EMAIL') or '').strip().lower()

# Object storage
STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
APP_NAME = "agrirent"
_storage_key = {"value": None}


def init_storage(force: bool = False):
    if _storage_key["value"] and not force:
        return _storage_key["value"]
    if not EMERGENT_KEY:
        raise RuntimeError("EMERGENT_LLM_KEY missing — storage disabled")
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
    resp.raise_for_status()
    _storage_key["value"] = resp.json()["storage_key"]
    return _storage_key["value"]


def storage_put(path: str, data: bytes, content_type: str) -> dict:
    key = init_storage()
    r = requests.put(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key, "Content-Type": content_type}, data=data, timeout=120)
    if r.status_code == 404:
        key = init_storage(force=True)
        r = requests.put(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key, "Content-Type": content_type}, data=data, timeout=120)
    r.raise_for_status()
    return r.json()


def storage_get(path: str):
    key = init_storage()
    r = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    if r.status_code == 404:
        key = init_storage(force=True)
        r = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    r.raise_for_status()
    return r.content, r.headers.get("Content-Type", "application/octet-stream")


app = FastAPI()
api_router = APIRouter(prefix="/api")


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    role: Literal["USER", "ADMIN"] = "USER"
    blocked: bool = False
    created_at: str

class Tool(BaseModel):
    id: str
    name: str
    category: str
    description: str
    location: str
    owner: str
    hourly_rate: float
    daily_rate: float
    available: bool = True
    image_url: str
    rating: float = 4.8

class ToolCreate(BaseModel):
    name: str
    category: str
    description: str = ""
    location: str
    owner: str = "AgriRent Fleet"
    hourly_rate: float = 0
    daily_rate: float
    available: bool = True
    image_url: str = ""
    rating: float = 4.7

class ToolPatch(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    owner: Optional[str] = None
    hourly_rate: Optional[float] = None
    daily_rate: Optional[float] = None
    available: Optional[bool] = None
    image_url: Optional[str] = None
    rating: Optional[float] = None

class RentalCreate(BaseModel):
    tool_id: str
    start_date: date
    end_date: date

class Rental(BaseModel):
    id: str
    tool_id: str
    tool_name: str
    user_id: str
    user_email: str
    renter_name: str
    start_date: str
    end_date: str
    days: int
    total: float
    status: str
    requested_at: str
    payment_status: str = "unpaid"
    razorpay_order_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    amount_paid: Optional[float] = None
    paid_at: Optional[str] = None
    payment_method: Optional[str] = None
    last_payment_error: Optional[str] = None

class PaymentVerify(BaseModel):
    rental_id: str
    razorpay_payment_id: str
    razorpay_order_id: str
    razorpay_signature: str

class PaymentFailure(BaseModel):
    rental_id: str
    razorpay_order_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    reason: Optional[str] = None

class SessionExchange(BaseModel):
    session_id: str

class BlockToggle(BaseModel):
    blocked: bool


SEED_TOOLS = [
    {"id":"tool-001","name":"Compact Field Tractor","category":"Tractors","description":"Reliable 45 HP tractor for ploughing, hauling and everyday field work.","location":"Nashik, Maharashtra","owner":"Green Valley Co-op","hourly_rate":850,"daily_rate":5800,"available":True,"image_url":"https://images.unsplash.com/photo-1606739211185-2c846d734a6d?auto=format&fit=crop&w=900&q=80","rating":4.9},
    {"id":"tool-002","name":"Heavy Duty Harvester","category":"Harvesting","description":"High-capacity harvester that keeps grain collection moving during peak season.","location":"Pune, Maharashtra","owner":"Kisan Equipment House","hourly_rate":1200,"daily_rate":8200,"available":True,"image_url":"https://images.unsplash.com/photo-1614977645968-6db1d7798ac7?auto=format&fit=crop&w=900&q=80","rating":4.8},
    {"id":"tool-003","name":"Rotary Power Tiller","category":"Tillage","description":"Easy-to-handle tiller for seedbed preparation, weeding and small plots.","location":"Satara, Maharashtra","owner":"Sahyadri Tools","hourly_rate":420,"daily_rate":2900,"available":True,"image_url":"https://images.unsplash.com/photo-1602446692855-6d096499f69b?auto=format&fit=crop&w=900&q=80","rating":4.7},
    {"id":"tool-004","name":"Precision Seed Drill","category":"Planting","description":"Consistent row spacing and seed depth for faster, more uniform planting.","location":"Kolhapur, Maharashtra","owner":"Harvest First Rentals","hourly_rate":650,"daily_rate":4500,"available":True,"image_url":"https://images.unsplash.com/photo-1592982537447-7440770cbfc9?auto=format&fit=crop&f=crop&w=900&q=80","rating":4.6},
]


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
async def _resolve_session_token(request: Request) -> Optional[str]:
    tok = request.cookies.get("session_token")
    if tok:
        return tok
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        return auth_header.split(" ", 1)[1].strip()
    return None


async def current_user(request: Request) -> User:
    token = await _resolve_session_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    sess = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not sess:
        raise HTTPException(status_code=401, detail="Session not found")
    expires_at = sess.get("expires_at")
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at and expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")
    user_doc = await db.users.find_one({"user_id": sess["user_id"]}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    if user_doc.get("blocked"):
        raise HTTPException(status_code=403, detail="Account has been blocked. Please contact support.")
    return User(**user_doc)


async def current_admin(user: User = Depends(current_user)) -> User:
    if user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def _startup():
    # Seed tools if none
    if await db.tools.count_documents({}) == 0:
        await db.tools.insert_many(SEED_TOOLS)
    # One-time wipe: remove legacy rentals (created before auth was introduced)
    if await db.rentals.count_documents({"user_id": {"$exists": False}}) > 0:
        await db.rentals.delete_many({"user_id": {"$exists": False}})
        await db.payments.delete_many({"user_id": {"$exists": False}})
    # Init object storage (best-effort)
    try:
        init_storage()
        logger.info("Object storage initialized")
    except Exception as e:
        logger.warning(f"Object storage init failed: {e}")


# ---------------------------------------------------------------------------
# Public routes
# ---------------------------------------------------------------------------
@api_router.get("/")
async def root():
    return {"message": "AgriRent Pro API"}


@api_router.get("/tools", response_model=List[Tool])
async def get_tools(search: Optional[str] = Query(None), category: Optional[str] = Query(None), available: Optional[bool] = Query(None)):
    query = {}
    if search:
        query["$or"] = [{"name": {"$regex": search, "$options": "i"}}, {"category": {"$regex": search, "$options": "i"}}, {"location": {"$regex": search, "$options": "i"}}]
    if category and category != "All tools":
        query["category"] = category
    if available is not None:
        query["available"] = available
    docs = await db.tools.find(query, {"_id": 0}).to_list(500)
    return docs


@api_router.get("/tools/{tool_id}", response_model=Tool)
async def get_tool(tool_id: str):
    tool = await db.tools.find_one({"id": tool_id}, {"_id": 0})
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    return tool


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------
@api_router.post("/auth/session")
async def exchange_session(payload: SessionExchange, response: Response):
    """Exchange Emergent Auth session_id for a persistent session_token cookie."""
    try:
        async with httpx.AsyncClient(timeout=15) as http:
            r = await http.get("https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data", headers={"X-Session-ID": payload.session_id})
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Auth provider unreachable: {e}")
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid session_id")
    data = r.json()
    email = (data.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Google account is missing an email")
    existing = await db.users.find_one({"email": email}, {"_id": 0})
    role = "ADMIN" if email == ADMIN_EMAIL else "USER"
    if existing:
        user_id = existing["user_id"]
        # Promote existing user if they match ADMIN_EMAIL and were still USER
        update = {"name": data.get("name") or existing.get("name"), "picture": data.get("picture") or existing.get("picture")}
        if email == ADMIN_EMAIL and existing.get("role") != "ADMIN":
            update["role"] = "ADMIN"
        await db.users.update_one({"user_id": user_id}, {"$set": update})
        if existing.get("blocked"):
            raise HTTPException(status_code=403, detail="Account has been blocked. Please contact support.")
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        await db.users.insert_one({
            "user_id": user_id,
            "email": email,
            "name": data.get("name") or email.split("@")[0],
            "picture": data.get("picture"),
            "role": role,
            "blocked": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    session_token = data.get("session_token") or f"tok_{uuid.uuid4().hex}"
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    await db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": expires_at,
        "created_at": datetime.now(timezone.utc),
    })
    response.set_cookie(key="session_token", value=session_token, httponly=True, secure=True, samesite="none", path="/", max_age=7 * 24 * 60 * 60)
    user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    return {"user": user_doc, "session_token": session_token}


@api_router.get("/auth/me", response_model=User)
async def auth_me(user: User = Depends(current_user)):
    return user


@api_router.post("/auth/logout")
async def auth_logout(request: Request, response: Response):
    token = await _resolve_session_token(request)
    if token:
        await db.user_sessions.delete_one({"session_token": token})
    response.delete_cookie("session_token", path="/")
    return {"ok": True}


# ---------------------------------------------------------------------------
# User (authenticated) rental routes
# ---------------------------------------------------------------------------
@api_router.get("/rentals", response_model=List[Rental])
async def list_my_rentals(user: User = Depends(current_user), status: Optional[str] = Query(None)):
    q = {"user_id": user.user_id}
    if status:
        q["status"] = status
    docs = await db.rentals.find(q, {"_id": 0}).sort("requested_at", -1).to_list(500)
    return docs


@api_router.post("/rentals", response_model=Rental)
async def create_rental(input: RentalCreate, user: User = Depends(current_user)):
    tool = await db.tools.find_one({"id": input.tool_id}, {"_id": 0})
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    if not tool["available"]:
        raise HTTPException(status_code=400, detail="Tool is currently unavailable")
    if input.end_date < input.start_date:
        raise HTTPException(status_code=400, detail="End date must be after start date")
    days = max(1, (input.end_date - input.start_date).days + 1)
    total = days * tool["daily_rate"]
    rental = {
        "id": str(uuid.uuid4()),
        "tool_id": tool["id"],
        "tool_name": tool["name"],
        "user_id": user.user_id,
        "user_email": user.email,
        "renter_name": user.name,
        "start_date": input.start_date.isoformat(),
        "end_date": input.end_date.isoformat(),
        "days": days,
        "total": total,
        "status": "Requested",
        "requested_at": datetime.now(timezone.utc).isoformat(),
        "payment_status": "unpaid",
    }
    await db.rentals.insert_one(rental)
    return Rental(**rental)


@api_router.get("/rentals/{rental_id}", response_model=Rental)
async def get_rental(rental_id: str, user: User = Depends(current_user)):
    rental = await db.rentals.find_one({"id": rental_id}, {"_id": 0})
    if not rental:
        raise HTTPException(status_code=404, detail="Rental not found")
    if user.role != "ADMIN" and rental["user_id"] != user.user_id:
        raise HTTPException(status_code=403, detail="You cannot view this rental")
    return Rental(**rental)


@api_router.post("/rentals/{rental_id}/cancel", response_model=Rental)
async def cancel_rental(rental_id: str, user: User = Depends(current_user)):
    rental = await db.rentals.find_one({"id": rental_id}, {"_id": 0})
    if not rental:
        raise HTTPException(status_code=404, detail="Rental not found")
    if user.role != "ADMIN" and rental["user_id"] != user.user_id:
        raise HTTPException(status_code=403, detail="You cannot cancel this rental")
    if rental.get("payment_status") == "paid":
        raise HTTPException(status_code=400, detail="Paid rentals cannot be cancelled from here")
    await db.rentals.update_one({"id": rental_id}, {"$set": {"status": "Cancelled"}})
    updated = await db.rentals.find_one({"id": rental_id}, {"_id": 0})
    return Rental(**updated)


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------
@api_router.post("/payments/order")
async def create_payment_order(rental_id: str, user: User = Depends(current_user)):
    rental = await db.rentals.find_one({"id": rental_id}, {"_id": 0})
    if not rental:
        raise HTTPException(status_code=404, detail="Rental not found")
    if rental["user_id"] != user.user_id:
        raise HTTPException(status_code=403, detail="You cannot pay for someone else's rental")
    if rental.get("status") != "Approved":
        raise HTTPException(status_code=400, detail="Rental must be approved before payment")
    if rental.get("payment_status") == "paid":
        raise HTTPException(status_code=400, detail="Rental is already paid")
    order = razorpay_client.order.create({
        "amount": int(round(rental["total"] * 100)),
        "currency": "INR",
        "receipt": f"rent_{rental_id[:30]}",
        "payment_capture": 1,
    })
    await db.rentals.update_one({"id": rental_id}, {"$set": {"razorpay_order_id": order["id"], "payment_status": "created"}})
    return {"id": order["id"], "amount": order["amount"], "currency": order["currency"], "key_id": os.environ["RAZORPAY_KEY_ID"]}


@api_router.post("/payments/verify")
async def verify_payment(input: PaymentVerify, user: User = Depends(current_user)):
    rental = await db.rentals.find_one({"id": input.rental_id}, {"_id": 0})
    if not rental:
        raise HTTPException(status_code=404, detail="Rental not found")
    if rental["user_id"] != user.user_id:
        raise HTTPException(status_code=403, detail="Cannot verify someone else's payment")
    if rental.get("payment_status") == "paid":
        return {"status": "paid", "rental_id": input.rental_id, "duplicate": True}
    if rental.get("razorpay_order_id") != input.razorpay_order_id:
        raise HTTPException(status_code=400, detail="Payment order does not match rental")
    try:
        razorpay_client.utility.verify_payment_signature({
            "razorpay_order_id": input.razorpay_order_id,
            "razorpay_payment_id": input.razorpay_payment_id,
            "razorpay_signature": input.razorpay_signature,
        })
    except Exception:
        await db.rentals.update_one({"id": input.rental_id}, {"$set": {"payment_status": "PAYMENT_PENDING"}})
        raise HTTPException(status_code=400, detail="Payment signature verification failed")
    payment_method = None
    try:
        fetched = razorpay_client.payment.fetch(input.razorpay_payment_id)
        payment_method = fetched.get("method")
    except Exception as e:
        logger.warning(f"Could not fetch payment method: {e}")
    paid_at = datetime.now(timezone.utc).isoformat()
    await db.rentals.update_one({"id": input.rental_id}, {"$set": {
        "status": "Paid",
        "payment_status": "paid",
        "razorpay_payment_id": input.razorpay_payment_id,
        "amount_paid": rental["total"],
        "paid_at": paid_at,
        "payment_method": payment_method,
    }})
    await db.tools.update_one({"id": rental["tool_id"]}, {"$set": {"available": False}})
    await db.payments.update_one({"razorpay_payment_id": input.razorpay_payment_id}, {"$setOnInsert": {
        "rental_id": input.rental_id,
        "user_id": rental["user_id"],
        "user_email": rental["user_email"],
        "tool_name": rental["tool_name"],
        "renter_name": rental["renter_name"],
        "razorpay_order_id": input.razorpay_order_id,
        "razorpay_payment_id": input.razorpay_payment_id,
        "amount": rental["total"],
        "payment_status": "paid",
        "payment_method": payment_method,
        "source": "checkout",
        "paid_at": paid_at,
        "created_at": paid_at,
    }}, upsert=True)
    return {"status": "paid", "rental_id": input.rental_id, "payment_method": payment_method}


@api_router.post("/payments/failed")
async def record_payment_failure(input: PaymentFailure, user: User = Depends(current_user)):
    rental = await db.rentals.find_one({"id": input.rental_id}, {"_id": 0})
    if not rental:
        raise HTTPException(status_code=404, detail="Rental not found")
    if rental["user_id"] != user.user_id:
        raise HTTPException(status_code=403, detail="Cannot flag someone else's payment")
    if rental.get("payment_status") == "paid":
        return {"status": "paid", "duplicate": True}
    now_iso = datetime.now(timezone.utc).isoformat()
    await db.rentals.update_one({"id": input.rental_id}, {"$set": {
        "payment_status": "PAYMENT_PENDING",
        "last_payment_error": (input.description or input.reason or input.code or "cancelled"),
    }})
    if input.razorpay_payment_id:
        await db.payments.update_one({"razorpay_payment_id": input.razorpay_payment_id}, {"$set": {
            "rental_id": input.rental_id,
            "user_id": rental["user_id"],
            "tool_name": rental["tool_name"],
            "renter_name": rental["renter_name"],
            "razorpay_order_id": input.razorpay_order_id or rental.get("razorpay_order_id"),
            "razorpay_payment_id": input.razorpay_payment_id,
            "amount": rental["total"],
            "payment_status": "failed",
            "source": "checkout",
            "failed_at": now_iso,
            "created_at": now_iso,
            "error_code": input.code,
            "error_description": input.description,
        }}, upsert=True)
    return {"status": "pending"}


@api_router.post("/payments/webhook")
async def razorpay_webhook(request: Request, x_razorpay_signature: Optional[str] = Header(None)):
    body = await request.body()
    secret = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "")
    if not secret:
        raise HTTPException(status_code=503, detail="Webhook secret not configured")
    if not x_razorpay_signature:
        raise HTTPException(status_code=400, detail="Missing signature header")
    try:
        razorpay_client.utility.verify_webhook_signature(body.decode("utf-8"), x_razorpay_signature, secret)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
    payload = await request.json()
    event = payload.get("event", "")
    entity = payload.get("payload", {}).get("payment", {}).get("entity", {}) or {}
    order_id = entity.get("order_id")
    payment_id = entity.get("id")
    amount = (entity.get("amount") or 0) / 100
    method = entity.get("method")
    if not order_id or not payment_id:
        return {"received": True, "ignored": True}
    rental = await db.rentals.find_one({"razorpay_order_id": order_id}, {"_id": 0})
    if not rental:
        return {"received": True, "unknown_order": order_id}
    now_iso = datetime.now(timezone.utc).isoformat()
    if event in ("payment.captured", "payment.authorized"):
        if rental.get("payment_status") != "paid":
            await db.rentals.update_one({"id": rental["id"]}, {"$set": {"status": "Paid", "payment_status": "paid", "razorpay_payment_id": payment_id, "amount_paid": amount, "paid_at": now_iso, "payment_method": method}})
            await db.tools.update_one({"id": rental["tool_id"]}, {"$set": {"available": False}})
        await db.payments.update_one({"razorpay_payment_id": payment_id}, {"$setOnInsert": {"rental_id": rental["id"], "user_id": rental.get("user_id"), "tool_name": rental.get("tool_name"), "renter_name": rental.get("renter_name"), "razorpay_order_id": order_id, "razorpay_payment_id": payment_id, "amount": amount, "payment_status": "paid", "payment_method": method, "source": "webhook", "paid_at": now_iso, "created_at": now_iso}}, upsert=True)
    elif event == "payment.failed":
        if rental.get("payment_status") != "paid":
            await db.rentals.update_one({"id": rental["id"]}, {"$set": {"payment_status": "PAYMENT_PENDING"}})
        await db.payments.update_one({"razorpay_payment_id": payment_id}, {"$set": {"rental_id": rental["id"], "user_id": rental.get("user_id"), "tool_name": rental.get("tool_name"), "renter_name": rental.get("renter_name"), "razorpay_order_id": order_id, "razorpay_payment_id": payment_id, "amount": amount, "payment_status": "failed", "payment_method": method, "source": "webhook", "failed_at": now_iso, "created_at": now_iso}}, upsert=True)
    return {"received": True, "event": event}


@api_router.get("/payments/methods")
async def payment_methods():
    kid = os.environ["RAZORPAY_KEY_ID"]
    try:
        async with httpx.AsyncClient(timeout=8) as http:
            r = await http.get(f"https://api.razorpay.com/v1/methods?key_id={kid}")
            data = r.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not reach Razorpay: {e}")
    return {"upi_collect": bool(data.get("upi")), "upi_intent": bool(data.get("upi_intent")), "card": bool(data.get("card")), "netbanking": bool(data.get("netbanking")), "wallet": bool(data.get("wallet")), "mode": "test" if kid.startswith("rzp_test") else "live"}


@api_router.get("/payments/history")
async def my_payments_history(user: User = Depends(current_user)):
    return await db.payments.find({"user_id": user.user_id}, {"_id": 0}).sort("paid_at", -1).to_list(500)


# ---------------------------------------------------------------------------
# Admin routes
# ---------------------------------------------------------------------------
@api_router.get("/admin/stats")
async def admin_stats(_: User = Depends(current_admin)):
    total_tools = await db.tools.count_documents({})
    available_tools = await db.tools.count_documents({"available": True})
    total_users = await db.users.count_documents({})
    active_rentals = await db.rentals.count_documents({"status": {"$in": ["Requested", "Approved"]}})
    paid_rentals = await db.rentals.count_documents({"status": "Paid"})
    cancelled_rentals = await db.rentals.count_documents({"status": "Cancelled"})
    revenue_agg = await db.payments.aggregate([{"$match": {"payment_status": "paid"}}, {"$group": {"_id": None, "total": {"$sum": "$amount"}}}]).to_list(1)
    total_revenue = (revenue_agg[0]["total"] if revenue_agg else 0)
    return {
        "total_tools": total_tools,
        "available_tools": available_tools,
        "total_users": total_users,
        "active_rentals": active_rentals,
        "paid_rentals": paid_rentals,
        "cancelled_rentals": cancelled_rentals,
        "total_revenue": total_revenue,
    }


@api_router.get("/admin/tools", response_model=List[Tool])
async def admin_list_tools(_: User = Depends(current_admin)):
    return await db.tools.find({}, {"_id": 0}).to_list(500)


@api_router.post("/admin/tools", response_model=Tool)
async def admin_create_tool(input: ToolCreate, _: User = Depends(current_admin)):
    tool = {"id": f"tool-{uuid.uuid4().hex[:8]}", **input.model_dump()}
    if not tool["image_url"]:
        tool["image_url"] = "https://images.unsplash.com/photo-1500595046743-cd271d694d30?auto=format&fit=crop&w=900&q=80"
    await db.tools.insert_one(tool)
    tool.pop("_id", None)
    return Tool(**tool)


@api_router.patch("/admin/tools/{tool_id}", response_model=Tool)
async def admin_update_tool(tool_id: str, input: ToolPatch, _: User = Depends(current_admin)):
    tool = await db.tools.find_one({"id": tool_id}, {"_id": 0})
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    changes = {k: v for k, v in input.model_dump(exclude_unset=True).items() if v is not None}
    if changes:
        await db.tools.update_one({"id": tool_id}, {"$set": changes})
    updated = await db.tools.find_one({"id": tool_id}, {"_id": 0})
    return Tool(**updated)


@api_router.delete("/admin/tools/{tool_id}")
async def admin_delete_tool(tool_id: str, _: User = Depends(current_admin)):
    active = await db.rentals.count_documents({"tool_id": tool_id, "status": {"$in": ["Requested", "Approved", "Paid"]}})
    if active > 0:
        raise HTTPException(status_code=400, detail=f"Cannot delete — {active} active rentals still reference this tool")
    result = await db.tools.delete_one({"id": tool_id})
    if not result.deleted_count:
        raise HTTPException(status_code=404, detail="Tool not found")
    return {"ok": True}


@api_router.post("/admin/tools/{tool_id}/image")
async def admin_upload_tool_image(tool_id: str, file: UploadFile = File(...), user: User = Depends(current_admin)):
    tool = await db.tools.find_one({"id": tool_id}, {"_id": 0})
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    ext = (file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "bin").lower()
    if ext not in {"jpg", "jpeg", "png", "webp", "gif"}:
        raise HTTPException(status_code=400, detail="Unsupported image type")
    path = f"{APP_NAME}/tools/{tool_id}/{uuid.uuid4().hex}.{ext}"
    data = await file.read()
    try:
        result = storage_put(path, data, file.content_type or f"image/{ext}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Object storage upload failed: {e}")
    await db.tool_files.insert_one({
        "id": str(uuid.uuid4()),
        "tool_id": tool_id,
        "storage_path": result["path"],
        "original_filename": file.filename,
        "content_type": file.content_type,
        "size": result.get("size"),
        "is_deleted": False,
        "uploaded_by": user.user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    # Publicly-readable relative URL served via /api/files
    image_url = f"/api/files/{result['path']}"
    await db.tools.update_one({"id": tool_id}, {"$set": {"image_url": image_url}})
    return {"image_url": image_url, "storage_path": result["path"]}


@api_router.get("/files/{path:path}")
async def serve_file(path: str):
    record = await db.tool_files.find_one({"storage_path": path, "is_deleted": False}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    try:
        data, ct = storage_get(path)
    except Exception:
        raise HTTPException(status_code=404, detail="File missing from storage")
    return Response(content=data, media_type=record.get("content_type") or ct)


@api_router.get("/admin/users")
async def admin_list_users(_: User = Depends(current_admin), search: Optional[str] = Query(None)):
    q = {}
    if search:
        q["$or"] = [{"email": {"$regex": search, "$options": "i"}}, {"name": {"$regex": search, "$options": "i"}}]
    users = await db.users.find(q, {"_id": 0}).sort("created_at", -1).to_list(1000)
    # Attach rental counts
    for u in users:
        u["rental_count"] = await db.rentals.count_documents({"user_id": u["user_id"]})
        u["total_spent"] = ((await db.payments.aggregate([{"$match": {"user_id": u["user_id"], "payment_status": "paid"}}, {"$group": {"_id": None, "t": {"$sum": "$amount"}}}]).to_list(1)) or [{"t": 0}])[0]["t"]
    return users


@api_router.patch("/admin/users/{user_id}/block")
async def admin_block_user(user_id: str, payload: BlockToggle, admin: User = Depends(current_admin)):
    target = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target["email"] == ADMIN_EMAIL:
        raise HTTPException(status_code=400, detail="Cannot block the primary admin")
    await db.users.update_one({"user_id": user_id}, {"$set": {"blocked": payload.blocked}})
    if payload.blocked:
        await db.user_sessions.delete_many({"user_id": user_id})
    return {"ok": True, "blocked": payload.blocked}


@api_router.get("/admin/rentals")
async def admin_list_rentals(_: User = Depends(current_admin), status: Optional[str] = Query(None), search: Optional[str] = Query(None)):
    q = {}
    if status:
        q["status"] = status
    if search:
        q["$or"] = [{"tool_name": {"$regex": search, "$options": "i"}}, {"user_email": {"$regex": search, "$options": "i"}}, {"renter_name": {"$regex": search, "$options": "i"}}]
    return await db.rentals.find(q, {"_id": 0}).sort("requested_at", -1).to_list(1000)


@api_router.patch("/admin/rentals/{rental_id}/approve")
async def admin_approve_rental(rental_id: str, _: User = Depends(current_admin)):
    rental = await db.rentals.find_one({"id": rental_id}, {"_id": 0})
    if not rental:
        raise HTTPException(status_code=404, detail="Rental not found")
    if rental.get("status") == "Paid":
        return rental
    await db.rentals.update_one({"id": rental_id}, {"$set": {"status": "Approved"}})
    return await db.rentals.find_one({"id": rental_id}, {"_id": 0})


@api_router.get("/admin/payments")
async def admin_list_payments(_: User = Depends(current_admin), status: Optional[str] = Query(None)):
    q = {}
    if status:
        q["payment_status"] = status
    return await db.payments.find(q, {"_id": 0}).sort("created_at", -1).to_list(1000)


# ---------------------------------------------------------------------------
# Wire up
# ---------------------------------------------------------------------------
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
