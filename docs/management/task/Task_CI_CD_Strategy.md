> ⚠️ **PHASE 5 TARGET**
> Эта задача запланирована на этап "Инфраструктура и Релиз".

# 🚀 CI/CD Strategy & Branching Model

> **Status:** Planned
> **Goal:** Автоматизация проверок кода и деплоя для обеспечения стабильности `main` и `release` веток.

## 1. Branch Protection Rules (Правила "Галочек")

Настройка GitHub для защиты ключевых веток от прямого вмешательства и сломанного кода.

### 1.1. Ветка `develop` (Интеграционная)
*   **Цель:** Сборка фич от разработчиков. Код должен компилироваться и проходить базовые тесты.
*   **Правила:**
    *   `Require pull request`: **Да**.
    *   `Require status checks`: Включить проверку **Lite Checks** (см. Workflow 1).

### 1.2. Ветка `main` (Стабильная / Pre-Prod)
*   **Цель:** "Золотой стандарт". Код, готовый к релизу.
*   **Правила:**
    *   `Require pull request`: **Да**.
    *   `Require status checks`: Включить проверку **Heavy Checks** (см. Workflow 2).
    *   *Policy:* Мерж только из `develop` (контролируется культурой/ревью).

### 1.3. Ветка `release` (Production)
*   **Цель:** Деплой на боевые сервера.
*   **Правила:**
    *   `Require pull request`: **Да**.
    *   `Restrict who can push`: Только Tech Leads / DevOps.
    *   *Policy:* Мерж только из `main`.

---

## 2. GitHub Actions Workflows

Три раздельных пайплайна для разных этапов жизненного цикла кода.

### Workflow 1: Lite Checks (Develop)
*   **Trigger:** PR в ветку `develop`.
*   **Задача:** Быстрая обратная связь разработчику (1-3 мин).
*   **Шаги:**
    1.  Checkout code.
    2.  Linter (Ruff/Mypy).
    3.  Unit Tests (Pytest - быстрые, без БД/сети).

```yaml
# .github/workflows/1-develop-check.yml
name: Lite Checks (Develop)
on:
  pull_request:
    branches: [ "develop" ]
jobs:
  fast-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install Deps
        run: pip install -r requirements.txt
      - name: Lint & Unit
        run: |
          ruff check .
          mypy .
          pytest tests/unit
```

### Workflow 2: Heavy Checks (Main Guard)
*   **Trigger:** PR в ветку `main`.
*   **Задача:** Полная валидация перед стабилизацией.
*   **Шаги:**
    1.  Checkout code.
    2.  Integration Tests (с поднятием тестовой БД в Docker Service).
    3.  E2E Tests (если есть).
    4.  Security Scan (Bandit/Safety).

```yaml
# .github/workflows/2-main-full-check.yml
name: Heavy Checks (Main Guard)
on:
  pull_request:
    branches: [ "main" ]
jobs:
  full-validation:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        # ... настройки сервиса ...
    steps:
      - uses: actions/checkout@v3
      # ... setup ...
      - name: Integration Tests
        run: pytest tests/integration
```

### Workflow 3: Build & Deploy (Release)
*   **Trigger:** Push (Merge) в ветку `release`.
*   **Задача:** Доставка кода на прод. Тесты пропускаются (мы доверяем `main`).
*   **Шаги:**
    1.  Login to Docker Hub.
    2.  Build & Push Docker Image (теги: `latest`, `sha`).
    3.  Deploy via SSH (обновление сервиса на сервере).

```yaml
# .github/workflows/3-release-deploy.yml
name: Build & Deploy (Release)
on:
  push:
    branches: [ "release" ]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build and Push
        # ... docker build ...
      - name: Update Production
        uses: appleboy/ssh-action@master
        # ... docker service update ...
```

---

## 3. Future Improvement: Immutable Artifacts

**Проблема текущей схемы:** Сборка происходит в `release`. Если Docker Hub упадет или `pip install` скачает сломанную зависимость, релиз сломается, хотя тесты прошли.

**Целевая схема (Best Practice):**
1.  **В Main (после тестов):** Собираем Docker-образ и пушим его с тегом `v1.0-rc` (Release Candidate).
2.  **В Release:** Мы **не собираем** заново. Мы просто берем готовый образ `v1.0-rc`, ставим ему тег `latest` (или `v1.0`) и деплоим.

*Для старта проекта текущая схема (сборка в release) достаточна и проще в настройке.*
