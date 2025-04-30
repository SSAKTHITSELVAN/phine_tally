from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from utility import get_db

from database.models import Customer as CustomerModel
from schemas.customer import CustomerCreate, Customer, CustomerUpdate

router = APIRouter(
    prefix="/customers",
    tags=["customers"]
)

@router.post("/", response_model=Customer, status_code=status.HTTP_201_CREATED)
async def create_customer(
    customer: CustomerCreate,
    db: AsyncSession = Depends(get_db)
):
    db_customer = CustomerModel(**customer.dict())
    db.add(db_customer)
    await db.commit()
    await db.refresh(db_customer)
    return db_customer

@router.get("/", response_model=List[Customer])
async def read_customers(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(CustomerModel).offset(skip).limit(limit))
    customers = result.scalars().all()
    return customers

@router.get("/{customer_id}", response_model=Customer)
async def read_customer(
    customer_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(CustomerModel).filter(CustomerModel.customer_id == customer_id))
    customer = result.scalars().first()
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer

@router.put("/{customer_id}", response_model=Customer)
async def update_customer(
    customer_id: int,
    customer: CustomerUpdate,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(CustomerModel).filter(CustomerModel.customer_id == customer_id))
    db_customer = result.scalars().first()
    if db_customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    update_data = customer.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_customer, key, value)

    await db.commit()
    await db.refresh(db_customer)
    return db_customer

@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    customer_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(CustomerModel).filter(CustomerModel.customer_id == customer_id))
    customer = result.scalars().first()
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    await db.delete(customer)
    await db.commit()
    return None
