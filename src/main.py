from fastapi import FastAPI
from .database import engine, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Booking API")

@app.get("/")
def read_root():
    return {"message": "Booking API is running"}