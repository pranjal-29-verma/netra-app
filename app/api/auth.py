from fastapi import APIRouter, Depends, Request, status, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.config import settings
from app.schemas.user import UserRegister, UserLogin, TokenResponse, UserResponse, GoogleLoginRequest
from app.services.auth_service import AuthService
from app.core.security import create_access_token, create_refresh_token, get_current_user, verify_token
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(lambda: settings.RATE_LIMIT_REGISTER)
def register(request: Request, user_data: UserRegister, db: Session = Depends(get_db)):
    user = AuthService.register_user(db, user_data)
    return user


@router.post("/login", response_model=TokenResponse)
@limiter.limit(lambda: settings.RATE_LIMIT_LOGIN)
def login(request: Request, user_data: UserLogin, db: Session = Depends(get_db)):
    user = AuthService.authenticate_user(db, user_data)
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.from_orm(user)
    )


@router.post("/google", response_model=TokenResponse)
@limiter.limit(lambda: settings.RATE_LIMIT_GOOGLE)
def google_login(request: Request, body: GoogleLoginRequest, db: Session = Depends(get_db)):
    user = AuthService.google_login_user(db, body.credential)
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.from_orm(user),
    )


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit(lambda: settings.RATE_LIMIT_REFRESH)
def refresh(request: Request, body: RefreshRequest, db: Session = Depends(get_db)):
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
    return current_user
