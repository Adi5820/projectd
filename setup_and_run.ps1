########################################################################
# AGENTIC ADS - Complete Setup & Execution Script (Windows PowerShell)
# Run this file: Right-click -> Run with PowerShell
# Or: powershell -ExecutionPolicy Bypass -File d:\projectd\setup_and_run.ps1
########################################################################

$ErrorActionPreference = "Continue"
$ProjectRoot = "d:\projectd"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  AGENTIC ADS - Setup & Launcher" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ============================================================
# STEP 1: Check Prerequisites
# ============================================================
Write-Host "[1/7] Checking prerequisites..." -ForegroundColor Yellow

# Python
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ERROR: Python is not installed!" -ForegroundColor Red
    Write-Host "  Download from: https://www.python.org/downloads/" -ForegroundColor Red
    Write-Host "  Make sure to check 'Add Python to PATH' during install" -ForegroundColor Red
    exit 1
}
Write-Host "  Python: $pythonVersion" -ForegroundColor Green

# Node.js
$nodeVersion = node --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ERROR: Node.js is not installed!" -ForegroundColor Red
    Write-Host "  Download from: https://nodejs.org/" -ForegroundColor Red
    exit 1
}
Write-Host "  Node.js: $nodeVersion" -ForegroundColor Green

# MongoDB
try {
    $mongoCheck = Invoke-RestMethod -Uri "http://localhost:27017" -TimeoutSec 3 -ErrorAction SilentlyContinue 2>&1
} catch {
    # MongoDB returns a message even on error connections - that's OK
}
# Try mongosh or mongo ping
$mongoRunning = $false
try {
    $tcpClient = New-Object System.Net.Sockets.TcpClient
    $tcpClient.Connect("localhost", 27017)
    $mongoRunning = $tcpClient.Connected
    $tcpClient.Close()
} catch {}

if ($mongoRunning) {
    Write-Host "  MongoDB: Running on port 27017" -ForegroundColor Green
} else {
    Write-Host "  WARNING: MongoDB does not appear to be running on port 27017!" -ForegroundColor Red
    Write-Host "  The backend will start but database operations will fail." -ForegroundColor Red
    Write-Host "" -ForegroundColor Red
    Write-Host "  To install MongoDB:" -ForegroundColor Yellow
    Write-Host "    Option A - MongoDB Community Server:" -ForegroundColor White
    Write-Host "      Download: https://www.mongodb.com/try/download/community" -ForegroundColor White
    Write-Host "      Install as Windows Service (checked by default)" -ForegroundColor White
    Write-Host "" -ForegroundColor White
    Write-Host "    Option B - MongoDB Atlas (Free Cloud):" -ForegroundColor White
    Write-Host "      1. Go to https://www.mongodb.com/atlas" -ForegroundColor White
    Write-Host "      2. Create free M0 cluster" -ForegroundColor White
    Write-Host "      3. Get connection string" -ForegroundColor White
    Write-Host "      4. Update MONGODB_URL in backend\.env" -ForegroundColor White
    Write-Host ""
    $continue = Read-Host "  Continue anyway? (y/n)"
    if ($continue -ne "y") { exit 1 }
}

# FFmpeg (for video generation)
$ffmpegPath = Get-Command ffmpeg -ErrorAction SilentlyContinue
if ($ffmpegPath) {
    Write-Host "  FFmpeg: Found at $($ffmpegPath.Source)" -ForegroundColor Green
} else {
    Write-Host "  WARNING: FFmpeg not found. Video generation will not work." -ForegroundColor Yellow
    Write-Host "  Install: winget install ffmpeg" -ForegroundColor Yellow
    Write-Host "  Or download from: https://ffmpeg.org/download.html" -ForegroundColor Yellow
}

Write-Host ""

# ============================================================
# STEP 2: Install Python Dependencies
# ============================================================
Write-Host "[2/7] Installing Python dependencies..." -ForegroundColor Yellow
Set-Location $ProjectRoot

pip install -r backend\requirements.txt --quiet 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Python packages installed successfully" -ForegroundColor Green
} else {
    Write-Host "  WARNING: Some packages may have failed. Trying again..." -ForegroundColor Yellow
    pip install -r backend\requirements.txt 2>&1
}
Write-Host ""

