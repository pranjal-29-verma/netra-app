from fastapi import APIRouter, BackgroundTasks, Depends, status, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.user import UserRegister, UserLogin, TokenResponse, UserResponse, GoogleLoginRequest
from app.services.auth_service import AuthService
from app.services import notify_client
from app.core.security import create_access_token, create_refresh_token, get_current_user, verify_token
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


class RefreshRequest(BaseModel):
    refresh_token: str

class ResendVerificationRequest(BaseModel):
    email: EmailStr


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserRegister, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    user = AuthService.register_user(db, user_data)
    if user.verification_token:
        background_tasks.add_task(
            notify_client.send_verification_email,
            user.email, user.username, user.verification_token,
        )
    return user


@router.get("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    AuthService.verify_email(db, token)
    return {"message": "Email verified successfully"}


@router.post("/resend-verification")
def resend_verification(body: ResendVerificationRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    user = AuthService.resend_verification(db, body.email)
    background_tasks.add_task(
        notify_client.send_verification_email,
        user.email, user.username, user.verification_token,
    )
    return {"message": "Verification email sent"}

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

@router.post("/google", response_model=TokenResponse)
def google_login(body: GoogleLoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate with a Google ID token.

    The frontend sends the credential returned by Google OAuth; the backend
    verifies it, finds or creates the user, and returns app JWT tokens.
    """
    user = AuthService.google_login_user(db, body.credential)

    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.from_orm(user),
    )

@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    """Exchange a valid refresh token for a new access + refresh token pair."""
    payload = verify_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    access_token = create_access_token(data={"sub": str(user.id)})
    new_refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        user=UserResponse.from_orm(user),
    )


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return current_user