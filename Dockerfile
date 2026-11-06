FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for audio handling
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libasound2-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Expose Streamlit default port
EXPOSE 8502

# Run Zyren on container launch
CMD ["streamlit", "run", "app.py", "--server.port=8502", "--server.address=0.0.0.0", "--server.headless=true"]

