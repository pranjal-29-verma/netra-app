# Netra Chatbot API

Netra is a Personal Knowledge Chatbot backend application built with **FastAPI**, **Uvicorn**, and **SQLAlchemy** (with PostgreSQL/Supabase support).

---

## 🚀 Getting Started

Follow these step-by-step instructions to set up the project and run the backend server locally.

### Prerequisites

- **Python 3.10+** installed on your system.
- A **PostgreSQL** database (or Supabase instance).

---

### 1. Environment Setup

Open your terminal, navigate to the project root directory, and execute the following:

#### A. Create and Activate Virtual Environment

We recommend using a Python virtual environment to keep dependencies isolated.

```bash
# Create a virtual environment named 'venv'
python3 -m venv venv

# Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows (Command Prompt):
# .\venv\Scripts\activate.bat

# On Windows (PowerShell):
# .\venv\Scripts\Activate.ps1
```

#### B. Install Dependencies

Install all the required Python packages specified in `requirements.txt`:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

### 2. Configure Environment Variables

1. Create a local `.env` configuration file by duplicating the provided `.env.example` template:
   ```bash
   cp .env.example .env
   ```
2. Open the newly created `.env` file in your editor and configure the necessary variables:
   - **`DATABASE_URL`**: Your PostgreSQL or Supabase connection string.
   - **`SECRET_KEY`**: A secure random secret key (used to sign JWT authentication tokens).
   - **`FRONTEND_URL`**: The URL of your local frontend application (default is `http://localhost:5174`).

---

### 3. Run the Backend Server

Start the development server with **Uvicorn** by executing the following command in your terminal:

```bash
uvicorn app.main:app --reload --port 8000
```

#### 📌 Application Endpoints & Documentation

Once the server is running, the following endpoints are available:

- **API Root**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Interactive API Documentation (Swagger UI)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) (Highly recommended for testing endpoints)
- **Alternative API Documentation (ReDoc)**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health Check Endpoint**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## 📁 Directory Structure

```text
netra-app/
├── app/                  # Main FastAPI Application Directory
│   ├── api/              # API router and endpoints (e.g. auth)
│   ├── core/             # Core configurations (database, security settings)
│   ├── models/           # SQLAlchemy Database Models
│   ├── schemas/          # Pydantic Schemas for data validation
│   ├── services/         # Application business logic
│   └── main.py           # Application entrypoint & middlewares
├── .env                  # Local environment file (ignored by git)
├── .env.example          # Environment template file
├── requirements.txt      # Project requirements/dependencies
└── README.md             # Project documentation (this file)
```
