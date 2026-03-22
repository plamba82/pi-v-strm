 # Use official Python image (slim for smaller size)
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir locust

# Copy the Python script into the container
COPY app/main.py .


# Expose Locust web UI port
EXPOSE 8081

# Set entrypoint to run the script
# Default command (can be overridden)
CMD ["locust", "-f", "main.py"]
