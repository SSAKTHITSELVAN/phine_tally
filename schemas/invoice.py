from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional, List, Any

class InvoiceItemBase(BaseModel):
    product_id: Optional[Any] = None
    quantity: Optional[float] = 0
    unit_price: Optional[float] = 0
    tax_amount: Optional[float] = 0
    subtotal: Optional[float] = 0

class InvoiceItemCreate(InvoiceItemBase):
    pass

class InvoiceBase(BaseModel):
    customer_id: Optional[Any] = None
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    status: Optional[str] = "draft"
    notes: Optional[str] = None

class InvoiceCreate(InvoiceBase):
    items: List[InvoiceItemCreate] = []

class InvoiceItem(InvoiceItemBase):
    item_id: Optional[int] = None
    invoice_id: Optional[int] = None
    
    class Config:
        orm_mode = True
        from_attributes = True

class Invoice(InvoiceBase):
    invoice_id: Optional[int] = None
    invoice_number: Optional[str] = None
    total_amount: Optional[float] = 0
    created_at: Optional[datetime] = None
    items: Optional[List[InvoiceItem]] = []
    
    class Config:
        orm_mode = True
        from_attributes = True

class InvoiceUpdate(BaseModel):
    customer_id: Optional[Any] = None
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    status: Optional[str] = None
    notes: Optional[str] = None