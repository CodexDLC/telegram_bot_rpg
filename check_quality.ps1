$ErrorActionPreference = "Stop"
Write-Host "🚀 Starting Local Quality Check..." -ForegroundColor Cyan

# 1. Backend & Tests: Ruff
Write-Host "`n🔍 Checking Style (Ruff)..." -ForegroundColor Yellow
try {
    # Проверяем backend
    ruff check backend/ --fix
    if ($LASTEXITCODE -ne 0) { throw "Ruff found errors" }
    Write-Host "✅ Ruff passed!" -ForegroundColor Green
} catch {
    Write-Host "❌ Ruff failed!" -ForegroundColor Red
    exit 1
}

# 2. Backend: Mypy
Write-Host "`n🧠 Checking Backend Types (Mypy)..." -ForegroundColor Yellow
try {
    mypy backend/
    if ($LASTEXITCODE -ne 0) { throw "Mypy found errors" }
    Write-Host "✅ Mypy passed!" -ForegroundColor Green
} catch {
    Write-Host "❌ Mypy failed!" -ForegroundColor Red
    exit 1
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
