FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY agent/ ./agent/
COPY tools/ ./tools/

EXPOSE 8501

# Streamlit UI
CMD ["streamlit", "run", "agent/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
