FROM python:3.12-slim

LABEL org.opencontainers.image.title="Chore Tracker"
LABEL org.opencontainers.image.version="2026-06-17-gamified-metrics"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app directory contents to /app/app
COPY app/ ./app/

# Verify the image contains the web assets before it can be deployed.
RUN test -f /app/app/templates/base.html \
    && test -f /app/app/templates/kid_dashboard.html \
    && test -f /app/app/templates/admin_login.html \
    && test -f /app/app/templates/admin_dashboard.html \
    && test -f /app/app/static/styles.css \
    && test -f /app/app/main.py \
    && python -c "import app.main; assert hasattr(app.main, 'app')"

# Create instance directory for database
RUN mkdir -p /app/instance

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
