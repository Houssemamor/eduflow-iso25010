FROM python:3.14-slim

# Run as a non-root user (least privilege, OWASP security misconfiguration).
RUN useradd --create-home --uid 10001 appuser
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY seed.py ./seed.py

USER appuser
EXPOSE 8000

# Exec form so the process receives signals directly.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
