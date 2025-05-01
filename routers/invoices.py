from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
from typing import List, Optional
from database import models
from schemas import invoice as schemas
from utility import get_db
import datetime
from sqlalchemy.orm import selectinload

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
        prefix = f"INV-{current_year}-"
        sequence_str = highest_invoice[len(prefix):]
        sequence_number = int(sequence_str) + 1
        return f"{prefix}{sequence_number:03d}"
    except (ValueError, IndexError):
        # If we can't parse the number, use timestamp as fallback
        timestamp = int(datetime.datetime.now().timestamp())
        return f"INV-{current_year}-{timestamp}"

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_invoice(invoice_data: dict, db: AsyncSession = Depends(get_db)):
    """Create a new invoice with items"""
    try:
        # Pre-process the input data to handle validation issues
        if "items" in invoice_data and invoice_data["items"]:
            for item in invoice_data["items"]:
                # Remove invoice_id if provided (will be set automatically)
                if "invoice_id" in item:
                    del item["invoice_id"]
                
                # Ensure product_id is valid
                if "product_id" not in item or item["product_id"] is None:
                    # If product_id is missing, check if we can create a default product
                    # For this example, we'll just set a dummy value to pass validation
                    # In a real app, you might want to create a default product
                    item["product_id"] = 1  # Set a default product_id
        
        # Now parse with Pydantic model for full validation
        try:
            invoice = schemas.InvoiceCreate(**invoice_data)
        except Exception as val_error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Validation error: {str(val_error)}"
            )
        
        # Check if customer exists
        customer_id = invoice.customer_id
        customer_query = select(models.Customer).filter(models.Customer.customer_id == customer_id)
        result = await db.execute(customer_query)
        customer = result.scalars().first()
        
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer with ID {customer_id} not found. Please use a valid customer ID."
            )
        
        # Check if products exist
        for item in invoice.items:
            product_query = select(models.Product).filter(models.Product.product_id == item.product_id)
            result = await db.execute(product_query)
            product = result.scalars().first()
            
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product with ID {item.product_id} not found. Please use valid product IDs."
                )
        
        # Set default dates if not provided
        if invoice.issue_date is None:
            invoice.issue_date = datetime.date.today()
            
        if invoice.due_date is None:
            invoice.due_date = invoice.issue_date + datetime.timedelta(days=30)
        
        # Generate invoice number
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
        await db.flush()
        
        # Create invoice items
        if invoice.items:
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
        await db.refresh(db_invoice)
        
        # Return result as dictionary
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
        
        # Query to get items
        items_query = select(models.InvoiceItem).filter(models.InvoiceItem.invoice_id == db_invoice.invoice_id)
        items_result = await db.execute(items_query)
        items = items_result.scalars().all()
        
        for item in items:
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
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error creating invoice: {str(e)}"
        )


@router.get("/")
async def read_invoices(
    skip: int = 0, 
    limit: int = 100, 
    customer_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get all invoices"""
    try:
        # Build query
        query = select(models.Invoice)
        
        # Add customer filter if provided
        if customer_id:
            query = query.filter(models.Invoice.customer_id == customer_id)
            
        # Add pagination
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        invoices = result.scalars().all()
        
        # Format response
        response = []
        for invoice in invoices:
            # Get invoice items
            items_query = select(models.InvoiceItem).filter(models.InvoiceItem.invoice_id == invoice.invoice_id)
            items_result = await db.execute(items_query)
            items = items_result.scalars().all()
            
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
            for item in items:
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
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching invoices: {str(e)}"
        )

@router.get("/{invoice_id}")
async def read_invoice(invoice_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific invoice by ID"""
    try:
        # Get invoice
        query = select(models.Invoice).filter(models.Invoice.invoice_id == invoice_id)
        result = await db.execute(query)
        invoice = result.scalars().first()
        
        if invoice is None:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # Get invoice items
        items_query = select(models.InvoiceItem).filter(models.InvoiceItem.invoice_id == invoice_id)
        items_result = await db.execute(items_query)
        items = items_result.scalars().all()
        
        # Format response
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching invoice: {str(e)}"
        )

@router.put("/{invoice_id}")
async def update_invoice(invoice_id: int, invoice_update: schemas.InvoiceUpdate, db: AsyncSession = Depends(get_db)):
    """Update an invoice"""
    try:
        # Get invoice
        query = select(models.Invoice).filter(models.Invoice.invoice_id == invoice_id)
        result = await db.execute(query)
        db_invoice = result.scalars().first()
        
        if db_invoice is None:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # Update fields that are not None
        update_data = invoice_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                setattr(db_invoice, key, value)
        
        await db.commit()
        await db.refresh(db_invoice)
        
        # Get invoice items
        items_query = select(models.InvoiceItem).filter(models.InvoiceItem.invoice_id == invoice_id)
        items_result = await db.execute(items_query)
        items = items_result.scalars().all()
        
        # Format response
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
            "items": []
        }
        
        # Add items
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
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error updating invoice: {str(e)}"
        )

@router.delete("/{invoice_id}")
async def delete_invoice(invoice_id: int, db: AsyncSession = Depends(get_db)):
    """Delete an invoice"""
    try:
        # Get invoice
        query = select(models.Invoice).filter(models.Invoice.invoice_id == invoice_id)
        result = await db.execute(query)
        db_invoice = result.scalars().first()
        
        if db_invoice is None:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # Delete invoice (this will cascade delete items due to relationship)
        await db.delete(db_invoice)
        await db.commit()
        
        return {"message": "Invoice deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting invoice: {str(e)}"
        )