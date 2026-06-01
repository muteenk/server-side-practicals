from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.db import Base, engine

from src.idempotence import routes as idempotence_routes
from src.payment_gateway_strategy import (
    legacy_hardcoded_router,
    router as strategy_payment_router,
    single_gateway_router,
)
from src.retry_mechanisms import router as retry_mechanisms_router


# Config
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
Base.metadata.create_all(bind=engine)

# Routes
app.include_router(idempotence_routes.router, tags=['idempotence'])
app.include_router(strategy_payment_router)
app.include_router(legacy_hardcoded_router)
app.include_router(single_gateway_router)
app.include_router(retry_mechanisms_router)

# Test Route
@app.get("/")
def root():
    return {"message": "API running"}