from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date, DateTime, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from config import Base

# Enums
class TransactionType(str, enum.Enum):
    income = "income"
    expense = "expense"

class InvoiceStatus(str, enum.Enum):
    draft = "draft"
    sent = "sent"
    paid = "paid"
    overdue = "overdue"

class Customer(Base):
    __tablename__ = "customers"
    
    customer_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True, nullable=True)
    phone = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    invoices = relationship("Invoice", back_populates="customer")

class Product(Base):
    __tablename__ = "products"
    
    product_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text, nullable=True)
    unit_price = Column(Float)
    tax_rate = Column(Float, default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    invoice_items = relationship("InvoiceItem", back_populates="product")

class Transaction(Base):
    __tablename__ = "transactions"
    
    tx_id = Column(Integer, primary_key=True, index=True)
    type = Column(Enum(TransactionType))
    amount = Column(Float)
    description = Column(Text, nullable=True)
    category = Column(String)
    tx_date = Column(Date)
    created_at = Column(DateTime, default=func.now())


class Invoice(Base):
    __tablename__ = "invoices"
    
    invoice_id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String, unique=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.customer_id"), nullable=False)
    issue_date = Column(Date)
    due_date = Column(Date)
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.draft)
    total_amount = Column(Float)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    
    customer = relationship("Customer", back_populates="invoices")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan", lazy="selectin")

class InvoiceItem(Base):
    __tablename__ = "invoice_items"
    
    item_id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.invoice_id", ondelete="CASCADE"))
    product_id = Column(Integer, ForeignKey("products.product_id"))
    quantity = Column(Float)
    unit_price = Column(Float)
    tax_amount = Column(Float)
    subtotal = Column(Float)
    
    invoice = relationship("Invoice", back_populates="items")
    product = relationship("Product", back_populates="invoice_items")