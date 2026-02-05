FROM python:3.11-slim

# Metadata
LABEL maintainer="WS Conveyor Digital Twin Project"
LABEL description="Containerized environment for WS Conveyor simulation"
LABEL version="1.0"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install additional tools for development
RUN pip install --no-cache-dir \
    ipython \
    jupyter \
    jupyterlab

# Copy project files
COPY . .

# Create directories for output
RUN mkdir -p data/logs data/embeddings analysis/notebooks

# Set Python path
ENV PYTHONPATH=/app:$PYTHONPATH

# Default command (run example simulation)
CMD ["python", "examples/ws_conveyor_simulation.py"]

# For Jupyter notebook access, override with:
# docker run -p 8888:8888 ws-conveyor-twin jupyter notebook --ip=0.0.0.0 --allow-root --no-browser
