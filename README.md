# UniMarket

Everything you need. All in one place.

Multi-vendor, multi-category e-commerce and B2B marketplace.
Initial market: Zambia. Architecture designed for international expansion.

## Stack

- **Frontend:** React 18 + Vite + Tailwind CSS + TypeScript
- **Backend:** Django 5 + Django REST Framework + Channels + Celery
- **Database:** PostgreSQL 16
- **Cache/Broker:** Redis 7
- **Package managers:** `uv` (Python), `pnpm` (Node)

## Prerequisites

- Python 3.12+ (3.14 supported via `uv`)
- Node 20+ and `pnpm` 10+
- `uv` (https://docs.astral.sh/uv/)
- Docker + Docker Compose

## Local Development Setup

```bash
# 1. Start Postgres + Redis
make up

# 2. Install backend dependencies
cd backend && uv sync --extra dev

# 3. Run migrations
make migrate

# 4. Start backend (terminal 1)
make backend

# 5. Install frontend dependencies
cd frontend && pnpm install

# 6. Start frontend (terminal 2)
make frontend