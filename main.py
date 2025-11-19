import os
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

from database import db, create_document, get_documents, upsert_document, update_by_id, aggregate
from schemas import Listing, SavedSearch, Alert

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
    return {"name": "Tunisia Real Estate Aggregator API", "version": 2}

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

# ---------------------------
# Listings: Create + List
# ---------------------------
@app.post("/api/listings", response_model=dict)
def create_listing(payload: CreateListing):
    try:
        # Create dedup key (url OR title+price+posted_at)
        l = payload.listing.model_dump()
        dedup_key = l.get('url') or f"{l.get('title','')}-{l.get('price','')}-{l.get('posted_at','')}"
        l['dedup_key'] = dedup_key
        # Upsert by dedup_key
        _id, is_new = upsert_document("listing", {"dedup_key": dedup_key}, l)
        return {"id": _id, "created": is_new}
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
        filter_dict: Dict[str, Any] = {"status": {"$ne": "rejected"}}
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

        docs = get_documents("listing", filter_dict, limit, sort=[["posted_at", -1], ["created_at", -1]])
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

# ---------------------------
# Saved Searches & Alerts
# ---------------------------
@app.post("/api/saved-searches", response_model=dict)
def create_saved_search(search: SavedSearch):
    try:
        _id = create_document("savedsearch", search)
        return {"id": _id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/saved-searches", response_model=List[dict])
def list_saved_searches(limit: int = 50):
    try:
        docs = get_documents("savedsearch", {}, limit, sort=[["created_at", -1]])
        for d in docs:
            d["id"] = str(d.pop("_id"))
            if isinstance(d.get("created_at"), datetime):
                d["created_at"] = d["created_at"].isoformat()
        return docs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Minimal endpoint to record an alert sent (hook for future email/telegram integrations)
@app.post("/api/alerts", response_model=dict)
def record_alert(alert: Alert):
    try:
        _id = create_document("alert", alert)
        return {"id": _id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------
# Admin moderation
# ---------------------------
@app.post("/api/listings/{listing_id}/approve", response_model=dict)
def approve_listing(listing_id: str):
    try:
        modified = update_by_id("listing", listing_id, {"status": "approved"})
        return {"updated": modified}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/listings/{listing_id}/reject", response_model=dict)
def reject_listing(listing_id: str):
    try:
        modified = update_by_id("listing", listing_id, {"status": "rejected"})
        return {"updated": modified}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------
# Analytics
# ---------------------------
@app.get("/api/analytics/summary", response_model=dict)
def analytics_summary(city: Optional[str] = None, deal_type: Optional[str] = None, property_type: Optional[str] = None):
    try:
        match: Dict[str, Any] = {"status": {"$ne": "rejected"}}
        if city:
            match["city"] = {"$regex": city, "$options": "i"}
        if deal_type:
            match["deal_type"] = deal_type
        if property_type:
            match["property_type"] = property_type

        pipeline = [
            {"$match": match},
            {"$group": {
                "_id": {
                    "city": "$city",
                    "property_type": "$property_type",
                    "deal_type": "$deal_type"
                },
                "count": {"$sum": 1},
                "median_price": {"$median": "$price"},
                "avg_price": {"$avg": "$price"}
            }},
            {"$sort": {"count": -1}}
        ]
        results = aggregate("listing", pipeline)
        # normalize keys
        for r in results:
            r["city"] = r.pop("_id", {}).get("city")
            r["property_type"] = r.get("property_type") or None
        return {"groups": results}
    except Exception as e:
        # in case $median not supported, fallback simple stats
        try:
            pipeline = [
                {"$match": match},
                {"$group": {
                    "_id": {
                        "city": "$city",
                        "property_type": "$property_type",
                        "deal_type": "$deal_type"
                    },
                    "count": {"$sum": 1},
                    "avg_price": {"$avg": "$price"},
                    "min_price": {"$min": "$price"},
                    "max_price": {"$max": "$price"}
                }},
                {"$sort": {"count": -1}}
            ]
            results = aggregate("listing", pipeline)
            for r in results:
                r["city"] = r.pop("_id", {}).get("city")
            return {"groups": results, "note": "median not available; showing avg/min/max"}
        except Exception as e2:
            raise HTTPException(status_code=500, detail=str(e2))

# ---------------------------
# Ingestion webhook placeholders (scrapers will call these)
# ---------------------------
@app.post("/ingest/{source}")
def ingest_source(source: str, payload: Dict[str, Any] = Body(...)):
    """
    Generic ingestion endpoint for connectors/scrapers.
    Accepts either a single listing or a list of listings under `items`.
    Deduplicates using url or title+price+posted_at.
    """
    if source not in {"facebook", "tayara", "tunisie-annonces", "other"}:
        raise HTTPException(status_code=400, detail="Unsupported source")

    items = payload.get("items") or [payload]
    created, updated = 0, 0
    ids: List[str] = []
    for it in items:
        it = dict(it)
        it['source'] = source
        # build dedup key
        dedup_key = it.get('url') or f"{it.get('title','')}-{it.get('price','')}-{it.get('posted_at','')}"
        it['dedup_key'] = dedup_key
        _id, is_new = upsert_document("listing", {"dedup_key": dedup_key}, it)
        ids.append(_id)
        if is_new:
            created += 1
        else:
            updated += 1
    return {"created": created, "updated": updated, "ids": ids}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
