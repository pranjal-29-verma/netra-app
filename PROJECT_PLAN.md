# Netra Chatbot - Project Plan & Progress

## 🎯 Project Overview

**Project Name:** Netra Chatbot  
**Description:** Personal knowledge chatbot that allows users to upload documents/links and query them using AI  
**Tech Stack:**
- **Frontend:** React.js + TypeScript + Tailwind CSS + Vite
- **Backend:** FastAPI + Python 3.14
- **Database:** PostgreSQL + Redis + ChromaDB (Vector DB)
- **LLM:** Claude Sonnet 4.5 (Anthropic)
- **Auth:** JWT + Google OAuth

---

## 📋 Development Phases

### **Phase 1: Architecture & Budget** ✅ COMPLETED
**Duration:** N/A  
**Status:** Completed

**Deliverables:**
- ✅ System architecture designed
- ✅ Technology stack finalized
- ✅ Monthly budget estimated ($20-25/month for single user)
- ✅ Database schema designed
- ✅ API structure planned

**Key Decisions:**
- Using Claude Sonnet 4.5 for LLM
- ChromaDB for vector storage (free, self-hosted)
- Sentence Transformers for embeddings (local, free)
- PostgreSQL for relational data
- Redis for sessions & incognito mode

---

### **Phase 2: Core Development** 🔄 IN PROGRESS
**Duration:** 3-4 weeks (estimated)  
**Status:** In Progress (Iteration 5/16 completed)

#### Iteration Breakdown:

##### **Iteration 1: Project Setup & Basic Authentication UI** ✅ COMPLETED
**Status:** Completed  
**Files Created:**
- Frontend project setup with Vite + React + TypeScript
- Tailwind CSS configuration
- Basic routing setup
- Login/Register UI components
- Zustand state management
- Type definitions

**Deliverables:**
- ✅ React project initialized
- ✅ Tailwind CSS configured
- ✅ Login page with form validation
- ✅ Registration page
- ✅ Protected routes structure
- ✅ Google OAuth button (UI only)

---

##### **Iteration 2: Authentication Backend** ✅ COMPLETED
**Status:** Completed  
**Backend Files Created:**
netra-backend/
├── app/
│   ├── main.py                    # FastAPI app entry point
│   ├── core/
│   │   ├── config.py              # Settings & environment variables
│   │   ├── database.py            # SQLAlchemy setup
│   │   └── security.py            # Password hashing, JWT functions
│   ├── models/
│   │   └── user.py                # User & UserToken models
│   ├── schemas/
│   │   └── user.py                # Pydantic schemas
│   ├── services/
│   │   └── auth_service.py        # Authentication business logic
│   └── api/
│       └── auth.py                # Auth endpoints
├── requirements.txt               # Python dependencies
└── .env                          # Environment variables

**Dependencies:**
fastapi==0.136.1
uvicorn[standard]==0.46.0
sqlalchemy==2.0.49
asyncpg==0.31.0
python-jose[cryptography]==3.5.0
bcrypt==5.0.0                      # Native bcrypt (not passlib)
python-multipart==0.0.28
pydantic==2.13.4
pydantic-settings==2.14.1
python-dotenv==1.2.2
alembic==1.18.4
psycopg2-binary==2.9.12

**Database Tables Created:**
- `users` - User accounts (username, email, password_hash, google_id)
- `user_tokens` - Token quota tracking (daily_quota, tokens_used)

**API Endpoints:**
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login with email/password
- `GET /api/auth/me` - Get current user (placeholder)

**Key Implementation Notes:**
- ✅ Using native `bcrypt` instead of deprecated `passlib`
- ✅ JWT tokens with 15-minute expiry
- ✅ Password hashing with bcrypt
- ✅ CORS configured for frontend

---

##### **Iteration 3: Connect Auth UI to Backend** ✅ COMPLETED
**Status:** Completed  
**Frontend Files Created:**
src/
├── config/
│   └── api.ts                     # API base URL & endpoints
├── services/
│   ├── api.ts                     # Axios instance with interceptors
│   └── authService.ts             # Auth API calls
└── store/
└── authStore.ts (updated)     # Real API integration

