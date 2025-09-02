# Use the official Playwright Python image with Chromium installed
FROM mcr.microsoft.com/playwright/python:v1.46.0-jammy

# Create and set the working directory inside the container
WORKDIR /app

# Copy only requirements first for Docker layer caching
COPY requirements.txt ./

# Install Python dependencies without caching
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (Chromium) with dependencies.
# This is usually redundant since the base image already has them, but kept for clarity.
RUN playwright install --with-deps chromium

# Copy the bot code into the container
COPY bot.py ./

# By default, run the bot. Environment variables will be provided by the
# deployment platform (e.g. Railway) at runtime.
CMD ["python", "bot.py"]