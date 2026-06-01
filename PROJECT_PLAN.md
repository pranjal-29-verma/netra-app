# Netra Chatbot - Backend Project Plan

## Project Overview

**Project Name:** Netra Chatbot Backend
**Description:** FastAPI backend for a personal knowledge chatbot — RAG pipeline, LLM streaming, RBAC admin panel, multi-provider LLM config, email verification, rate limiting
**Tech Stack:**
- FastAPI + Python 3.14
- PostgreSQL (Supabase) + pgvector (vector search)
- SQLAlchemy (ORM)
- LiteLLM (multi-provider LLM abstraction)
- Voyage AI (embeddings)
- Supabase Storage (document files)
- JWT + Google OAuth (auth)
- Fernet (API key encryption)
- SlowAPI (rate limiting)
- netra-notify (internal email microservice)

---

## Development Workflow (AI_CODE_CLI_RULES.md)

Before every task:
1. `git checkout main && git fetch origin && git pull origin main`
2. `git checkout -b <feature|bugfix|hotfix|refactor>/<name>`
3. Implement changes
4. Show modified files + summary → ask user before committing
5. Commit format:
```
<TicketNo> : One line summary

What is changed?
--------------
- list of changes

Testing
--------------
- testing performed
```
Never commit directly to main. Never push without explicit user approval.

---

## Project Structure

```
netra-app/
├── app/
│   ├── main.py                    # FastAPI app, lifespan hook, routers, rate limit setup
│   ├── core/
│   │   ├── config.py              # Pydantic settings from .env
│   │   ├── database.py            # SQLAlchemy engine + SessionLocal
│   │   ├── security.py            # JWT, bcrypt, require_permission()
│   │   ├── storage.py             # Supabase Storage client
│   │   ├── encryption.py          # Fernet encrypt/decrypt for LLM keys
│   │   └── rate_limit.py          # SlowAPI limiter + key functions
│   ├── models/
│   │   ├── user.py                # User (+ email verification), UserToken
│   │   ├── conversation.py        # Conversation
│   │   ├── message.py             # Message
│   │   ├── document.py            # Document
│   │   ├── document_chunk.py      # DocumentChunk (pgvector)
│   │   ├── rbac.py                # Role, Permission, junction tables
│   │   ├── audit_log.py           # AuditLog
│   │   └── llm_config.py          # LLMConfig, SystemConfig
│   ├── schemas/
│   │   ├── user.py                # UserResponse (+ is_verified), UserUpdate, PasswordChange
│   │   ├── conversation.py
│   │   ├── message.py
│   │   ├── document.py
│   │   └── token.py
│   ├── services/
│   │   ├── auth_service.py        # + email verification token logic
│   │   ├── chat_service.py        # RAG orchestration + SSE streaming
│   │   ├── llm_service.py         # LiteLLM streaming + asyncio Semaphore
│   │   ├── llm_config_service.py  # In-memory active LLM cache
│   │   ├── notify_client.py       # HTTP client → netra-notify (fire-and-forget)
│   │   ├── audit_service.py       # Audit log writes
│   │   ├── token_service.py
│   │   ├── document_service.py
│   │   ├── vector_service.py      # pgvector store + similarity search
│   │   ├── embedding_service.py   # Voyage AI embeddings
│   │   ├── chunking_service.py
│   │   └── text_extractor.py
│   └── api/
│       ├── auth.py                # + /verify-email, /resend-verification (rate limited)
│       ├── chat.py                # rate limited
│       ├── conversations.py       # rate limited stream endpoint
│       ├── documents.py
│       ├── tokens.py
│       ├── users.py
│       └── admin/
│           └── router.py          # All admin + LLM config + audit log endpoints
├── migrations/
│   ├── add_rbac_tables.py
│   ├── add_user_profile_columns.py
│   ├── add_llm_config_tables.py
│   ├── add_audit_logs_table.py
│   ├── add_quota_permission.py
│   └── add_email_verification.py
├── requirements.txt
├── .env
├── .env.example
├── AI_CODE_CLI_RULES.md
└── PROJECT_PLAN.md
```

---

## Database Schema (Current)

