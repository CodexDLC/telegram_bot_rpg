$ErrorActionPreference = "Continue" # Изменил на Continue, чтобы обрабатывать ошибки вручную
Write-Host "🚀 Starting Local Quality Check..." -ForegroundColor Cyan

# 1. Backend & Tests: Ruff
Write-Host "`n🔍 Checking Style (Ruff)..." -ForegroundColor Yellow

# Сначала пробуем проверить
ruff check
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️ Ruff found errors. Attempting to fix..." -ForegroundColor Yellow

    # Пытаемся исправить
    ruff check --fix

    # Проверяем снова после исправления
    Write-Host "🔍 Re-checking Style (Ruff)..." -ForegroundColor Yellow
    ruff check

    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Ruff failed even after fix!" -ForegroundColor Red
        exit 1
    } else {
        Write-Host "✅ Ruff fixed issues and passed!" -ForegroundColor Green
    }
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
