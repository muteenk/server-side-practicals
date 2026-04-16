from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.db import Base, engine

from src.idempotence import routes as idempotence_routes

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

# Test Route
@app.get("/")
def root():
    return {"message": "API running"}