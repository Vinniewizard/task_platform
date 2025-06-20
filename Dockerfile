# Use official Python image
FROM python:3.12-slim

# Set working directory in the container
WORKDIR /app

# Install required system packages
RUN apt-get update && apt-get install -y \
    gcc \
    libmysqlclient-dev \
    default-libmysqlclient-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy all project files
COPY . /app

# Upgrade pip and install dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Expose default Django port
EXPOSE 8000

# Run the application with Gunicorn
CMD ["gunicorn", "task_platform.wsgi:application", "--bind", "0.0.0.0:8000"]
