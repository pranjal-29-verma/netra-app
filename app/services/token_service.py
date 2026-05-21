from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.models.user import UserToken


class TokenService:

    @staticmethod
    def get_or_create(db: Session, user_id: int) -> UserToken:
        record = db.query(UserToken).filter(UserToken.user_id == user_id).first()
        if not record:
            record = UserToken(user_id=user_id)
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
            db.commit()
            db.refresh(record)

        return record

    @staticmethod
    def add_tokens(db: Session, user_id: int, tokens: int) -> None:
        record = TokenService.get_or_create(db, user_id)
        record.tokens_used += tokens
        record.total_tokens_used += tokens
        db.commit()
