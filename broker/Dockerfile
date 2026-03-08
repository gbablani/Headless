FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY app.py start_server.py .env* ./

EXPOSE 3978 8000

# Default: M365 Agents SDK mode (port 3978).
# Override with:  CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
# to run the standalone FastAPI broker instead.
CMD ["python", "app.py"]
