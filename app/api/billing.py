from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.billing import Plan, TokenPack
from app.services import billing_service

router = APIRouter(prefix="/billing", tags=["Billing"])


class CreateOrderRequest(BaseModel):
    item_type: str   # 'plan' | 'pack'
    item_id: int


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


@router.get("/plans")
def list_plans(db: Session = Depends(get_db)):
    return db.query(Plan).filter(Plan.is_active == True).order_by(Plan.price_inr).all()


@router.get("/packs")
def list_packs(db: Session = Depends(get_db)):
    return db.query(TokenPack).filter(TokenPack.is_active == True).order_by(TokenPack.price_inr).all()


@router.post("/create-order")
def create_order(
    body: CreateOrderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return billing_service.create_order(db, current_user.id, body.item_type, body.item_id)


@router.post("/verify-payment")
def verify_payment(
    body: VerifyPaymentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sub = billing_service.verify_payment(
        db,
        current_user.id,
        body.razorpay_order_id,
        body.razorpay_payment_id,
        body.razorpay_signature,
    )
    return {"status": "success", "item_type": sub.item_type, "item_name": sub.item_name}


@router.get("/summary")
def billing_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    billing_service.claim_welcome_bonus(db, current_user.id)
    return billing_service.get_billing_summary(db, current_user.id)
