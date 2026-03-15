from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from typing import List, Optional

from . import models, schemas, auth, database
from .auth import get_current_user

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Booking API - Stage 4")

@app.get("/")
def root():
    return {"message": "API Stage 4 is working!"}

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

@app.get("/resources/search", response_model=List[schemas.ResourceWithRating])
def search_resources(
    start: datetime, 
    end: datetime, 
    capacity: Optional[int] = None,
    db: Session = Depends(database.get_db)
):
    occupied_ids = db.query(models.Booking.resource_id).filter(
        models.Booking.start_time < end,
        models.Booking.end_time > start
    ).all()
    occupied_ids = [r[0] for r in occupied_ids]

    query = db.query(models.Resource).filter(~models.Resource.id.in_(occupied_ids))
    if capacity:
        query = query.filter(models.Resource.capacity >= capacity)
    
    resources = query.all()
    
    for res in resources:
        avg = db.query(func.avg(models.Review.rating)).filter(models.Review.resource_id == res.id).scalar()
        res.average_rating = round(avg, 1) if avg else 0.0
        
    return resources

@app.get("/resources/{resource_id}/schedule", response_model=List[schemas.BookingOut])
def get_resource_schedule(resource_id: int, db: Session = Depends(database.get_db)):
    return db.query(models.Booking).filter(models.Booking.resource_id == resource_id).order_by(models.Booking.start_time).all()

@app.post("/reviews", response_model=schemas.ReviewOut)
def leave_review(
    review: schemas.ReviewCreate, 
    db: Session = Depends(database.get_db),
    current_user_email: str = Depends(get_current_user)
):
    user = db.query(models.User).filter(models.User.email == current_user_email).first()

    completed_booking = db.query(models.Booking).filter(
        models.Booking.user_id == user.id,
        models.Booking.resource_id == review.resource_id,
        models.Booking.end_time < datetime.utcnow()
    ).first()

    if not completed_booking:
        raise HTTPException(status_code=400, detail="You can only review resources you have actually used.")

    new_review = models.Review(**review.dict(), user_id=user.id)
    db.add(new_review)
    db.commit()
    db.refresh(new_review)
    return new_review