**Dependencies Added:**
- `react-hot-toast` - Toast notifications

**Deliverables:**
- ✅ Axios configured with interceptors
- ✅ Login form connected to backend
- ✅ Register form connected to backend
- ✅ JWT token storage in localStorage
- ✅ Protected routes with real auth check
- ✅ Error handling with toast notifications
- ✅ 401 auto-logout handling

**Key Implementation Notes:**
- ✅ Using `import type` for TypeScript types (prevents runtime errors)
- ✅ Toast notifications (no `toast.info`, use `toast.success/error`)
- ✅ Proper type imports vs value imports

---

##### **Iteration 4: Google OAuth Integration** ✅ COMPLETED
**Status:** Completed  
**Backend Files Updated/Created:**
app/
├── core/
│   └── config.py (updated)        # Added Google OAuth settings
├── services/
│   └── google_auth_service.py     # Google token verification
└── api/
└── auth.py (updated)          # Added /google endpoint

**Frontend Files Updated:**
src/
├── services/
│   └── authService.ts (updated)   # Added googleLogin()
└── components/auth/
└── LoginForm.tsx (updated)    # Added Google button logic

**Dependencies Added:**
Backend:
google-auth==2.37.0
google-auth-oauthlib==1.2.1
google-auth-httplib2==0.2.0

Frontend:
@react-oauth/google

**New API Endpoint:**
- `POST /api/auth/google` - Login/register with Google OAuth

**Deliverables:**
- ✅ Google OAuth consent screen configured
- ✅ Backend verifies Google tokens
- ✅ Auto-create user from Google account
- ✅ Link Google to existing email accounts
- ✅ One-click Google login working

---

##### **Iteration 5: Chat Interface UI** ✅ COMPLETED
**Status:** Completed  
**Frontend Files Created:**
src/
├── types/index.ts (updated)       # Added Message, Conversation types
├── store/
│   └── chatStore.ts               # Chat state management
├── components/chat/
│   ├── ChatLayout.tsx             # Main layout with sidebar
│   ├── ConversationList.tsx       # Sidebar conversation list
│   ├── ChatArea.tsx               # Main chat area
│   ├── Message.tsx                # Message bubble component
│   └── ChatInput.tsx              # Input field with send button
└── pages/
└── Dashboard.tsx (updated)    # Chat dashboard

**Dependencies Added:**
react-markdown
remark-gfm
rehype-highlight

**Deliverables:**
- ✅ Chat layout with collapsible sidebar
- ✅ Conversation list with mock data
- ✅ Message components (user & assistant)
- ✅ Chat input with auto-resize
- ✅ Copy message functionality
- ✅ Markdown rendering for AI responses
- ✅ Empty states
- ✅ Responsive design
- ✅ Token display placeholder

**Current State:**
- UI is fully functional with mock data
- Messages simulate AI responses (1-second delay)
- Next iteration will connect to real backend

---

##### **Iteration 6: Chat Backend (Basic)** 🔜 NEXT
**Status:** Not Started  
**Planned Backend Files:**
app/
├── models/
│   ├── conversation.py            # Conversation model
│   └── message.py                 # Message model
├── schemas/
│   ├── conversation.py            # Conversation schemas
│   └── message.py                 # Message schemas
├── services/
│   └── chat_service.py            # Chat business logic
└── api/
└── chat.py                    # Chat endpoints

**Planned Database Tables:**
- `conversations` - Chat conversations
- `messages` - Chat messages

**Planned API Endpoints:**
- `POST /api/conversations` - Create new conversation
- `GET /api/conversations` - List user conversations
- `GET /api/conversations/{id}` - Get conversation with messages
- `POST /api/conversations/{id}/messages` - Send message
- `DELETE /api/conversations/{id}` - Delete conversation

