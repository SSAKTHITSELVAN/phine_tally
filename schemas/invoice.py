from pydantic import BaseModel, Field, validator
from datetime import date, datetime, timedelta
from typing import Optional, List, Any
from enum import Enum

class InvoiceStatus(str, Enum):
    draft = "draft"
    sent = "sent"
    paid = "paid"
    overdue = "overdue"

class InvoiceItemBase(BaseModel):
    product_id: int = Field(..., description="ID of the product")
    quantity: float = Field(..., description="Quantity of product")
    unit_price: float = Field(..., description="Price per unit")
    tax_amount: float = Field(0, description="Tax amount")
    subtotal: Optional[float] = None

    @validator('subtotal', pre=True, always=True)
    def calculate_subtotal(cls, v, values):
        """Calculate subtotal if not provided"""
        if v is not None:
            return v
        
        quantity = values.get('quantity', 0)
        unit_price = values.get('unit_price', 0)
        tax_amount = values.get('tax_amount', 0)
        
        return round((quantity * unit_price) + tax_amount, 2)

class InvoiceItemCreate(InvoiceItemBase):
    pass

class InvoiceBase(BaseModel):
    customer_id: int = Field(..., description="ID of the customer")
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    status: Optional[InvoiceStatus] = InvoiceStatus.draft
    notes: Optional[str] = None

    @validator('due_date', 'issue_date', pre=True)
    def parse_dates(cls, v):
        """Parse string dates to date objects"""
        if isinstance(v, str):
            try:
                return datetime.strptime(v, "%Y-%m-%d").date()
            except ValueError:
                raise ValueError("Invalid date format. Use YYYY-MM-DD")
        return v
    
    @validator('due_date')
    def validate_due_date(cls, v, values):
        """Validate due date is not before issue date"""
        if v is None:
            # Set default due date to 30 days from now
            return datetime.now().date() + timedelta(days=30)
            
        issue_date = values.get('issue_date')
        if issue_date and isinstance(issue_date, date) and isinstance(v, date):
            if v < issue_date:
                raise ValueError("Due date cannot be before issue date")
                
        return v

class InvoiceCreate(InvoiceBase):
    items: List[InvoiceItemCreate] = []

class InvoiceItem(InvoiceItemBase):
    item_id: int
    invoice_id: int
    
    class Config:
        orm_mode = True
        from_attributes = True

class Invoice(InvoiceBase):
    invoice_id: int
    invoice_number: str
    total_amount: float
    created_at: datetime
    items: List[InvoiceItem] = []
    
    class Config:
        orm_mode = True
        from_attributes = True

class InvoiceUpdate(BaseModel):
    customer_id: Optional[int] = None
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    
    @validator('due_date', 'issue_date', pre=True)
    def parse_dates(cls, v):
        """Parse string dates to date objects"""
        if isinstance(v, str):
            try:
                return datetime.strptime(v, "%Y-%m-%d").date()
            except ValueError:
                raise ValueError("Invalid date format. Use YYYY-MM-DD")
        return v