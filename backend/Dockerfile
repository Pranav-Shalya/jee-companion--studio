# Python 3.12 slim base image for minimal footprint
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Set container working directory
WORKDIR /app

# Install system dependencies (build-essential for C extensions if required)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code
COPY . /app

# Ensure data directory exists for SQLite analytics DB persistence
RUN mkdir -p /app/data

# Expose FastAPI application port
EXPOSE 8000

# Start FastAPI backend with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
