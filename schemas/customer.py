from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# Customer schemas
class CustomerBase(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(CustomerBase):
    name: Optional[str] = None

class Customer(CustomerBase):
    customer_id: int
    created_at: datetime
    
    class Config:
        orm_mode = True