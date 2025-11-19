"""
Database Helper Functions

MongoDB helper functions ready to use in your backend code.
Import and use these functions in your API endpoints for database operations.
"""

from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, timezone
import os
from dotenv import load_dotenv
from typing import Union, List, Dict, Any
from pydantic import BaseModel

# Load environment variables from .env file
load_dotenv()

_client = None
db = None

database_url = os.getenv("DATABASE_URL")
database_name = os.getenv("DATABASE_NAME")

if database_url and database_name:
    _client = MongoClient(database_url)
    db = _client[database_name]

# Helper functions for common database operations
def create_document(collection_name: str, data: Union[BaseModel, dict]):
    """Insert a single document with timestamp"""
    if db is None:
        raise Exception("Database not available. Check DATABASE_URL and DATABASE_NAME environment variables.")

    data_dict = data.model_dump() if isinstance(data, BaseModel) else dict(data)

    now = datetime.now(timezone.utc)
    data_dict['created_at'] = data_dict.get('created_at', now)
    data_dict['updated_at'] = now

    result = db[collection_name].insert_one(data_dict)
    return str(result.inserted_id)


def upsert_document(collection_name: str, filter_dict: Dict[str, Any], data: Dict[str, Any]):
    """Upsert a document by filter with timestamps. Returns id and upserted flag."""
    if db is None:
        raise Exception("Database not available. Check env vars.")

    now = datetime.now(timezone.utc)
    data = dict(data)
    data['updated_at'] = now
    set_on_insert = {'created_at': now}

    result = db[collection_name].update_one(filter_dict, {"$set": data, "$setOnInsert": set_on_insert}, upsert=True)

    if result.upserted_id is not None:
        return str(result.upserted_id), True
    # fetch existing id
    existing = db[collection_name].find_one(filter_dict, {"_id": 1})
    return str(existing["_id"]) if existing else None, False


def get_documents(collection_name: str, filter_dict: dict = None, limit: int = None, sort: List = None):
    """Get documents from collection"""
    if db is None:
        raise Exception("Database not available. Check DATABASE_URL and DATABASE_NAME environment variables.")

    cursor = db[collection_name].find(filter_dict or {})
    if sort:
        cursor = cursor.sort(sort)
    if limit:
        cursor = cursor.limit(limit)
    return list(cursor)


def update_by_id(collection_name: str, _id: str, updates: Dict[str, Any]):
    if db is None:
        raise Exception("Database not available.")
    updates = dict(updates)
    updates['updated_at'] = datetime.now(timezone.utc)
    result = db[collection_name].update_one({"_id": ObjectId(_id)}, {"$set": updates})
    return result.modified_count


def aggregate(collection_name: str, pipeline: List[Dict[str, Any]]):
    if db is None:
        raise Exception("Database not available.")
    return list(db[collection_name].aggregate(pipeline))
