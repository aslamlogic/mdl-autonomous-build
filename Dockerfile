FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (if any needed – none for this app)
# RUN apt-get update && apt-get install -y --no-install-recommends ... && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose the port FastAPI runs on (8000 is default for uvicorn)
EXPOSE 8000

# Command to run the application
# The entrypoint is app.py (which contains the FastAPI app)
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
