"""
Migration: Add users:manage_quota permission and assign to admin role.

Run once: python migrations/add_quota_permission.py
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import engine
from sqlalchemy import text


def run():
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO permissions (name, description)
            VALUES ('users:manage_quota', 'Override individual user daily token quota')
            ON CONFLICT (name) DO NOTHING;
        """))

        conn.execute(text("""
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM roles r, permissions p
            WHERE r.name = 'admin' AND p.name = 'users:manage_quota'
            ON CONFLICT DO NOTHING;
        """))

        conn.commit()

    print("Migration complete.")
    print("  Added: users:manage_quota permission → admin role")


if __name__ == "__main__":
    run()
