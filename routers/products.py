from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from utility import get_db


from database.models import Product as ProductModel
from schemas.product import ProductCreate, Product, ProductUpdate

router = APIRouter(
    prefix="/products",
    tags=["products"]
)

@router.post("/", response_model=Product, status_code=status.HTTP_201_CREATED)
async def create_product(
    product: ProductCreate,
    db: AsyncSession = Depends(get_db)
):
    db_product = ProductModel(**product.dict())
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)
    return db_product

@router.get("/", response_model=List[Product])
async def read_products(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(ProductModel).offset(skip).limit(limit))
    products = result.scalars().all()
    return products

@router.get("/{product_id}", response_model=Product)
async def read_product(
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(ProductModel).filter(ProductModel.product_id == product_id))
    product = result.scalars().first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.put("/{product_id}", response_model=Product)
async def update_product(
    product_id: int,
    product: ProductUpdate,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(ProductModel).filter(ProductModel.product_id == product_id))
    db_product = result.scalars().first()
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = product.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_product, key, value)

    await db.commit()
    await db.refresh(db_product)
    return db_product

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(ProductModel).filter(ProductModel.product_id == product_id))
    product = result.scalars().first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    await db.delete(product)
    await db.commit()
    return None
