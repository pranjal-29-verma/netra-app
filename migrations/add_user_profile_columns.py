"""
Migration: Add gender, avatar_seed, save_conversations to users table
Run once: python migrations/add_user_profile_columns.py
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
            ADD COLUMN IF NOT EXISTS gender VARCHAR(10),
            ADD COLUMN IF NOT EXISTS avatar_seed VARCHAR(100),
            ADD COLUMN IF NOT EXISTS save_conversations BOOLEAN DEFAULT TRUE NOT NULL;
        """))
        conn.commit()
    print("Migration complete: gender, avatar_seed, save_conversations added to users table.")

if __name__ == "__main__":
    run()
