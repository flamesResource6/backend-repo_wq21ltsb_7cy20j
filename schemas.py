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

from pydantic import BaseModel, Field, HttpUrl
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
    posted_at: Optional[datetime] = Field(None, description="Original post datetime if known")

# Keeping examples for reference (not used by app)
class User(BaseModel):
    name: str
    email: str
    address: str
    age: Optional[int] = None
    is_active: bool = True

class Product(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    category: str
    in_stock: bool = True
