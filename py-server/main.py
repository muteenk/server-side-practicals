from fastapi import FastAPI
import db

app = FastAPI()

@app.get("/")
def root():
    return {"message": "API running"}