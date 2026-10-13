# Agentic Ads

Agentic Ads is a full-stack AI advertising platform that helps generate campaign ideas, ad copy, posters, and promotional videos from a single campaign brief.

## Tech Stack

- Backend: FastAPI + Python
- Frontend: Next.js + React + TypeScript
- Database: MongoDB
- Vector search: ChromaDB
- AI providers: Google Gemini and Together AI

## Project Structure

- `backend/` — API, agents, repositories, workers, and generation logic
- `frontend/` — Next.js web app
- `media/` — generated media files
- `data/` — local storage for vector and database data
- `setup_and_run.ps1` — Windows launcher script for the project

## Prerequisites

Before running the app, install the following:

- Python 3.11+
- Node.js 18+
- MongoDB running locally on port 27017
- Optional: FFmpeg for video generation

## Quick Start (Windows)

From the project root:

```powershell
cd d:\projectd
powershell -ExecutionPolicy Bypass -File .\setup_and_run.ps1
```

This script will:

1. Check Python, Node.js, and MongoDB
2. Install Python dependencies
3. Install frontend dependencies
4. Create the required `.env` and frontend `.env.local` files
5. Create media and data directories
6. Start the backend and frontend servers

## Manual Start

### 1) Backend

```powershell
cd d:\projectd
$env:PYTHONPATH = "d:\projectd"
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2) Frontend

```powershell
cd d:\projectd\frontend
npm install
npm run dev
```

## Environment Variables

The project expects configuration in `backend/.env`.

Create it from the example if needed:

```powershell
cd d:\projectd
copy backend\.env.example backend\.env
```

Required values may include:

- `MONGODB_URL`
- `MONGODB_DB_NAME`
- `GOOGLE_API_KEY`
- `TOGETHER_API_KEY`

## URLs

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Swagger Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/api/health

## Useful Commands

### Backend tests

```powershell
cd d:\projectd
python -m pytest backend/tests -q
```

### Production frontend build

```powershell
cd d:\projectd\frontend
npm run build
```

## Notes

- If MongoDB is not running, the backend may start but generation features will fail.
- If FFmpeg is missing, video generation may not work.
- The project uses local media and vector storage directories under `media/` and `data/`.

## License

This project is intended for local development and demonstration use.
