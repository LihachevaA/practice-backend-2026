from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from . import models, schemas, auth, database
from .auth import get_current_user

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Booking API")

@app.get("/")
def root():
    return {"message": "API is working!"}

@app.post("/register", response_model=schemas.UserOut)
def register(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_pass = auth.hash_password(user.password)
    role = "admin" if db.query(models.User).count() == 0 else "user"
    new_user = models.User(email=user.email, hashed_password=hashed_pass, role=role)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/login", response_model=schemas.Token)
def login(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if not db_user or not auth.verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    access_token = auth.create_access_token(data={"sub": db_user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/resources", response_model=List[schemas.Resource])
def get_resources(db: Session = Depends(database.get_db)):
    return db.query(models.Resource).all()

@app.post("/bookings", response_model=schemas.BookingOut)
def create_booking(booking: schemas.BookingCreate, db: Session = Depends(database.get_db), current_user_email: str = Depends(get_current_user)):
    user = db.query(models.User).filter(models.User.email == current_user_email).first()

    overlap = db.query(models.Booking).filter(
        models.Booking.resource_id == booking.resource_id,
        models.Booking.start_time < booking.end_time,
        models.Booking.end_time > booking.start_time
    ).first()
    
    if overlap:
        raise HTTPException(status_code=400, detail="Time slot already booked")
        
    new_booking = models.Booking(**booking.dict(), user_id=user.id)
    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)
    return new_booking