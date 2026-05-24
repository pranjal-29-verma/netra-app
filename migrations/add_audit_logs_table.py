"""
Migration: Create audit_logs table and add audit:view permission to admin role.

Run once: python migrations/add_audit_logs_table.py
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import engine
from sqlalchemy import text


def run():
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id           SERIAL PRIMARY KEY,
                actor_id     INTEGER,
                actor_name   VARCHAR(100) NOT NULL,
                action       VARCHAR(50)  NOT NULL,
                target_type  VARCHAR(50),
                target_id    VARCHAR(50),
                target_label VARCHAR(200),
                meta         JSONB,
                created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """))

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_audit_logs_action     ON audit_logs (action);
            CREATE INDEX IF NOT EXISTS idx_audit_logs_actor_name ON audit_logs (actor_name);
            CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs (created_at DESC);
        """))

        conn.execute(text("""
            INSERT INTO permissions (name, description)
            VALUES ('audit:view', 'View admin audit logs')
            ON CONFLICT (name) DO NOTHING;
        """))

        conn.execute(text("""
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM roles r, permissions p
            WHERE r.name = 'admin' AND p.name = 'audit:view'
            ON CONFLICT DO NOTHING;
        """))

        conn.commit()

    print("Migration complete.")
    print("  Created: audit_logs table with indexes")
    print("  Added:   audit:view permission → admin role")


if __name__ == "__main__":
    run()