**Planned Deliverables:**
- Conversation CRUD operations
- Message storage
- Chat history retrieval
- Conversation title generation

---

##### **Iteration 7: Connect Chat UI to Backend** 🔜 UPCOMING
**Status:** Not Started  
**Planned Features:**
- Real-time message persistence
- Load chat history from database
- Create new conversations
- Delete conversations
- Update conversation titles

---

##### **Iteration 8: Token Management UI** 🔜 UPCOMING
**Status:** Not Started  
**Planned Features:**
- Token usage display
- Daily quota indicator
- Warning when quota low
- Token usage per message

---

##### **Iteration 9: Token Management Backend** 🔜 UPCOMING
**Status:** Not Started  
**Planned Features:**
- Token counting per message
- Daily quota enforcement
- Hourly rate limiting
- Token reset at midnight UTC
- Usage tracking

---

##### **Iteration 10: Incognito Mode UI** 🔜 UPCOMING
**Status:** Not Started  
**Planned Features:**
- Incognito toggle switch
- Visual indicators
- Session-based storage
- No history persistence

---

##### **Iteration 11: Incognito Mode Backend** 🔜 UPCOMING
**Status:** Not Started  
**Planned Features:**
- Redis integration
- Temporary message storage
- Session cleanup
- 24-hour TTL

---

##### **Iteration 12: Document Upload UI** 🔜 UPCOMING
**Status:** Not Started  
**Planned Features:**
- File upload component
- URL input for links
- Document list display
- Project/tag organization

---

##### **Iteration 13: Document Processing Backend** 🔜 UPCOMING
**Status:** Not Started  
**Planned Features:**
- File upload endpoint
- PDF/DOCX/TXT parsing
- Web scraping for URLs
- Text chunking strategy

---

##### **Iteration 14: Vector Database Integration** 🔜 UPCOMING
**Status:** Not Started  
**Planned Features:**
- ChromaDB setup
- Document embedding generation
- Vector storage
- Similarity search

---

##### **Iteration 15: LLM Integration (RAG)** 🔜 UPCOMING
**Status:** Not Started  
**Planned Features:**
- Claude API integration
- Retrieval-Augmented Generation (RAG)
- Context injection from documents
- Streaming responses
- Source citations

---

##### **Iteration 16: Polish & Bug Fixes** 🔜 UPCOMING
**Status:** Not Started  
**Planned Features:**
- Error handling improvements
- Loading states
- UI/UX polish
- Performance optimization

---

### **Phase 3: Deployment** ⏳ PENDING
**Duration:** 3-5 days (estimated)  
**Status:** Not Started