# ============================================================
# STEP 3: Install Node.js Dependencies
# ============================================================
Write-Host "[3/7] Installing frontend dependencies..." -ForegroundColor Yellow
Set-Location "$ProjectRoot\frontend"

if (-not (Test-Path "node_modules")) {
    npm install 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  Node modules installed successfully" -ForegroundColor Green
    } else {
        Write-Host "  Retrying npm install..." -ForegroundColor Yellow
        npm install 2>&1
    }
} else {
    Write-Host "  Node modules already installed (skipping)" -ForegroundColor Green
}

Set-Location $ProjectRoot
Write-Host ""

# ============================================================
# STEP 4: Configure Environment Variables
# ============================================================
Write-Host "[4/7] Checking environment configuration..." -ForegroundColor Yellow

$envFile = "$ProjectRoot\backend\.env"
if (-not (Test-Path $envFile)) {
    Write-Host "  Creating .env from .env.example..." -ForegroundColor Yellow
    Copy-Item "$ProjectRoot\backend\.env.example" $envFile
}

$envContent = Get-Content $envFile -Raw
$needsKeys = $false

if ($envContent -match "GOOGLE_API_KEY\s*=\s*$" -or $envContent -match "GOOGLE_API_KEY\s*=\s*your") {
    Write-Host "  GOOGLE_API_KEY is not set!" -ForegroundColor Red
    Write-Host "    Get a free key at: https://aistudio.google.com/apikey" -ForegroundColor Yellow
    $needsKeys = $true
}

if ($envContent -match "TOGETHER_API_KEY\s*=\s*$" -or $envContent -match "TOGETHER_API_KEY\s*=\s*your") {
    Write-Host "  TOGETHER_API_KEY is not set!" -ForegroundColor Red
    Write-Host "    Get free $5 credit at: https://api.together.ai/settings/api-keys" -ForegroundColor Yellow
    $needsKeys = $true
}

if ($needsKeys) {
    Write-Host ""
    Write-Host "  NOTE: The app will start without API keys but AI generation" -ForegroundColor Yellow
    Write-Host "  features will return errors. You can add keys later to:" -ForegroundColor Yellow
    Write-Host "    $envFile" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host "  Environment configured" -ForegroundColor Green
}

# Frontend env
$frontendEnv = "$ProjectRoot\frontend\.env.local"
if (-not (Test-Path $frontendEnv)) {
    Set-Content -Path $frontendEnv -Value "NEXT_PUBLIC_API_URL=http://localhost:8000/api"
    Write-Host "  Created frontend .env.local" -ForegroundColor Green
}

Write-Host ""

# ============================================================
# STEP 5: Create Required Directories
# ============================================================
Write-Host "[5/7] Creating required directories..." -ForegroundColor Yellow

$dirs = @(
    "$ProjectRoot\media",
    "$ProjectRoot\media\posters",
    "$ProjectRoot\media\videos",
    "$ProjectRoot\media\thumbnails",
    "$ProjectRoot\media\documents",
    "$ProjectRoot\media\temp",
    "$ProjectRoot\data\chroma"
)

foreach ($dir in $dirs) {
    New-Item -ItemType Directory -Path $dir -Force -ErrorAction SilentlyContinue | Out-Null
}
Write-Host "  Media and data directories created" -ForegroundColor Green
Write-Host ""

# ============================================================
# STEP 6: Kill existing processes on ports 8000 and 3000
# ============================================================
Write-Host "[6/7] Checking for existing processes..." -ForegroundColor Yellow

