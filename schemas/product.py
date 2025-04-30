from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

# Product schemas
class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    unit_price: float = Field(gt=0)
    tax_rate: float = Field(ge=0, default=0)

class ProductCreate(ProductBase):
    pass

class ProductUpdate(ProductBase):
    name: Optional[str] = None
    unit_price: Optional[float] = None

class Product(ProductBase):
    product_id: int
    created_at: datetime
    
    class Config:
        orm_mode = True