import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from database import db, create_document, get_documents
from schemas import Listing

app = FastAPI(title="Tunisia Real Estate Aggregator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CreateListing(BaseModel):
    # Allows internal ingestion via API (webhooks, scrapers)
    listing: Listing

@app.get("/")
def read_root():
    return {"name": "Tunisia Real Estate Aggregator API", "version": 1}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": "❌ Not Set",
        "database_name": "❌ Not Set",
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "❌ Not Set"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"
    return response

@app.post("/api/listings", response_model=dict)
def create_listing(payload: CreateListing):
    try:
        inserted_id = create_document("listing", payload.listing)
        return {"inserted_id": inserted_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/listings", response_model=List[dict])
def list_listings(
    q: Optional[str] = Query(None, description="Search in title/description"),
    city: Optional[str] = Query(None),
    deal_type: Optional[str] = Query(None, regex="^(rent|sale)$"),
    property_type: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    min_rooms: Optional[int] = Query(None, ge=0),
    max_rooms: Optional[int] = Query(None, ge=0),
    source: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200)
):
    try:
        filter_dict = {}
        if city:
            filter_dict["city"] = {"$regex": city, "$options": "i"}
        if deal_type:
            filter_dict["deal_type"] = deal_type
        if property_type:
            filter_dict["property_type"] = property_type
        if source:
            filter_dict["source"] = source
        # Price range
        price_filter = {}
        if min_price is not None:
            price_filter["$gte"] = min_price
        if max_price is not None:
            price_filter["$lte"] = max_price
        if price_filter:
            filter_dict["price"] = price_filter
        # Rooms
        if min_rooms is not None or max_rooms is not None:
            room_filter = {}
            if min_rooms is not None:
                room_filter["$gte"] = min_rooms
            if max_rooms is not None:
                room_filter["$lte"] = max_rooms
            filter_dict["bedrooms"] = room_filter
        # Full-text like search
        if q:
            filter_dict["$or"] = [
                {"title": {"$regex": q, "$options": "i"}},
                {"description": {"$regex": q, "$options": "i"}},
                {"city": {"$regex": q, "$options": "i"}},
            ]

        docs = get_documents("listing", filter_dict, limit)
        # Serialize ObjectId and datetimes if present
        for d in docs:
            if "_id" in d:
                d["id"] = str(d.pop("_id"))
            for key, val in list(d.items()):
                if isinstance(val, datetime):
                    d[key] = val.isoformat()
        return docs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
