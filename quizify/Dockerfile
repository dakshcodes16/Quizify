# Quizify — multi-stage Dockerfile
# Runs both FastAPI (auth/data API) and Streamlit (UI) in one container
# via a small supervisor script. For production, prefer running them as
# two separate services/containers (see docker-compose.yml).

FROM python:3.11-slim

WORKDIR /app

# System deps for pypdf/python-docx/chromadb
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p database vectorstore/chroma_data /app/uploads

EXPOSE 8000 8501

COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

ENTRYPOINT ["/app/docker-entrypoint.sh"]
