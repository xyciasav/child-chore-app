# Chore Tracker

A local FastAPI web app for tracking family chores and rewards. Children can submit chores and request rewards; parents can approve or deny those requests from an admin panel.

## Features

- Child dashboard at `/kid`
- Parent admin panel at `/admin`
- REST API under `/api` for Home Assistant or other local integrations
- SQLite persistence through a Docker volume

## Quick Start

```bash
docker compose up --build
```

The compose file maps host port `8765` to container port `8000`:

- Child dashboard: `http://localhost:8765/kid`
- Admin dashboard: `http://localhost:8765/admin`
- API docs: `http://localhost:8765/docs`

The default admin passcode is `parent123`. Set `ADMIN_PASSCODE` in your environment or compose stack to change it.

## Portainer Deployment

Use the repository stack with this compose file. After pulling a new commit, redeploy with rebuild enabled so Portainer does not reuse an old image.

The app expects these files inside the container:

- `/app/app/templates/base.html`
- `/app/app/templates/kid_dashboard.html`
- `/app/app/templates/admin_login.html`
- `/app/app/templates/admin_dashboard.html`
- `/app/app/static/styles.css`

Startup validates those files and fails with a clear error if the image is missing any of them.

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `ADMIN_PASSCODE` | `parent123` | Passcode for the admin panel |
| `DATABASE_URL` | `sqlite+aiosqlite:///./instance/chore.db` | SQLAlchemy database URL |

## API Endpoints

| Endpoint | Description |
| --- | --- |
| `GET /api/children` | List children |
| `GET /api/children/{id}/balance` | Get a child's coin balance |
| `GET /api/chores` | List active chores |
| `GET /api/chores/pending` | List pending chore approvals |
| `GET /api/chores/history` | List reviewed chore submissions |
| `GET /api/rewards` | List active rewards |
| `GET /api/rewards/pending` | List pending reward requests |
| `GET /api/rewards/history` | List reviewed reward requests |
| `GET /api/summary` | Return a compact app summary |

## Project Structure

```text
app/
  main.py              FastAPI app entry point
  core.py              Template/static paths and layout validation
  database.py          Database setup
  models.py            SQLAlchemy models
  schemas.py           Pydantic schemas
  auth.py              Admin passcode check
  routes_kid.py        Child dashboard routes
  routes_admin.py      Admin dashboard routes
  routes_api.py        REST API routes
  templates/           Jinja templates
  static/styles.css    CSS
docker-compose.yml
Dockerfile
requirements.txt
```

## Data Persistence

The SQLite database is stored in the `chore-data` Docker volume at `/app/instance/chore.db`.
