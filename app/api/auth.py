from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.user import UserRegister, UserLogin, TokenResponse, UserResponse
from app.services.auth_service import AuthService
from app.core.security import create_access_token, create_refresh_token

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user.
    
    - **username**: Unique username (3-50 characters, alphanumeric)
    - **email**: Valid email address
    - **password**: Password (minimum 6 characters)
    """
    user = AuthService.register_user(db, user_data)
    return user

@router.post("/login", response_model=TokenResponse)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """
    Login with email and password.
    
    Returns access token and refresh token.
    """
    user = AuthService.authenticate_user(db, user_data)
    
    # Create tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.from_orm(user)
    )

@router.get("/me", response_model=UserResponse)
def get_current_user(
    db: Session = Depends(get_db),
    # We'll add proper auth dependency in next iteration
):
    """
    Get current authenticated user.
    (Will be protected in next iteration)
    """
    # Placeholder - will implement proper JWT verification next
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Will be implemented in Iteration 3"
    )