FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential tzdata wget \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHERUSAGESTATS=false \
    PYTHONUNBUFFERED=1 \
    FASTF1_CACHE=/app/cache

RUN mkdir -p /app/cache

EXPOSE 8501

#HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
#  CMD wget -qO- http://127.0.0.1:8501/ || exit 1

CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]