```sql
users (
  id, username, email, password_hash, google_id,
  display_name, gender, avatar_seed, save_conversations,
  theme, is_active,
  is_verified, verification_token, verification_token_expires_at,
  created_at, last_login
)

user_tokens (id, user_id, daily_quota, tokens_used, last_reset, total_tokens_used)

conversations (id, user_id, title, is_incognito, created_at, updated_at)
messages (id, conversation_id, role, content, tokens_used, sources, created_at)

documents (
  id, user_id, filename, file_type, file_size,
  storage_path, source_url, status, scope, conversation_id, created_at
)
document_chunks (id, document_id, content, embedding vector(1024), chunk_index, created_at)

roles (id, name, description)
permissions (id, name, description)
role_permissions (role_id, permission_id)
user_roles (user_id, role_id)

audit_logs (id, admin_id, action, target_user_id, detail, created_at)

llm_configs (id, provider, model_name, display_label, api_key_encrypted, is_active, created_at)
system_config (id=1, use_custom_llm)
```

---

## API Endpoints (Current)

### Auth
- `POST /api/auth/register`            — rate limited: RATE_LIMIT_REGISTER
- `POST /api/auth/login`               — rate limited: RATE_LIMIT_LOGIN
- `POST /api/auth/google`              — rate limited: RATE_LIMIT_GOOGLE
- `POST /api/auth/refresh`             — rate limited: RATE_LIMIT_REFRESH
- `GET  /api/auth/verify-email`        — email verification link handler
- `POST /api/auth/resend-verification` — resend verification email
- `GET  /api/auth/me`

### Users
- `GET    /api/users/me`
- `PATCH  /api/users/me`
- `PATCH  /api/users/me/password`

### Conversations & Chat
- `GET    /api/conversations`
- `POST   /api/conversations`
- `DELETE /api/conversations/{id}`
- `GET    /api/conversations/{id}/messages`
- `POST   /api/conversations/{id}/messages/stream` (SSE) — rate limited: RATE_LIMIT_CHAT
- `POST   /api/chat/stream`                          (SSE) — rate limited: RATE_LIMIT_CHAT

### Tokens
- `GET /api/tokens/usage`

### Documents
- `GET    /api/documents`
- `POST   /api/documents/upload`
- `POST   /api/documents/url`
- `DELETE /api/documents/{id}`

### Admin
- `GET    /api/admin/me`
- `GET    /api/admin/stats`
- `GET    /api/admin/activity`
- `GET    /api/admin/users`
- `GET    /api/admin/users/{id}`
- `PATCH  /api/admin/users/{id}/ban`
- `PATCH  /api/admin/users/{id}/quota`
- `DELETE /api/admin/users/{id}`
- `PUT    /api/admin/users/{id}/roles`
- `GET    /api/admin/roles`
- `POST   /api/admin/roles`
- `GET    /api/admin/permissions`
- `GET    /api/admin/conversations`
- `DELETE /api/admin/conversations/{id}`
- `GET    /api/admin/documents`
- `DELETE /api/admin/documents/{id}`
- `GET    /api/admin/analytics/registrations`
- `GET    /api/admin/analytics/conversations`
- `GET    /api/admin/analytics/top-users`
- `GET    /api/admin/audit-logs`
- `GET    /api/admin/llm/supported-models`
- `GET    /api/admin/llm/settings`
- `PATCH  /api/admin/llm/toggle`
- `POST   /api/admin/llm/configs`
- `POST   /api/admin/llm/configs/test`
- `POST   /api/admin/llm/configs/{id}/activate`
- `POST   /api/admin/llm/configs/{id}/deactivate`
- `DELETE /api/admin/llm/configs/{id}`

---

## Permissions (RBAC)

| Permission | Description | Roles |
|---|---|---|
| users:read | View user list and profiles | admin, moderator |
| users:ban | Activate/deactivate users | admin, moderator |
| users:delete | Delete users | admin |
| users:manage_quota | Override individual user daily token quota | admin |
| roles:assign | Assign/revoke roles | admin |
| roles:manage | Create roles and manage permissions | admin |
| conversations:read_meta | View conversation metadata | admin, moderator |
| conversations:delete | Delete any conversation | admin, moderator |
| documents:read | View all documents | admin, moderator |
| documents:delete | Delete any document | admin, moderator |
| analytics:view | View analytics charts | admin |
| system:config | Manage system-wide config | admin |
| manage_models | Add, activate, test LLM configs | admin |

---

## Completed Work