# Kill anything on port 8000
$existing8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($existing8000) {
    $pids = $existing8000 | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($pid in $pids) {
        Write-Host "  Stopping process on port 8000 (PID: $pid)" -ForegroundColor Yellow
        Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
}

# Kill anything on port 3000
$existing3000 = Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue
if ($existing3000) {
    $pids = $existing3000 | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($pid in $pids) {
        Write-Host "  Stopping process on port 3000 (PID: $pid)" -ForegroundColor Yellow
        Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
}

Write-Host "  Ports 8000 and 3000 are free" -ForegroundColor Green
Write-Host ""

# ============================================================
# STEP 7: Start Both Servers
# ============================================================
Write-Host "[7/7] Starting servers..." -ForegroundColor Yellow
Write-Host ""

# Set PYTHONPATH for the backend
$env:PYTHONPATH = $ProjectRoot

# Start Backend (FastAPI + Uvicorn) in a new PowerShell window
Write-Host "  Starting Backend (FastAPI) on http://localhost:8000 ..." -ForegroundColor Cyan
$backendCmd = "cd '$ProjectRoot'; `$env:PYTHONPATH='$ProjectRoot'; Write-Host '=== AGENTIC ADS BACKEND ===' -ForegroundColor Cyan; Write-Host 'API Docs: http://localhost:8000/docs' -ForegroundColor Green; Write-Host 'Health:   http://localhost:8000/api/health' -ForegroundColor Green; Write-Host ''; uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload; Read-Host 'Press Enter to close'"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd

# Wait for backend to start
Write-Host "  Waiting for backend to initialize..." -ForegroundColor Gray
$backendReady = $false
for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep -Seconds 2
    try {
        $health = Invoke-RestMethod -Uri "http://localhost:8000/api/health" -TimeoutSec 3 -ErrorAction SilentlyContinue
        if ($health.status -eq "healthy") {
            $backendReady = $true
            break
        }
    } catch {}
    Write-Host "    Waiting... ($($i*2)s)" -ForegroundColor Gray
}

if ($backendReady) {
    Write-Host "  Backend is RUNNING and HEALTHY!" -ForegroundColor Green
} else {
    Write-Host "  WARNING: Backend may still be starting. Check the backend window." -ForegroundColor Yellow
}

# Start Frontend (Next.js) in a new PowerShell window
Write-Host ""
Write-Host "  Starting Frontend (Next.js) on http://localhost:3000 ..." -ForegroundColor Cyan
$frontendCmd = "cd '$ProjectRoot\frontend'; Write-Host '=== AGENTIC ADS FRONTEND ===' -ForegroundColor Cyan; Write-Host 'App: http://localhost:3000' -ForegroundColor Green; Write-Host ''; npm run dev; Read-Host 'Press Enter to close'"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

# Wait for frontend
Write-Host "  Waiting for frontend to compile..." -ForegroundColor Gray
$frontendReady = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 2
    try {
        $resp = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 5 -ErrorAction SilentlyContinue
        if ($resp.StatusCode -eq 200) {
            $frontendReady = $true
            break
        }
    } catch {}
    Write-Host "    Compiling... ($($i*2)s)" -ForegroundColor Gray
}

if ($frontendReady) {
    Write-Host "  Frontend is RUNNING!" -ForegroundColor Green
} else {
    Write-Host "  Frontend may still be compiling. Check the frontend window." -ForegroundColor Yellow
}

# ============================================================
# DONE - Print Summary
# ============================================================
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  AGENTIC ADS IS RUNNING!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Frontend App:    http://localhost:3000" -ForegroundColor White
Write-Host "  Backend API:     http://localhost:8000" -ForegroundColor White
Write-Host "  API Docs:        http://localhost:8000/docs" -ForegroundColor White
Write-Host "  Health Check:    http://localhost:8000/api/health" -ForegroundColor White
Write-Host ""
Write-Host "  How to use:" -ForegroundColor Yellow
Write-Host "    1. Open http://localhost:3000 in your browser" -ForegroundColor White
Write-Host "    2. Click 'New Campaign' in the sidebar" -ForegroundColor White
Write-Host "    3. Fill the 5-step wizard and click 'Launch Campaign'" -ForegroundColor White
Write-Host "    4. Click 'Generate All' on the campaign detail page" -ForegroundColor White
Write-Host "    5. Watch the AI generate ad copy, posters, and videos!" -ForegroundColor White
Write-Host ""

if ($needsKeys) {
    Write-Host "  REMINDER: Add your API keys to enable AI generation:" -ForegroundColor Red
    Write-Host "    Edit: $ProjectRoot\backend\.env" -ForegroundColor Yellow
    Write-Host "    GOOGLE_API_KEY=xxx    (https://aistudio.google.com/apikey)" -ForegroundColor Yellow
    Write-Host "    TOGETHER_API_KEY=xxx  (https://api.together.ai/settings/api-keys)" -ForegroundColor Yellow
    Write-Host ""
}

# Open browser
Write-Host "  Opening browser..." -ForegroundColor Cyan
Start-Process "http://localhost:3000"

Write-Host ""
Write-Host "  To stop: Close the Backend and Frontend PowerShell windows" -ForegroundColor Gray
Write-Host ""
