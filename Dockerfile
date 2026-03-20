FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p reports tests config

# Install the framework
RUN pip install -e .

# Set environment variables
ENV PYTHONPATH=/app/src
ENV API_TEST_BASE_URL=http://localhost:8080

# Expose port for potential web interface
EXPOSE 8080

# Default command
CMD ["python", "main.py", "run", "--help"]