| Phase | Item | Status |
|-------|------|--------|
| Core | Auth (JWT + Google OAuth + refresh tokens) | ✅ Done |
| Core | Conversations + message persistence | ✅ Done |
| Core | Cursor-based message pagination (limit + before_id) | ✅ Done |
| Core | Token quota tracking | ✅ Done |
| Core | Document upload (Supabase Storage) | ✅ Done |
| Core | RAG pipeline (pgvector + Voyage AI) | ✅ Done |
| Core | LLM streaming via LiteLLM (SSE) | ✅ Done |
| Core | Incognito stateless chat endpoint | ✅ Done |
| Core | User profile settings (display name, avatar, theme, privacy) | ✅ Done |
| Phase 5 | RBAC tables, permissions, seed data | ✅ Done |
| Phase 5 | Admin endpoints: users, roles, content, analytics | ✅ Done |
| Phase 5 | Theme persistence (DB column + sync on login) | ✅ Done |
| Phase 6 | LLM model config: encrypted storage, in-memory cache, admin endpoints | ✅ Done |
| Phase 6 | Audit logs: admin action tracking with filters + pagination | ✅ Done |
| Phase 6 | Token quota per user: admin override via PATCH /users/{id}/quota | ✅ Done |
| Phase 7 | Email verification (P7.1): token generation, verify + resend endpoints | ✅ Done |
| Phase 7 | Rate limiting (P7.2): SlowAPI on auth + chat, LLM semaphore | ✅ Done |

---

## Phase 6: Admin Panel Completion

| # | Item | Status |
|---|------|--------|
| P6.1 | LLM model config | ✅ Done |
| P6.2 | Audit logs | ✅ Done |
| P6.3 | Token quota per user | ✅ Done |
| P6.4 | System announcements | 🔲 Todo |

---

## Phase 7: Production Readiness

| # | Item | Status |
|---|------|--------|
| P7.1 | Email verification (netra-notify + verify/resend endpoints) | ✅ Done |
| P7.2 | Rate limiting (SlowAPI + LLM concurrency semaphore) | ✅ Done |
| P7.3 | Password reset flow | 🔲 Todo |
| P7.4 | In-app notifications | 🔲 Todo |
| P7.5 | Payment gateway (Stripe integration, plan tiers) | 🔲 Todo |

---

## Phase 8: User Experience Polish

| # | Item | Status |
|---|------|--------|
| P8.1 | Conversation export — PDF or Markdown download | 🔲 Todo |
| P8.2 | Chat history search — full-text search inside message content | 🔲 Todo |
| P8.3 | Model usage analytics — usage per model, estimated cost | 🔲 Todo |
| P8.4 | Message feedback — thumbs up/down on AI responses | 🔲 Todo |
| P8.5 | Conversation sharing — public read-only link | 🔲 Todo |
| P8.6 | Document summarization — auto-summary on upload | 🔲 Todo |
| P8.7 | Two-factor authentication (2FA) — TOTP-based | 🔲 Todo |
| P8.8 | Code optimization — profile and optimize based on real usage data | 🔲 Todo (last) |

---

## Environment Variables

See `.env.example` for the full reference with comments.

Key groups:
- **Database** — `DATABASE_URL`
- **JWT** — `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`
- **Google OAuth** — `GOOGLE_CLIENT_ID`
- **Supabase** — `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_STORAGE_BUCKET`
- **Voyage AI** — `VOYAGE_API_KEY`
- **LLM** — `LLM_MODEL`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `MISTRAL_API_KEY`, `LLM_ENCRYPTION_KEY`, `LLM_MAX_CONCURRENT`
- **Notify** — `NOTIFY_BASE_URL`, `NOTIFY_API_KEY`, `NOTIFY_ENABLED`
- **Rate limits** — `RATE_LIMIT_LOGIN`, `RATE_LIMIT_REGISTER`, `RATE_LIMIT_GOOGLE`, `RATE_LIMIT_REFRESH`, `RATE_LIMIT_CHAT`
- **CORS** — `FRONTEND_URL`, `ALLOWED_ORIGINS`
- **App** — `ENVIRONMENT`

---

**Last Updated:** Phase 7 — P7.1 Email Verification ✅, P7.2 Rate Limiting ✅. Next: P6.4 System Announcements or P7.3 Password Reset.
