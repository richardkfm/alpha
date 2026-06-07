FROM python:3.11-slim

WORKDIR /app

# psycopg2-binary ships its own libs, but keep build essentials minimal & cached.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
