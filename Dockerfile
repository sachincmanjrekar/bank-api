# Small official Python image (Debian Linux without extras), same version as the local .venv.
FROM python:3.14-slim

# Don't write .pyc files; print logs immediately instead of buffering them.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first, in their own layer. Docker caches each step, so as
# long as requirements.txt doesn't change, rebuilding after a code change skips this.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Then the code (changes often, so it comes last).
COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app

# Don't run as root: if the app were ever compromised, the attacker wouldn't
# have full control of the container. /app/data is where SQLite keeps its file.
RUN useradd --create-home appuser && mkdir /app/data && chown appuser /app/data
USER appuser

ENV DATABASE_URL=sqlite:////app/data/bank.db

EXPOSE 8000

# On every start: bring the database up to date, then start the server.
# --host 0.0.0.0 accepts connections from outside the container (127.0.0.1 wouldn't).
# "exec" makes uvicorn the main process, so `docker stop` shuts it down cleanly.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
