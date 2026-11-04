# UniMarket — Developer Documentation

Living documentation, updated at the end of every phase.

## Contents

- Architecture: docs/architecture.md
- Data Model: docs/data-model.md
- API: docs/api.md
- Roadmap: docs/roadmap.md
- Changelog: docs/CHANGELOG.md
- ADRs: docs/adr/

## Running locally

make up          # Postgres + Redis (Docker)
make backend     # Django on :8001 (terminal A)
make frontend    # Vite on :5173  (terminal B)
make test        # backend test suite

- Backend: http://localhost:8001
- Frontend: http://localhost:5173
- API docs: http://localhost:8001/api/v1/docs/
- Health:   http://localhost:8001/api/v1/health/

## Layout

backend/    Django project (modular monolith)
frontend/   React SPA (feature folders)
infra/      Docker Compose
docs/       This documentation
