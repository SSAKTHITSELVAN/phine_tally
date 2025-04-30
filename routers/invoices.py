from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc
from typing import List, Dict, Any
from database import models
from schemas import invoice as schemas
from utility import get_db
import datetime
from sqlalchemy.orm import joinedload, selectinload

router = APIRouter(
    prefix="/invoices",
    tags=["invoices"]
)

async def generate_unique_invoice_number(db: AsyncSession):
    """Generate a unique invoice number based on the current year and the max existing number"""
    current_year = datetime.datetime.now().year
    
    # Query to find the highest invoice number for the current year
    query = select(models.Invoice.invoice_number).filter(
        models.Invoice.invoice_number.like(f"INV-{current_year}-%")
    ).order_by(desc(models.Invoice.invoice_number))
    
    result = await db.execute(query)
    highest_invoice = result.scalars().first()
    
    if not highest_invoice:
        # No invoices for this year yet
        return f"INV-{current_year}-001"
    
    try:
        # Extract the sequence number and increment it
        # Format: "INV-YYYY-NNN"
        prefix = f"INV-{current_year}-"
        sequence_str = highest_invoice[len(prefix):]
        sequence_number = int(sequence_str) + 1
        return f"{prefix}{sequence_number:03d}"
    except (ValueError, IndexError):
        # If we can't parse the number for some reason, use timestamp as fallback
        timestamp = int(datetime.datetime.now().timestamp())
        return f"INV-{current_year}-{timestamp}"

@router.post("/")
async def create_invoice(invoice: schemas.InvoiceCreate, db: AsyncSession = Depends(get_db)):
    """Create a new invoice with items"""
    
    # Generate a unique invoice number
    invoice_number = await generate_unique_invoice_number(db)
    
    # Calculate total amount from items
    total_amount = sum(item.subtotal for item in invoice.items) if invoice.items else 0
    
    # Create invoice
    db_invoice = models.Invoice(
        invoice_number=invoice_number,
        customer_id=invoice.customer_id,
        issue_date=invoice.issue_date,
        due_date=invoice.due_date,
        status=invoice.status,
        total_amount=total_amount,
        notes=invoice.notes
    )
    db.add(db_invoice)
    await db.flush()  # Get invoice_id without committing
    
    # Create invoice items
    for item in invoice.items:
        db_item = models.InvoiceItem(
            invoice_id=db_invoice.invoice_id,
            product_id=item.product_id,
            quantity=item.quantity,
            unit_price=item.unit_price,
            tax_amount=item.tax_amount,
            subtotal=item.subtotal
        )
        db.add(db_item)
    
    await db.commit()
    
    # Convert the DB model to a dictionary for direct response
    result = {
        "invoice_id": db_invoice.invoice_id,
        "invoice_number": db_invoice.invoice_number,
        "customer_id": db_invoice.customer_id,
        "issue_date": db_invoice.issue_date,
        "due_date": db_invoice.due_date,
        "status": db_invoice.status,
        "total_amount": db_invoice.total_amount,
        "notes": db_invoice.notes,
        "created_at": db_invoice.created_at,
        "items": []
    }
    
    # Add items if they exist
    if hasattr(db_invoice, "items") and db_invoice.items:
        for item in db_invoice.items:
            result["items"].append({
                "item_id": item.item_id,
                "invoice_id": item.invoice_id,
                "product_id": item.product_id,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "tax_amount": item.tax_amount,
                "subtotal": item.subtotal
            })
    
    return result

@router.get("/")
async def read_invoices(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """Get all invoices"""
    # Modified query to eagerly load items
    query = select(models.Invoice).options(selectinload(models.Invoice.items)).offset(skip).limit(limit)
    result = await db.execute(query)
    invoices = result.scalars().all()
    
    # Convert to dictionary list for direct response
    response = []
    for invoice in invoices:
        inv_dict = {
            "invoice_id": invoice.invoice_id,
            "invoice_number": invoice.invoice_number,
            "customer_id": invoice.customer_id,
            "issue_date": invoice.issue_date,
            "due_date": invoice.due_date,
            "status": invoice.status,
            "total_amount": invoice.total_amount,
            "notes": invoice.notes,
            "created_at": invoice.created_at,
            "items": []
        }
        
        # Add items
        if hasattr(invoice, "items") and invoice.items:
            for item in invoice.items:
                inv_dict["items"].append({
                    "item_id": item.item_id,
                    "invoice_id": item.invoice_id,
                    "product_id": item.product_id,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "tax_amount": item.tax_amount,
                    "subtotal": item.subtotal
                })
        
        response.append(inv_dict)
    
    return response

@router.get("/{invoice_id}")
async def read_invoice(invoice_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific invoice by ID"""
    query = select(models.Invoice).options(selectinload(models.Invoice.items)).filter(models.Invoice.invoice_id == invoice_id)
    result = await db.execute(query)
    invoice = result.scalars().first()
    
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Convert to dictionary for direct response
    response = {
        "invoice_id": invoice.invoice_id,
        "invoice_number": invoice.invoice_number,
        "customer_id": invoice.customer_id,
        "issue_date": invoice.issue_date,
        "due_date": invoice.due_date,
        "status": invoice.status,
        "total_amount": invoice.total_amount,
        "notes": invoice.notes,
        "created_at": invoice.created_at,
        "items": []
    }
    
    # Add items
    if hasattr(invoice, "items") and invoice.items:
        for item in invoice.items:
            response["items"].append({
                "item_id": item.item_id,
                "invoice_id": item.invoice_id,
                "product_id": item.product_id,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "tax_amount": item.tax_amount,
                "subtotal": item.subtotal
            })
    
    return response

@router.put("/{invoice_id}")
async def update_invoice(invoice_id: int, invoice_update: schemas.InvoiceUpdate, db: AsyncSession = Depends(get_db)):
    """Update an invoice"""
    result = await db.execute(select(models.Invoice).filter(models.Invoice.invoice_id == invoice_id))
    db_invoice = result.scalars().first()
    if db_invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Update fields that are not None
    update_data = invoice_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            setattr(db_invoice, key, value)
    
    await db.commit()
    
    # Return updated invoice as dictionary
    response = {
        "invoice_id": db_invoice.invoice_id,
        "invoice_number": db_invoice.invoice_number,
        "customer_id": db_invoice.customer_id,
        "issue_date": db_invoice.issue_date,
        "due_date": db_invoice.due_date,
        "status": db_invoice.status,
        "total_amount": db_invoice.total_amount,
        "notes": db_invoice.notes,
        "created_at": db_invoice.created_at,
        "items": []  # We'll need to load items separately
    }
    
    # Query to get items
    items_query = select(models.InvoiceItem).filter(models.InvoiceItem.invoice_id == invoice_id)
    items_result = await db.execute(items_query)
    items = items_result.scalars().all()
    
    for item in items:
        response["items"].append({
            "item_id": item.item_id,
            "invoice_id": item.invoice_id,
            "product_id": item.product_id,
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "tax_amount": item.tax_amount,
            "subtotal": item.subtotal
        })
    
    return response

@router.delete("/{invoice_id}")
async def delete_invoice(invoice_id: int, db: AsyncSession = Depends(get_db)):
    """Delete an invoice"""
    result = await db.execute(select(models.Invoice).filter(models.Invoice.invoice_id == invoice_id))
    db_invoice = result.scalars().first()
    if db_invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    await db.delete(db_invoice)
    await db.commit()
    return {"message": "Invoice deleted successfully"}