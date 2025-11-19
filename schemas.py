"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field, HttpUrl, EmailStr
from typing import Optional, List, Literal
from datetime import datetime

# SaaS: Real estate listing schema
class Listing(BaseModel):
    """
    Normalized real estate listing across sources
    Collection name: "listing"
    """
    title: str = Field(..., description="Listing title")
    description: Optional[str] = Field(None, description="Listing description")
    price: Optional[float] = Field(None, ge=0, description="Price numeric value")
    currency: Optional[str] = Field(None, description="Currency code, e.g., TND, EUR")
    city: Optional[str] = Field(None, description="City or region in Tunisia")
    area: Optional[str] = Field(None, description="Neighborhood or area")
    bedrooms: Optional[int] = Field(None, ge=0, description="Number of bedrooms")
    bathrooms: Optional[int] = Field(None, ge=0, description="Number of bathrooms")
    surface_m2: Optional[float] = Field(None, ge=0, description="Surface in m²")
    deal_type: Optional[Literal['rent', 'sale']] = Field(None, description="rent or sale")
    property_type: Optional[Literal['apartment', 'house', 'land', 'villa', 'studio', 'office', 'other']] = Field('other', description="Type of property")
    url: Optional[HttpUrl] = Field(None, description="Original listing URL")
    images: List[HttpUrl] | None = Field(default=None, description="Image URLs if available")
    source: Literal['facebook', 'tayara', 'tunisie-annonces', 'other'] = Field(..., description="Source platform")
    source_id: Optional[str] = Field(None, description="Source-specific ID if available")
    posted_at: Optional[datetime] = Field(None, description="Original post datetime if known")

    # Moderation & enrichment
    status: Literal['pending', 'approved', 'rejected'] = Field('pending', description="Moderation status")
    dedup_key: Optional[str] = Field(None, description="Hash used to deduplicate")
    lat: Optional[float] = Field(None, ge=-90, le=90)
    lng: Optional[float] = Field(None, ge=-180, le=180)
    geocoded_city: Optional[str] = None
    geocoded_area: Optional[str] = None

# Minimal user model (for future authentication/ownership of saved searches)
class User(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    created_at: Optional[datetime] = None
    is_admin: bool = False

# Saved search subscriptions
class SavedSearch(BaseModel):
    name: str = Field(..., description="Saved search name")
    # association (optional until full auth)
    user_id: Optional[str] = Field(None, description="User ID (stringified ObjectId)")

    # filters
    q: Optional[str] = None
    city: Optional[str] = None
    deal_type: Optional[Literal['rent','sale']] = None
    property_type: Optional[str] = None
    min_price: Optional[float] = Field(None, ge=0)
    max_price: Optional[float] = Field(None, ge=0)
    min_rooms: Optional[int] = Field(None, ge=0)
    max_rooms: Optional[int] = Field(None, ge=0)
    source: Optional[str] = None

    # delivery preferences
    channels: List[Literal['email','telegram']] = Field(default_factory=lambda: ['email'])
    target_email: Optional[EmailStr] = None
    telegram_chat_id: Optional[str] = None

# Alert record when a listing matches and we notify
class Alert(BaseModel):
    saved_search_id: str
    listing_id: str
    channel: Literal['email','telegram']
    sent_at: Optional[datetime] = None
