# Local / docker compose image. Data is mounted by docker-compose.yml:
#   /contracts (MOCK=1 sample dataset + fixtures), /data/processed (real data).
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
ENV FIXTURES_DIR=/contracts/fixtures PROCESSED_DIR=/data/processed MOCK=1
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=6 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
