from pathlib import Path

from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent


def first_existing_path(*paths: Path) -> Path:
    """Return the first existing path, or the first candidate for clear errors."""
    for path in paths:
        if path.exists():
            return path
    return paths[0]


TEMPLATES_DIR = first_existing_path(
    BASE_DIR / "templates",
    PROJECT_DIR / "templates",
    Path("/app/app/templates"),
    Path("/app/templates"),
)
TEMPLATES_DIRS = [
    path
    for path in (
        BASE_DIR / "templates",
        PROJECT_DIR / "templates",
        Path("/app/app/templates"),
        Path("/app/templates"),
    )
    if path.exists()
]
STATIC_DIR = first_existing_path(
    BASE_DIR / "static",
    PROJECT_DIR / "static",
    Path("/app/app/static"),
    Path("/app/static"),
)

templates = Jinja2Templates(
    directory=[str(path) for path in TEMPLATES_DIRS] or str(TEMPLATES_DIR)
)
