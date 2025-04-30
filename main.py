from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import engine
from database import models
from routers import customers, products, transactions, invoices

app = FastAPI(
    title="Mini Tally API",
    description="An API to manage Tally-like accounting records.",
    version="1.0.0"
)

# Create tables at startup
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)

# Include routers
app.include_router(customers.router)
app.include_router(products.router)
app.include_router(transactions.router)
app.include_router(invoices.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to Mini Tally API"}

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)