FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including libev for gevent and supervisor
RUN apt-get update && apt-get install -y \
    sqlite3 \
    gcc \
    python3-dev \
    libev-dev \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install gevent as an alternative
RUN pip install gevent==23.9.1

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p /app/data

# Copy supervisor config
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expose port
EXPOSE 3000

# Run supervisor to manage both gunicorn and scheduler
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
