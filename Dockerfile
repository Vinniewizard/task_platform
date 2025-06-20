# Use official Python slim image
FROM python:3.12-slim

# Set environment variable to prevent prompts from apt
ENV DEBIAN_FRONTEND=noninteractive

# Set working directory
WORKDIR /app

# Install system dependencies needed for building mysqlclient and running Django
RUN apt-get update && apt-get install -y \
    gcc \
    pkg-config \
    libmariadb-dev \
    libmariadb-dev-compat \
    build-essential \
    python3-dev \
    libssl-dev \
    libffi-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv

# Activate virtualenv and add to path
ENV PATH="/opt/venv/bin:$PATH"

# Copy project files into container
COPY . /app

# Upgrade pip and install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Collect static files (optional: only if you use collectstatic)
# RUN python manage.py collectstatic --noinput

# Expose Django/Gunicorn default port
EXPOSE 8000

# Start Gunicorn to serve Django app
CMD ["gunicorn", "task_platform.wsgi:application", "--bind", "0.0.0.0:8000"]
