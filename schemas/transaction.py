from pydantic import BaseModel, Field, validator
from datetime import date, datetime
from typing import Optional, Literal, Union

class TransactionBase(BaseModel):
    type: Literal["income", "expense"]  # Only allow these specific values
    amount: float = Field(gt=0)
    description: Optional[str] = None
    category: str
    tx_date: date

    # Add a validator to ensure type is lowercase
    @validator('type')
    def type_must_be_lowercase(cls, v):
        if v is None:
            return v
        return v.lower()

class TransactionCreate(TransactionBase):
    pass

class TransactionUpdate(BaseModel):
    type: Optional[Literal["income", "expense"]] = None
    amount: Optional[float] = Field(default=None, gt=0)
    description: Optional[str] = None
    category: Optional[str] = None
    tx_date: Optional[date] = None
    
    # Add a validator to ensure type is lowercase if provided
    @validator('type')
    def type_must_be_lowercase(cls, v):
        if v is None:
            return v
        return v.lower()

class Transaction(BaseModel):
    tx_id: int
    type: Literal["income", "expense"]  
    amount: float
    description: Optional[str] = None
    category: str
    tx_date: date
    created_at: datetime
    
    class Config:
        orm_mode = True
        
    # Add validator to ensure type is lowercase
    @validator('type')
    def type_must_be_lowercase(cls, v):
        if v is None:
            return v
        return v.lower()