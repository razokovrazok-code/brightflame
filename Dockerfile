FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/staticfiles /app/media \
    && SECRET_KEY=collectstatic-build-only python manage.py collectstatic --noinput

EXPOSE 8000

ENV GUNICORN_WORKERS=3 \
    GUNICORN_THREADS=2

# --forwarded-allow-ips: nginx'dan kelgan X-Forwarded-* sarlavhalariga ishonish
# --graceful-timeout: qayta ishga tushirishda joriy so'rovlar tugashini kutish
CMD gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers ${GUNICORN_WORKERS} \
    --threads ${GUNICORN_THREADS} \
    --timeout 120 \
    --graceful-timeout 30 \
    --keep-alive 75 \
    --forwarded-allow-ips "*" \
    --access-logfile - \
    --error-logfile -
