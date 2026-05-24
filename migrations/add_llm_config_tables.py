"""
Migration: Create llm_configs and system_config tables.
Add manage_models permission and assign it to the admin role.

Run once: python migrations/add_llm_config_tables.py
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import engine
from sqlalchemy import text


def run():
    with engine.connect() as conn:
        # ── llm_configs table ────────────────────────────────────────────────
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS llm_configs (
                id                SERIAL PRIMARY KEY,
                provider          VARCHAR(50)  NOT NULL,
                model_name        VARCHAR(100) NOT NULL,
                display_label     VARCHAR(100),
                api_key_encrypted TEXT         NOT NULL,
                is_active         BOOLEAN      NOT NULL DEFAULT FALSE,
                created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW()
            );
        """))

        # ── system_config singleton table ────────────────────────────────────
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS system_config (
                id             INTEGER PRIMARY KEY DEFAULT 1,
                use_custom_llm BOOLEAN NOT NULL DEFAULT FALSE,
                CONSTRAINT singleton CHECK (id = 1)
            );
        """))

        # Seed the singleton row if not present
        conn.execute(text("""
            INSERT INTO system_config (id, use_custom_llm)
            VALUES (1, FALSE)
            ON CONFLICT (id) DO NOTHING;
        """))

        # ── manage_models permission ─────────────────────────────────────────
        conn.execute(text("""
            INSERT INTO permissions (name, description)
            VALUES ('manage_models', 'Add, activate, test, and delete LLM model configurations')
            ON CONFLICT (name) DO NOTHING;
        """))

        # Assign manage_models to admin role
        conn.execute(text("""
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM roles r, permissions p
            WHERE r.name = 'admin' AND p.name = 'manage_models'
            ON CONFLICT DO NOTHING;
        """))

        conn.commit()

    print("Migration complete.")
    print("  Created: llm_configs, system_config tables")
    print("  Added:   manage_models permission → admin role")


if __name__ == "__main__":
    run()