**Planned Tasks:**
- VM setup (Oracle Cloud Free Tier or Hetzner)
- PostgreSQL setup
- Redis setup
- Environment configuration
- SSL certificate (Let's Encrypt)
- Domain configuration
- Backend deployment
- Frontend build & deployment
- Database migrations
- Health checks & monitoring

---

### **Phase 4: Bug Fixing** ⏳ PENDING
**Duration:** 1 week (estimated)  
**Status:** Not Started

**Focus Areas:**
- Production bug fixes
- Performance issues
- Edge case handling
- User feedback implementation

---

### **Phase 5: Enhancements** ⏳ PENDING
**Duration:** Ongoing  
**Status:** Not Started

**Planned Features:**
- Email verification
- Password reset
- User profile editing
- Advanced search filters
- Export conversations
- API access
- Mobile responsive improvements
- Dark mode
- Multi-language support

---

## 🏗️ Architecture Overview

### Backend Architecture
FastAPI Backend (Port 8000)
├── API Layer (FastAPI)
│   ├── Auth Endpoints (/api/auth/)
│   ├── Chat Endpoints (/api/conversations/, /api/messages/)
│   └── Document Endpoints (/api/documents/)
│
├── Service Layer
│   ├── AuthService (business logic)
│   ├── ChatService
│   └── DocumentService
│
├── Database Layer
│   ├── PostgreSQL (users, conversations, messages, documents)
│   ├── Redis (sessions, incognito chats, token cache)
│   └── ChromaDB (vector embeddings)
│
└── External Services
├── Claude API (LLM)
└── Sentence Transformers (embeddings)

### Database Schema (Current)
```sql
-- Users
users (
  id, username, email, password_hash, google_id, 
  display_name, is_active, created_at, last_login
)

-- Token Management
user_tokens (
  id, user_id, daily_quota, tokens_used, 
  last_reset, total_tokens_used
)

-- Conversations (To be added in Iteration 6)
conversations (
  id, user_id, title, is_incognito, 
  created_at, updated_at, deleted_at
)

-- Messages (To be added in Iteration 6)
messages (
  id, conversation_id, role, content, 
  tokens_used, sources, created_at
)

-- Documents (To be added in Iteration 13)
user_documents (
  id, user_id, filename, file_type, file_size,
  file_path, is_url, url, project_tag, 
  indexed_at, created_at
)
```

---

## 🔑 Environment Variables

**Required Environment Variables:**
```env
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/netra_chatbot

# JWT
SECRET_KEY=<your-secret-key>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
FRONTEND_URL=http://localhost:5174
ALLOWED_ORIGINS=["http://localhost:5173", "http://localhost:5174"]

# Google OAuth
GOOGLE_CLIENT_ID=<your-client-id>.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=<your-client-secret>
GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/google/callback

# Environment
ENVIRONMENT=development
```

---

## 🐛 Known Issues & Technical Decisions

### Issue 1: Passlib Deprecated (Python 3.14)
**Problem:** `passlib[bcrypt]` crashes with `ValueError` on Python 3.14  
**Solution:** Use native `bcrypt==5.0.0` directly  
**Files Affected:** `app/core/security.py`, `requirements.txt`

### Issue 2: TypeScript Runtime Import Error
**Problem:** `InternalAxiosRequestConfig` treated as runtime value  
**Solution:** Use `import type { InternalAxiosRequestConfig }`  
**Files Affected:** `src/services/api.ts`

### Issue 3: react-hot-toast API
**Problem:** No `toast.info()` method exists  
**Solution:** Use `toast()`, `toast.success()`, or `toast.error()`  
**Files Affected:** `src/components/auth/LoginForm.tsx`

---

## 📝 Development Guidelines

### Code Style
- **Backend:** PEP 8, type hints, docstrings
- **Frontend:** ESLint, Prettier, TypeScript strict mode

### Git Workflow
- Feature branches: `feature/iteration-{number}-{name}`
- Commit format: `[Iteration {number}] Description`

### Testing Strategy (To be implemented)
- Unit tests for services
- Integration tests for API endpoints
- E2E tests for critical flows

---

## 📊 Progress Tracking

**Overall Progress:** 31% (5/16 iterations completed)

| Phase | Progress | Status |
|-------|----------|--------|
| Phase 1: Planning | 100% | ✅ Done |
| Phase 2: Development | 31% | 🔄 In Progress |
| Phase 3: Deployment | 0% | ⏳ Pending |
| Phase 4: Bug Fixes | 0% | ⏳ Pending |
| Phase 5: Enhancements | 0% | ⏳ Pending |

**Next Milestone:** Complete Iteration 6 (Chat Backend)

---

## 🚀 Quick Start Commands

### Development
```bash
# Start backend
cd netra-backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000

# View API docs
open http://localhost:8000/docs
```

### Database
```bash
# Access PostgreSQL
psql -d netra_chatbot

# Reset database (development only)
psql -d netra_chatbot -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
```

---

## 📚 Additional Resources

- **FastAPI Docs:** https://fastapi.tiangolo.com/
- **SQLAlchemy Docs:** https://docs.sqlalchemy.org/
- **Anthropic Claude API:** https://docs.anthropic.com/
- **ChromaDB Docs:** https://docs.trychroma.com/

---

**Last Updated:** Iteration 5 Completed  
**Next Update:** After Iteration 6
