from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from app.core.config import settings
from app.core.database import engine, Base, SessionLocal
from app.core.rate_limit import limiter
from app.api import auth
from app.api import conversations
from app.api import tokens
from app.api import documents
from app.api import chat
from app.api import users
from app.api.admin import router as admin_router
import app.models  # ensure all models are registered for table creation

# Create database tables
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load active LLM config into in-memory cache on startup
    from app.services import llm_config_service
    db = SessionLocal()
    try:
        llm_config_service.reload(db)
    finally:
        db.close()
    yield

# Initialize FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Personal Knowledge Chatbot API",
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter

async def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": f"Too many requests. You have hit the limit of {exc.limit}. Please wait and try again."},
        headers={"Retry-After": "60"},
    )

app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(conversations.router, prefix="/api")
app.include_router(tokens.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(admin_router, prefix="/api")

@app.get("/")
def root():
    return {
        "message": "Netra Chatbot API",
        "version": settings.VERSION,
        "status": "running"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}
