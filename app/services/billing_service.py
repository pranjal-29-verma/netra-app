import hmac
import hashlib
import razorpay
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.core.config import settings
from app.models.billing import Plan, TokenPack, UserSubscription
from app.models.user import UserToken

logger = logging.getLogger(__name__)


def _razorpay_client() -> razorpay.Client:
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def _get_or_create_token_record(db: Session, user_id: int) -> UserToken:
    record = db.query(UserToken).filter(UserToken.user_id == user_id).first()
    if not record:
        record = UserToken(user_id=user_id, daily_quota=settings.FREE_TIER_DAILY_QUOTA)
        db.add(record)
        db.commit()
        db.refresh(record)
    return record


def claim_welcome_bonus(db: Session, user_id: int) -> None:
    """Give 500 bonus tokens on first login if not already claimed."""
    record = _get_or_create_token_record(db, user_id)
    if not record.welcome_bonus_claimed:
        record.bonus_tokens += settings.WELCOME_BONUS_TOKENS
        record.welcome_bonus_claimed = True
        db.commit()


def get_active_plan(db: Session, user_id: int) -> Plan | None:
    """Return the user's active plan if not expired, else expire it."""
    record = _get_or_create_token_record(db, user_id)
    if not record.active_plan_id or not record.plan_expires_at:
        return None

    expires_at = record.plan_expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) > expires_at:
        # Plan expired — reset to free tier
        record.active_plan_id = None
        record.plan_expires_at = None
        record.daily_quota = settings.FREE_TIER_DAILY_QUOTA
        db.commit()
        return None

    return db.query(Plan).filter(Plan.id == record.active_plan_id).first()


def create_order(db: Session, user_id: int, item_type: str, item_id: int) -> dict:
    """Create a Razorpay order for a plan or token pack."""
    if item_type == "plan":
        item = db.query(Plan).filter(Plan.id == item_id, Plan.is_active == True).first()
        if not item:
            raise HTTPException(status_code=404, detail="Plan not found or inactive")
        amount_paise = item.price_inr * 100
        item_name = item.name
    elif item_type == "pack":
        item = db.query(TokenPack).filter(TokenPack.id == item_id, TokenPack.is_active == True).first()
        if not item:
            raise HTTPException(status_code=404, detail="Token pack not found or inactive")
        amount_paise = item.price_inr * 100
        item_name = item.name
    else:
        raise HTTPException(status_code=400, detail="item_type must be 'plan' or 'pack'")

    if amount_paise < 100:
        raise HTTPException(status_code=400, detail="Amount must be at least ₹1")

    client = _razorpay_client()
    try:
        order = client.order.create({
            "amount": amount_paise,
            "currency": "INR",
            "receipt": f"{item_type}_{item_id}_user_{user_id}",
        })
    except Exception as exc:
        logger.error(f"Razorpay order creation failed: {exc}")
        raise HTTPException(status_code=500, detail="Payment gateway error. Please try again.")

    # Save pending subscription record
    sub = UserSubscription(
        user_id=user_id,
        item_type=item_type,
        item_id=item_id,
        item_name=item_name,
        amount_paid=amount_paise,
        razorpay_order_id=order["id"],
        status="pending",
    )
    db.add(sub)
    db.commit()

    return {
        "order_id": order["id"],
        "amount": amount_paise,
        "currency": "INR",
        "key_id": settings.RAZORPAY_KEY_ID,
        "item_name": item_name,
    }


def verify_payment(
    db: Session,
    user_id: int,
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
) -> UserSubscription:
    """Verify HMAC signature, mark paid, activate plan or credit tokens."""

    # 1. Verify signature
    expected = hmac.new(
        key=settings.RAZORPAY_KEY_SECRET.encode(),
        msg=f"{razorpay_order_id}|{razorpay_payment_id}".encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, razorpay_signature):
        raise HTTPException(status_code=400, detail="Payment signature verification failed")

    # 2. Find the pending subscription
    sub = db.query(UserSubscription).filter(
        UserSubscription.razorpay_order_id == razorpay_order_id,
        UserSubscription.user_id == user_id,
    ).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Order not found")
    if sub.status == "paid":
        return sub  # idempotent

    # 3. Mark paid
    sub.razorpay_payment_id = razorpay_payment_id
    sub.status = "paid"
    sub.started_at = datetime.now(timezone.utc)

    # 4. Activate plan or credit bonus tokens
    token_record = _get_or_create_token_record(db, user_id)

    if sub.item_type == "plan":
        plan = db.query(Plan).filter(Plan.id == sub.item_id).first()
        if plan:
            expires_at = datetime.now(timezone.utc) + timedelta(days=plan.duration_days)
            sub.expires_at = expires_at
            token_record.active_plan_id = plan.id
            token_record.plan_expires_at = expires_at
            token_record.daily_quota = plan.tokens_per_day
            token_record.tokens_used = 0  # reset today's usage on upgrade

    elif sub.item_type == "pack":
        pack = db.query(TokenPack).filter(TokenPack.id == sub.item_id).first()
        if pack:
            token_record.bonus_tokens += pack.bonus_tokens

    db.commit()
    db.refresh(sub)
    return sub


def get_billing_summary(db: Session, user_id: int) -> dict:
    """Return current plan, token balances and purchase history."""
    token_record = _get_or_create_token_record(db, user_id)
    active_plan = get_active_plan(db, user_id)

    history = (
        db.query(UserSubscription)
        .filter(UserSubscription.user_id == user_id, UserSubscription.status == "paid")
        .order_by(UserSubscription.created_at.desc())
        .limit(20)
        .all()
    )

    return {
        "active_plan": {
            "id": active_plan.id,
            "name": active_plan.name,
            "tokens_per_day": active_plan.tokens_per_day,
            "expires_at": token_record.plan_expires_at,
        } if active_plan else None,
        "daily_quota": token_record.daily_quota,
        "tokens_used_today": token_record.tokens_used,
        "bonus_tokens": token_record.bonus_tokens,
        "welcome_bonus_claimed": token_record.welcome_bonus_claimed,
        "history": [
            {
                "id": s.id,
                "item_type": s.item_type,
                "item_name": s.item_name,
                "amount_paid": s.amount_paid,
                "status": s.status,
                "created_at": s.created_at,
                "expires_at": s.expires_at,
            }
            for s in history
        ],
    }
