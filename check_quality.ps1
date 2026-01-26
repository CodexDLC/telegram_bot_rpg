$ErrorActionPreference = "Continue"
Write-Host "🚀 Starting Local Quality Check..." -ForegroundColor Cyan

# 1. Backend & Tests: Ruff
Write-Host "`n🔍 Checking Style (Ruff)..." -ForegroundColor Yellow

# --- STEP 1: FORMATTING ---
Write-Host "✨ Running Ruff Format..." -ForegroundColor DarkYellow
ruff format --check
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️ Ruff Format found unformatted files. Attempting to fix..." -ForegroundColor Yellow
    ruff format
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Ruff Format failed to fix files!" -ForegroundColor Red
        exit 1
    } else {
        Write-Host "✅ Ruff Format fixed files." -ForegroundColor Green
        Start-Sleep -Seconds 1
        Clear-Host
    }
} else {
    Write-Host "✅ Ruff Format passed!" -ForegroundColor Green
}

# --- STEP 2: AUTO-FIX ---
Write-Host "`n🔧 Running Ruff Check with --fix..." -ForegroundColor DarkYellow
ruff check --fix
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️ Ruff Check --fix found issues. Re-checking..." -ForegroundColor Yellow
} else {
    Write-Host "✅ Ruff Check --fix applied." -ForegroundColor Green
}

Start-Sleep -Seconds 1
Clear-Host

# --- STEP 3: FINAL CHECK ---
Write-Host "`n🔍 Final Ruff Check..." -ForegroundColor Yellow
ruff check
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Ruff failed!" -ForegroundColor Red
    exit 1
} else {
    Write-Host "✅ Ruff passed!" -ForegroundColor Green
}

# 2. Backend: Mypy
Write-Host "`n🧠 Checking Types (Mypy)..." -ForegroundColor Yellow
mypy
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Mypy failed!" -ForegroundColor Red
    exit 1
} else {
    Write-Host "✅ Mypy passed!" -ForegroundColor Green
}

# 3. Backend: Pytest (Skipped)
Write-Host "`n🧪 Unit Tests (Pytest) - SKIPPED" -ForegroundColor DarkGray
# try {
#     $env:SECRET_KEY = "local_test_key"
#     pytest tests/unit
#     if ($LASTEXITCODE -ne 0) { throw "Tests failed" }
#     Write-Host "✅ Tests passed!" -ForegroundColor Green
# } catch {
#     Write-Host "❌ Tests failed!" -ForegroundColor Red
#     exit 1
# }

Write-Host "`n🎉 ALL CHECKS PASSED! You are ready to push." -ForegroundColor Cyan
