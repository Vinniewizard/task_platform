# Use official Python image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies (note: replaced libmysqlclient-dev)
RUN apt-get update && apt-get install -y \
    gcc \
    libmariadb-dev \
    libmariadb-dev-compat \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy project files
COPY . /app

# Upgrade pip and install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Expose Django's default port
EXPOSE 8000

# Run the Django app with Gunicorn
CMD ["gunicorn", "task_platform.wsgi:application", "--bind", "0.0.0.0:8000"]
