"""
Migration: Add billing tables and update user_tokens with bonus/plan columns.

Run once: python migrations/add_billing_tables.py
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import engine
from sqlalchemy import text


def run():
    with engine.connect() as conn:
        # Plans
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS plans (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                price_inr INTEGER NOT NULL,
                tokens_per_day INTEGER NOT NULL,
                duration_days INTEGER NOT NULL,
                max_documents INTEGER,
                max_conversations INTEGER,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """))

        # Token packs
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS token_packs (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                price_inr INTEGER NOT NULL,
                bonus_tokens INTEGER NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """))

        # User subscriptions
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_subscriptions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                item_type VARCHAR(20) NOT NULL,
                item_id INTEGER NOT NULL,
                item_name VARCHAR(100) NOT NULL,
                amount_paid INTEGER NOT NULL,
                razorpay_order_id VARCHAR(100) NOT NULL UNIQUE,
                razorpay_payment_id VARCHAR(100),
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                started_at TIMESTAMPTZ,
                expires_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """))

        # Add billing columns to user_tokens
        conn.execute(text("""
            ALTER TABLE user_tokens
            ADD COLUMN IF NOT EXISTS bonus_tokens INTEGER NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS welcome_bonus_claimed BOOLEAN NOT NULL DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS active_plan_id INTEGER,
            ADD COLUMN IF NOT EXISTS plan_expires_at TIMESTAMPTZ;
        """))

        # Seed default plan — Starter: 10,000 tokens/day, 30 days, ₹20
        conn.execute(text("""
            INSERT INTO plans (name, description, price_inr, tokens_per_day, duration_days, max_documents, max_conversations)
            VALUES (
                'Starter',
                '10,000 tokens per day for 30 days. Unlimited conversations.',
                20, 10000, 30, 10, NULL
            )
            ON CONFLICT DO NOTHING;
        """))

        # Seed default token pack — Boost: 5,000 bonus tokens, ₹20
        conn.execute(text("""
            INSERT INTO token_packs (name, description, price_inr, bonus_tokens)
            VALUES (
                'Boost Pack',
                '5,000 bonus tokens that never expire. Use anytime.',
                20, 5000
            )
            ON CONFLICT DO NOTHING;
        """))

        conn.commit()

    print("Migration complete.")
    print("  Created: plans, token_packs, user_subscriptions tables")
    print("  Updated: user_tokens with bonus_tokens, welcome_bonus_claimed, active_plan_id, plan_expires_at")
    print("  Seeded: Starter plan (₹20) + Boost Pack (₹20)")


if __name__ == "__main__":
    run()
