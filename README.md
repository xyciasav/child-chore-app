"# Chore Tracker

A simple local web app for tracking family chores and rewards. Designed for children to use on a tablet browser, with a parent admin panel for approvals and management.

## Features

- **Child Dashboard** (`/kid`): View chores, submit completions, request rewards
- **Admin Dashboard** (`/admin`): Approve/deny submissions, manage chores and rewards
- **REST API**: Ready for Home Assistant integration
- **Persistent Storage**: SQLite database with Docker volume

## Quick Start

### Run Locally

```bash
# Clone or copy this project
cd choretracker

# Run with Docker Compose
docker-compose up --build
```

The app will be available at:
- **Child Dashboard**: http://localhost:8000/kid
- **Admin Dashboard**: http://localhost:8000/admin
- **API Docs**: http://localhost:8000/docs

### Deploy in Portainer

1. In Portainer, go to **Stacks** → **Add Stack**
2. Choose **Compose file** as the build method
3. Paste the contents of `docker-compose.yml`
4. Set environment variables:
   - `ADMIN_PASSCODE`: Your desired admin passcode (default: `parent123`)
5. Click **Deploy the stack**

The stack will be available at the container's IP on port 8000.

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ADMIN_PASSCODE` | `parent123` | Passcode to access admin panel |
| `DATABASE_URL` | `sqlite:///./instance/chore.db` | Database connection string |

### Change Admin Passcode

Set the `ADMIN_PASSCODE` environment variable in your `docker-compose.yml`:

```yaml
environment:
  - ADMIN_PASSCODE=your_secure_passcode
```

Or set it as a Portainer stack environment variable.

## API Endpoints

All API endpoints are prefixed with `/api`:

| Endpoint | Description |
|----------|-------------|
| `GET /api/children` | List all children |
| `GET /api/children/{id}/balance` | Get child's coin balance |
| `GET /api/chores` | List all active chores |
| `GET /api/chores/pending` | Get pending chore approvals |
| `GET /api/chores/history` | Get completed chore history |
| `GET /api/rewards` | List all active rewards |
| `GET /api/rewards/pending` | Get pending reward requests |
| `GET /api/rewards/history` | Get completed reward history |
| `GET /api/summary` | Get overall summary |

### Home Assistant Integration

Example REST sensor for child's coin balance:

```yaml
sensor:
  - platform: rest
    name: "Child Coin Balance"
    resource: http://your-server-ip:8000/api/children/1/balance
    value_template: "{{ value_json.coins }}"
    json_attributes:
      - name
      - coins
```

Example for pending approvals count:

```yaml
sensor:
  - platform: rest
    name: "Pending Chore Approvals"
    resource: http://your-server-ip:8000/api/chores/pending
    value_template: "{{ value_json | length }}"
```

## Project Structure

```
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── database.py          # Database configuration
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── auth.py              # Admin authentication
│   ├── routes_kid.py        # Child dashboard routes
│   ├── routes_admin.py      # Admin dashboard routes
│   ├── routes_api.py        # REST API routes
│   ├── templates/           # Jinja2 HTML templates
│   │   ├── base.html
│   │   ├── kid_dashboard.html
│   │   ├── admin_login.html
│   │   └── admin_dashboard.html
│   └── static/
│       └── styles.css       # All CSS styles
├── docker-compose.yml       # Docker Compose configuration
├── Dockerfile               # Container build instructions
├── requirements.txt         # Python dependencies
└── README.md                # This file
```

## Data Persistence

The SQLite database is stored in a Docker volume (`chore-data`). Data persists across container restarts and updates.

To backup the database:
```bash
docker run --rm -v chore-tracker_chore-data:/data -v $(pwd):/backup alpine tar czf /backup/chore-db.tar.gz -C /data .
```

## Future Enhancements

- Multiple children support
- Home Assistant MQTT integration
- Push notifications for approvals
- Custom themes
- Export/import data
"