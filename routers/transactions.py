from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from database import models
from schemas import transaction as schemas
from utility import get_db
from datetime import date, datetime

router = APIRouter(
    prefix="/transactions",
    tags=["transactions"]
)

@router.post("/", response_model=schemas.Transaction)
async def create_transaction(transaction: schemas.TransactionCreate, db: AsyncSession = Depends(get_db)):
    """Create a new transaction"""
    # Convert type to lowercase and validate it matches allowed enum values
    transaction_type = transaction.type.lower()
    
    # Check if the transaction type is valid
    valid_types = [t.value for t in models.TransactionType]
    if transaction_type not in valid_types:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid transaction type. Must be one of: {', '.join(valid_types)}"
        )
    
    # Ensure required fields are present
    if not transaction.category:
        raise HTTPException(status_code=400, detail="Category is required")
    
    if not transaction.amount or transaction.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than 0")
        
    if not transaction.tx_date:
        transaction_date = date.today()
    else:
        transaction_date = transaction.tx_date
    
    db_transaction = models.Transaction(
        type=transaction_type,
        amount=transaction.amount,
        description=transaction.description,
        category=transaction.category,
        tx_date=transaction_date
    )
    db.add(db_transaction)
    await db.commit()
    await db.refresh(db_transaction)
    return db_transaction

@router.get("/", response_model=List[schemas.Transaction])
async def read_transactions(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """Get all transactions"""
    result = await db.execute(select(models.Transaction).offset(skip).limit(limit))
    transactions = result.scalars().all()
    
    # Filter out any invalid transactions
    valid_transactions = []
    for tx in transactions:
        # Skip transactions with missing required fields
        if (tx.type is None or tx.amount is None or 
            tx.category is None or tx.tx_date is None or 
            tx.created_at is None):
            continue
        valid_transactions.append(tx)
    
    return valid_transactions

@router.get("/{tx_id}", response_model=schemas.Transaction)
async def read_transaction(tx_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific transaction by ID"""
    result = await db.execute(select(models.Transaction).filter(models.Transaction.tx_id == tx_id))
    transaction = result.scalars().first()
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Validate transaction has all required fields
    if (transaction.type is None or transaction.amount is None or 
        transaction.category is None or transaction.tx_date is None or 
        transaction.created_at is None):
        raise HTTPException(status_code=500, detail="Transaction data is incomplete")
    
    return transaction

@router.put("/{tx_id}", response_model=schemas.Transaction)
async def update_transaction(tx_id: int, transaction: schemas.TransactionUpdate, db: AsyncSession = Depends(get_db)):
    """Update a transaction"""
    result = await db.execute(select(models.Transaction).filter(models.Transaction.tx_id == tx_id))
    db_transaction = result.scalars().first()
    if db_transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Create a dictionary of update data
    update_data = transaction.dict(exclude_unset=True)
    
    # Validate and convert type if it exists in the update data
    valid_types = [t.value for t in models.TransactionType]
    if "type" in update_data and update_data["type"]:
        transaction_type = update_data["type"].lower()
        if transaction_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid transaction type. Must be one of: {', '.join(valid_types)}"
            )
        update_data["type"] = transaction_type
    
    # Apply updates to the database object
    for key, value in update_data.items():
        setattr(db_transaction, key, value)
    
    # Ensure the transaction still has valid data after update
    if not db_transaction.type or not db_transaction.amount or not db_transaction.category or not db_transaction.tx_date:
        raise HTTPException(status_code=400, detail="Cannot update transaction with missing required fields")
    
    await db.commit()
    await db.refresh(db_transaction)
    return db_transaction

@router.delete("/{tx_id}")
async def delete_transaction(tx_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a transaction"""
    result = await db.execute(select(models.Transaction).filter(models.Transaction.tx_id == tx_id))
    db_transaction = result.scalars().first()
    if db_transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    await db.delete(db_transaction)
    await db.commit()
    return {"message": "Transaction deleted successfully"}