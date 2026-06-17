from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from app.core import STATIC_DIR, TEMPLATES_DIR, validate_project_layout
from app.database import init_db
from app.routes_kid import router as kid_router
from app.routes_admin import router as admin_router
from app.routes_api import router as api_router

APP_VERSION = "2026-06-17-child-name"
APP_FEATURES = (
    "admin_chore_editing",
    "kid_in_page_confirmations",
    "chore_room_grouping",
    "reward_claim_sound",
    "chore_submit_sound",
    "kid_chore_reward_tabs",
    "admin_child_name",
    "admin_metrics",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_project_layout()
    await init_db()
    yield


app = FastAPI(title="Chore Tracker", lifespan=lifespan)

validate_project_layout()
print(f"Loaded Chore Tracker app from {__file__}; templates={TEMPLATES_DIR}", flush=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Include routers
app.include_router(kid_router)
app.include_router(admin_router)
app.include_router(api_router)


@app.get("/")
async def homepage():
    """Redirect to kid dashboard by default."""
    return RedirectResponse(url="/kid")


@app.get("/favicon.ico")
async def favicon():
    """Return empty response for favicon requests."""
    from fastapi.responses import Response
    return Response(content=None, media_type="image/x-icon")


@app.get("/version")
async def version():
    """Show the running app version for deployment troubleshooting."""
    return {
        "app": "chore-tracker",
        "version": APP_VERSION,
        "features": APP_FEATURES,
        "source": __file__,
        "templates": str(TEMPLATES_DIR),
    }

