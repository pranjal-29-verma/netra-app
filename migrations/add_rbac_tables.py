"""
Migration: Create RBAC tables (roles, permissions, role_permissions, user_roles)
and seed default roles + permissions.

Run once: python migrations/add_rbac_tables.py
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import engine
from sqlalchemy import text

# All permissions in the system
PERMISSIONS = [
    ("users:read",              "View user list and profiles"),
    ("users:ban",               "Ban or unban users"),
    ("users:delete",            "Delete users"),
    ("roles:assign",            "Assign or revoke roles from users"),
    ("roles:manage",            "Create roles and manage role permissions"),
    ("conversations:read_meta", "View conversation metadata (no message content)"),
    ("conversations:delete",    "Delete any conversation"),
    ("documents:read",          "View all uploaded documents"),
    ("documents:delete",        "Delete any document"),
    ("analytics:view",          "View token usage analytics and charts"),
    ("system:config",           "Manage system-wide configuration"),
]

# Role → list of permission names it receives
ROLE_PERMISSIONS = {
    "admin": [p[0] for p in PERMISSIONS],  # all permissions
    "moderator": [
        "users:read",
        "users:ban",
        "conversations:read_meta",
        "conversations:delete",
        "documents:read",
        "documents:delete",
    ],
}

ROLES = [
    ("admin",     "Full access to all admin features"),
    ("moderator", "Can manage users and content, no analytics or system config"),
]


def run():
    with engine.connect() as conn:
        # ── Create tables ────────────────────────────────────────────────────
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS roles (
                id          SERIAL PRIMARY KEY,
                name        VARCHAR(50) UNIQUE NOT NULL,
                description VARCHAR(255)
            );
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS permissions (
                id          SERIAL PRIMARY KEY,
                name        VARCHAR(100) UNIQUE NOT NULL,
                description VARCHAR(255)
            );
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS role_permissions (
                role_id       INTEGER REFERENCES roles(id) ON DELETE CASCADE,
                permission_id INTEGER REFERENCES permissions(id) ON DELETE CASCADE,
                PRIMARY KEY (role_id, permission_id)
            );
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_roles (
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                role_id INTEGER REFERENCES roles(id) ON DELETE CASCADE,
                PRIMARY KEY (user_id, role_id)
            );
        """))

        # ── Seed permissions ─────────────────────────────────────────────────
        for name, description in PERMISSIONS:
            conn.execute(text("""
                INSERT INTO permissions (name, description)
                VALUES (:name, :description)
                ON CONFLICT (name) DO NOTHING;
            """), {"name": name, "description": description})

        # ── Seed roles ───────────────────────────────────────────────────────
        for name, description in ROLES:
            conn.execute(text("""
                INSERT INTO roles (name, description)
                VALUES (:name, :description)
                ON CONFLICT (name) DO NOTHING;
            """), {"name": name, "description": description})

        # ── Wire role → permissions ──────────────────────────────────────────
        for role_name, perm_names in ROLE_PERMISSIONS.items():
            for perm_name in perm_names:
                conn.execute(text("""
                    INSERT INTO role_permissions (role_id, permission_id)
                    SELECT r.id, p.id
                    FROM roles r, permissions p
                    WHERE r.name = :role AND p.name = :perm
                    ON CONFLICT DO NOTHING;
                """), {"role": role_name, "perm": perm_name})

        conn.commit()

    print("Migration complete: RBAC tables created and seeded.")
    print(f"  Roles:       {[r[0] for r in ROLES]}")
    print(f"  Permissions: {len(PERMISSIONS)} entries")


if __name__ == "__main__":
    run()
