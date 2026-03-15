from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from . import models, schemas, auth, database

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Booking API - Stage 2")


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
def read_resources(db: Session = Depends(database.get_db)):
    return db.query(models.Resource).all()

@app.post("/resources", response_model=schemas.Resource)
def create_resource(
    resource: schemas.ResourceCreate, 
    db: Session = Depends(database.get_db),
    current_user_email: str = Depends(auth.get_current_user)
):
    user = db.query(models.User).filter(models.User.email == current_user_email).first()
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create resources")
    
    new_res = models.Resource(**resource.dict())
    db.add(new_res)
    db.commit()
    db.refresh(new_res)
    return new_res

@app.delete("/resources/{res_id}", status_code=204)
def delete_resource(
    res_id: int, 
    db: Session = Depends(database.get_db),
    current_user_email: str = Depends(auth.get_current_user)
):
    user = db.query(models.User).filter(models.User.email == current_user_email).first()
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    res = db.query(models.Resource).filter(models.Resource.id == res_id).first()
    if not res:
        raise HTTPException(status_code=404, detail="Not found")
    
    db.delete(res)
    db.commit()
    return None