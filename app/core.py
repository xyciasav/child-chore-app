from fastapi.templating import Jinja2Templates
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

REQUIRED_TEMPLATES = (
    "base.html",
    "kid_dashboard.html",
    "admin_login.html",
    "admin_dashboard.html",
)
REQUIRED_STATIC_FILES = ("styles.css",)


def validate_project_layout() -> None:
    """Fail fast when the Docker image is missing web assets."""
    missing = []

    for template_name in REQUIRED_TEMPLATES:
        template_path = TEMPLATES_DIR / template_name
        if not template_path.is_file():
            missing.append(str(template_path))

    for static_name in REQUIRED_STATIC_FILES:
        static_path = STATIC_DIR / static_name
        if not static_path.is_file():
            missing.append(str(static_path))

    if missing:
        missing_files = ", ".join(missing)
        raise RuntimeError(f"Missing required app assets: {missing_files}")


templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
