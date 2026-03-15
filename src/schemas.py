from pydantic import BaseModel, EmailStr, Field, validator
from datetime import datetime
from typing import Optional, List

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    role: str
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class ResourceBase(BaseModel):
    name: str = Field(..., min_length=2)
    capacity: int = Field(..., gt=0)
    has_whiteboard: bool = False

class ResourceCreate(ResourceBase):
    pass

class Resource(ResourceBase):
    id: int
    class Config:
        from_attributes = True

class BookingBase(BaseModel):
    resource_id: int
    start_time: datetime
    end_time: datetime

    @validator('end_time')
    def end_date_must_be_after_start(cls, v, values):
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError('Время окончания должно быть позже времени начала')
        return v

class BookingCreate(BookingBase):
    pass

class BookingOut(BookingBase):
    id: int
    user_id: int
    resource_id: int
    start_time: datetime
    end_time: datetime
    class Config:
        from_attributes = True

class ReviewCreate(BaseModel):
    resource_id: int
    text: str
    rating: int = Field(..., ge=1, le=5)

class ReviewOut(BaseModel):
    id: int
    text: str
    rating: int
    user_id: int
    class Config:
        from_attributes = True

class ResourceWithRating(Resource):
    average_rating: float = 0.0
    class Config:
        from_attributes = True