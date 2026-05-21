from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from app.models.user import User, UserToken
from app.schemas.user import UserRegister, UserLogin
from app.core.security import get_password_hash, verify_password
from app.core.config import settings
from datetime import datetime

class AuthService:
    @staticmethod
    def register_user(db: Session, user_data: UserRegister) -> User:
        """Register a new user."""
        # Check if email already exists
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Check if username already exists
        existing_username = db.query(User).filter(User.username == user_data.username).first()
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        
        # Create new user
        hashed_password = get_password_hash(user_data.password)
        new_user = User(
            username=user_data.username,
            email=user_data.email,
            password_hash=hashed_password,
            display_name=user_data.username
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Create token quota for user
        user_token = UserToken(user_id=new_user.id, daily_quota=settings.DEFAULT_DAILY_TOKEN_QUOTA)
        db.add(user_token)
        db.commit()

        return new_user
    
    @staticmethod
    def authenticate_user(db: Session, user_data: UserLogin) -> User:
        """Authenticate user with email and password."""
        user = db.query(User).filter(User.email == user_data.email).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        if not user.password_hash:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Please login with Google"
            )
        
        if not verify_password(user_data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive"
            )
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
        
        return user
    
    @staticmethod
    def google_login_user(db: Session, credential: str) -> User:
        """Verify Google ID token and find or create the user."""
        try:
            id_info = id_token.verify_oauth2_token(
                credential,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID,
            )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Google credential",
            )

        google_id = id_info["sub"]
        email = id_info["email"]
        display_name = id_info.get("name", "")
        username_base = email.split("@")[0].replace(".", "_").replace("-", "_")

        # Find by google_id first, then fall back to email
        user = db.query(User).filter(User.google_id == google_id).first()
        if not user:
            user = db.query(User).filter(User.email == email).first()

        if user:
            # Link google_id if this email exists without it
            if not user.google_id:
                user.google_id = google_id
            user.last_login = datetime.utcnow()
            db.commit()
            db.refresh(user)
            return user

        # New Google user — generate a unique username
        username = username_base
        counter = 1
        while db.query(User).filter(User.username == username).first():
            username = f"{username_base}{counter}"
            counter += 1

        new_user = User(
            username=username,
            email=email,
            google_id=google_id,
            display_name=display_name,
            last_login=datetime.utcnow(),
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        user_token = UserToken(user_id=new_user.id, daily_quota=settings.DEFAULT_DAILY_TOKEN_QUOTA)
        db.add(user_token)
        db.commit()

        return new_user

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> User:
        """Get user by ID."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return user
