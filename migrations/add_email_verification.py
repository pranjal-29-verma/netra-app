"""
Migration: Add email verification columns to users table.

Run once: python migrations/add_email_verification.py
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import engine
from sqlalchemy import text


def run():
    with engine.connect() as conn:
        conn.execute(text("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS is_verified BOOLEAN NOT NULL DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS verification_token VARCHAR(100) UNIQUE,
            ADD COLUMN IF NOT EXISTS verification_token_expires_at TIMESTAMPTZ;
        """))

        # Google OAuth users are auto-verified — Google already confirmed their email
        conn.execute(text("""
            UPDATE users SET is_verified = TRUE WHERE google_id IS NOT NULL;
        """))

        conn.commit()

    print("Migration complete.")
    print("  Added: is_verified, verification_token, verification_token_expires_at")
    print("  Google OAuth users → auto-verified.")


if __name__ == "__main__":
    run()
