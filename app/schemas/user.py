from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime

# Request Schemas
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    gender: Optional[str] = None  # 'male' | 'female' | 'other'

    @validator('username')
    def username_alphanumeric(cls, v):
        assert v.replace('_', '').replace('-', '').isalnum(), 'Username must be alphanumeric (with _ or - allowed)'
        return v

    @validator('gender')
    def gender_valid(cls, v):
        if v is not None and v not in ('male', 'female', 'other'):
            raise ValueError("gender must be 'male', 'female', or 'other'")
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    display_name: Optional[str] = Field(None, max_length=100)
    gender: Optional[str] = None
    avatar_seed: Optional[str] = Field(None, max_length=100)
    save_conversations: Optional[bool] = None

    @validator('gender')
    def gender_valid(cls, v):
        if v is not None and v not in ('male', 'female', 'other'):
            raise ValueError("gender must be 'male', 'female', or 'other'")
        return v

class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)

# Response Schemas
class RoleResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]

    class Config:
        from_attributes = True

class PermissionResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]

    class Config:
        from_attributes = True

class RoleDetailResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    permissions: List[PermissionResponse] = []

    class Config:
        from_attributes = True

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    display_name: Optional[str]
    gender: Optional[str]
    avatar_seed: Optional[str]
    save_conversations: bool
    is_active: bool
    created_at: datetime
    roles: List[RoleDetailResponse] = []

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse

class TokenData(BaseModel):
    user_id: Optional[int] = None

class GoogleLoginRequest(BaseModel):
    credential: str
