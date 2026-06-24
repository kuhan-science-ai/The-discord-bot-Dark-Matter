FROM python:3.11-slim

WORKDIR /app

# Install compilation dependencies if needed (none strictly required but good for wheel builds)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Create directories for persistent SQLite db and log output
RUN mkdir -p data logs

# Run the bot main file
CMD ["python", "bot.py"]
