from fastapi import FastAPI, APIRouter, HTTPException, Query
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
import razorpay
from datetime import datetime, timezone


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]
razorpay_client = razorpay.Client(auth=(os.environ['RAZORPAY_KEY_ID'], os.environ['RAZORPAY_KEY_SECRET']))

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")  # Ignore MongoDB's _id field
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str

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

class RentalCreate(BaseModel):
    tool_id: str
    renter_name: str = "Demo Farmer"
    duration: int = 1
    unit: str = "day"

class Rental(BaseModel):
    id: str
    tool_id: str
    tool_name: str
    renter_name: str
    duration: int
    unit: str
    total: float
    status: str
    requested_at: str
    payment_status: str = "unpaid"
    razorpay_order_id: Optional[str] = None

class PaymentVerify(BaseModel):
    rental_id: str
    razorpay_payment_id: str
    razorpay_order_id: str
    razorpay_signature: str

SEED_TOOLS = [
    {"id":"tool-001","name":"Compact Field Tractor","category":"Tractors","description":"Reliable 45 HP tractor for ploughing, hauling and everyday field work.","location":"Nashik, Maharashtra","owner":"Green Valley Co-op","hourly_rate":850,"daily_rate":5800,"available":True,"image_url":"https://images.unsplash.com/photo-1606739211185-2c846d734a6d?auto=format&fit=crop&w=900&q=80","rating":4.9},
    {"id":"tool-002","name":"Heavy Duty Harvester","category":"Harvesting","description":"High-capacity harvester that keeps grain collection moving during peak season.","location":"Pune, Maharashtra","owner":"Kisan Equipment House","hourly_rate":1200,"daily_rate":8200,"available":True,"image_url":"https://images.unsplash.com/photo-1614977645968-6db1d7798ac7?auto=format&fit=crop&w=900&q=80","rating":4.8},
    {"id":"tool-003","name":"Rotary Power Tiller","category":"Tillage","description":"Easy-to-handle tiller for seedbed preparation, weeding and small plots.","location":"Satara, Maharashtra","owner":"Sahyadri Tools","hourly_rate":420,"daily_rate":2900,"available":True,"image_url":"https://images.unsplash.com/photo-1602446692855-6d096499f69b?auto=format&fit=crop&w=900&q=80","rating":4.7},
    {"id":"tool-004","name":"Precision Seed Drill","category":"Planting","description":"Consistent row spacing and seed depth for faster, more uniform planting.","location":"Kolhapur, Maharashtra","owner":"Harvest First Rentals","hourly_rate":650,"daily_rate":4500,"available":False,"image_url":"https://images.unsplash.com/photo-1592982537447-7440770cbfc9?auto=format&fit=crop&w=900&q=80","rating":4.6},
]

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "AgriRent Pro API"}

@api_router.get("/tools", response_model=List[Tool])
async def get_tools(search: Optional[str] = Query(None), category: Optional[str] = Query(None), available: Optional[bool] = Query(None)):
    if await db.tools.count_documents({}) == 0:
        await db.tools.insert_many(SEED_TOOLS)
    query = {}
    if search:
        query["$or"] = [{"name": {"$regex": search, "$options": "i"}}, {"category": {"$regex": search, "$options": "i"}}, {"location": {"$regex": search, "$options": "i"}}]
    if category and category != "All tools": query["category"] = category
    if available is not None: query["available"] = available
    docs = await db.tools.find(query, {"_id": 0}).to_list(100)
    return docs

@api_router.get("/tools/{tool_id}", response_model=Tool)
async def get_tool(tool_id: str):
    tool = await db.tools.find_one({"id": tool_id}, {"_id": 0})
    if not tool: raise HTTPException(status_code=404, detail="Tool not found")
    return tool

@api_router.get("/rentals", response_model=List[Rental])
async def get_rentals():
    return await db.rentals.find({}, {"_id": 0}).sort("requested_at", -1).to_list(100)

@api_router.post("/rentals", response_model=Rental)
async def create_rental(input: RentalCreate):
    tool = await db.tools.find_one({"id": input.tool_id}, {"_id": 0})
    if not tool: raise HTTPException(status_code=404, detail="Tool not found")
    if not tool["available"]: raise HTTPException(status_code=400, detail="Tool is currently unavailable")
    if input.duration < 1 or input.unit not in ["hour", "day"]: raise HTTPException(status_code=400, detail="Choose a valid rental duration")
    total = input.duration * (tool["hourly_rate"] if input.unit == "hour" else tool["daily_rate"])
    rental = Rental(id=str(uuid.uuid4()), tool_id=tool["id"], tool_name=tool["name"], renter_name=input.renter_name, duration=input.duration, unit=input.unit, total=total, status="Requested", requested_at=datetime.now(timezone.utc).isoformat())
    await db.rentals.insert_one(rental.model_dump())
    return rental

@api_router.patch("/rentals/{rental_id}/approve", response_model=Rental)
async def approve_rental(rental_id: str):
    rental = await db.rentals.find_one({"id": rental_id}, {"_id": 0})
    if not rental: raise HTTPException(status_code=404, detail="Rental not found")
    if rental.get("status") == "Paid": return rental
    await db.rentals.update_one({"id": rental_id}, {"$set": {"status": "Approved"}})
    rental["status"] = "Approved"
    return rental

@api_router.post("/payments/order")
async def create_payment_order(rental_id: str):
    rental = await db.rentals.find_one({"id": rental_id}, {"_id": 0})
    if not rental: raise HTTPException(status_code=404, detail="Rental not found")
    if rental.get("status") != "Approved": raise HTTPException(status_code=400, detail="Rental must be approved before payment")
    if rental.get("payment_status") == "paid": raise HTTPException(status_code=400, detail="Rental is already paid")
    order = razorpay_client.order.create({"amount": int(round(rental["total"] * 100)), "currency": "INR", "receipt": f"rent_{rental_id[:30]}", "payment_capture": 1})
    await db.rentals.update_one({"id": rental_id}, {"$set": {"razorpay_order_id": order["id"], "payment_status": "created"}})
    return {"id": order["id"], "amount": order["amount"], "currency": order["currency"], "key_id": os.environ["RAZORPAY_KEY_ID"]}

@api_router.post("/payments/verify")
async def verify_payment(input: PaymentVerify):
    rental = await db.rentals.find_one({"id": input.rental_id}, {"_id": 0})
    if not rental: raise HTTPException(status_code=404, detail="Rental not found")
    if rental.get("razorpay_order_id") != input.razorpay_order_id: raise HTTPException(status_code=400, detail="Payment order does not match rental")
    try:
        razorpay_client.utility.verify_payment_signature({"razorpay_order_id": input.razorpay_order_id, "razorpay_payment_id": input.razorpay_payment_id, "razorpay_signature": input.razorpay_signature})
    except Exception:
        raise HTTPException(status_code=400, detail="Payment signature verification failed")
    await db.rentals.update_one({"id": input.rental_id}, {"$set": {"status": "Paid", "payment_status": "paid"}})
    return {"status": "paid", "rental_id": input.rental_id}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.model_dump()
    status_obj = StatusCheck(**status_dict)
    
    # Convert to dict and serialize datetime to ISO string for MongoDB
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    
    _ = await db.status_checks.insert_one(doc)
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    # Exclude MongoDB's _id field from the query results
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    
    # Convert ISO string timestamps back to datetime objects
    for check in status_checks:
        if isinstance(check['timestamp'], str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    
    return status_checks

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()