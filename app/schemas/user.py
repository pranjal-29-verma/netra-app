from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime

# Request Schemas
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)

    @validator('username')
    def username_alphanumeric(cls, v):
        assert v.replace('_', '').replace('-', '').isalnum(), 'Username must be alphanumeric (with _ or - allowed)'
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

# Response Schemas
class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    display_name: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse

class TokenData(BaseModel):
    user_id: Optional[int] = None