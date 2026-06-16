import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from app.database import engine, init_db
from app.models import Base
from app.core import templates
from app.routes_kid import router as kid_router
from app.routes_admin import router as admin_router
from app.routes_api import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database on startup
    await init_db()
    yield


app = FastAPI(title="Chore Tracker", lifespan=lifespan)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(kid_router)
app.include_router(admin_router)
app.include_router(api_router)


@app.get("/")
async def homepage(request: Request):
    """Redirect to kid dashboard by default."""
    return RedirectResponse(url="/kid")


@app.get("/favicon.ico")
async def favicon():
    """Return empty response for favicon requests."""
    from fastapi.responses import Response
    return Response(content=None, media_type="image/x-icon")
