from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.models.user import UserToken
from app.core.config import settings


class TokenService:

    @staticmethod
    def get_or_create(db: Session, user_id: int) -> UserToken:
        record = db.query(UserToken).filter(UserToken.user_id == user_id).first()
        if not record:
            record = UserToken(user_id=user_id, daily_quota=settings.FREE_TIER_DAILY_QUOTA)
            db.add(record)
            db.commit()
            db.refresh(record)
        return record

    @staticmethod
    def get_usage(db: Session, user_id: int) -> UserToken:
        record = TokenService.get_or_create(db, user_id)

        # Reset daily counter if last_reset was on a previous UTC day
        now_utc = datetime.now(timezone.utc)
        last_reset = record.last_reset
        if last_reset.tzinfo is None:
            last_reset = last_reset.replace(tzinfo=timezone.utc)

        if last_reset.date() < now_utc.date():
            record.tokens_used = 0
            record.last_reset = now_utc

            # Check if active plan has expired on this new day
            if record.plan_expires_at:
                expires_at = record.plan_expires_at
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                if now_utc > expires_at:
                    record.active_plan_id = None
                    record.plan_expires_at = None
                    record.daily_quota = settings.FREE_TIER_DAILY_QUOTA

            db.commit()
            db.refresh(record)

        return record

    @staticmethod
    def add_tokens(db: Session, user_id: int, tokens: int) -> None:
        record = TokenService.get_usage(db, user_id)

        daily_remaining = record.daily_quota - record.tokens_used

        if daily_remaining >= tokens:
            # Daily quota covers it
            record.tokens_used += tokens
        elif daily_remaining > 0:
            # Partial from daily quota, rest from bonus tokens
            record.tokens_used += daily_remaining
            overflow = tokens - daily_remaining
            record.bonus_tokens = max(0, record.bonus_tokens - overflow)
        else:
            # Daily quota exhausted — consume from bonus tokens
            record.bonus_tokens = max(0, record.bonus_tokens - tokens)

        record.total_tokens_used += tokens
        db.commit()
