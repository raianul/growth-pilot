Read the entire codebase — backend (FastAPI), frontend (React/Vite), database config, environment variables, and any existing deployment configs.

## Task: Prepare for deployment — Railway (backend) + Vercel (frontend)

### 1. Backend — Railway

Create these files:

**Procfile** (root or backend directory):
- web: uvicorn app.main:app --host 0.0.0.0 --port $PORT

**railway.toml** (if needed):
- Set build command, start command
- Python version

**requirements.txt** or verify pyproject.toml has all dependencies listed

Verify/update:
- app.main:app — confirm this is the correct FastAPI app entry point
- CORS: allow the Vercel frontend domain (add env var FRONTEND_URL, default to localhost for dev)
- All secrets read from environment variables (not hardcoded):
  - DATABASE_URL (Supabase PostgreSQL connection string)
  - REDIS_URL (if using Redis)
  - SERPAPI_API_KEY
  - PERPLEXITY_API_KEY (if used)
  - FIRECRAWL_API_KEY (if used)
  - FRONTEND_URL (for CORS)
- Database: confirm SQLAlchemy uses DATABASE_URL from env
- Remove any localhost/127.0.0.1 hardcoded URLs
- Health check endpoint: GET /health returns {"status": "ok"}

### 2. Frontend — Vercel

Create/update:

**vercel.json** in the frontend directory:
- Build command: npm run build (or pnpm/yarn equivalent)
- Output directory: dist
- Rewrites: all routes → index.html (SPA)

**Environment variable handling:**
- API base URL should read from VITE_API_URL env var
- Default to http://localhost:8000 for local dev
- In production, set VITE_API_URL to the Railway backend URL

Check all API calls in the frontend:
- Find every fetch/axios call
- Confirm they use the API base URL variable, not hardcoded localhost
- List any hardcoded URLs that need fixing

### 3. Environment variables summary

Create a .env.example file listing ALL required env vars with descriptions:

