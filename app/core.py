import os
from fastapi.templating import Jinja2Templates

# Get the directory where this file is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Create templates instance with correct path
templates = Jinja2Templates(directory=TEMPLATES_DIR)

