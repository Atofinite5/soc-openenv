FROM python:3.11-slim

RUN useradd -m -u 1000 appuser
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY env ./env
COPY client ./client
COPY server ./server
COPY openenv.yaml ./openenv.yaml
COPY pyproject.toml ./pyproject.toml

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 7860
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]
